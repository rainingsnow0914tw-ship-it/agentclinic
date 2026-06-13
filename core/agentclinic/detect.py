"""Deterministic waste-pattern detectors (the judge).

Each detector is a pure function over the event list returning evidence
groups. All tunables — thresholds, severities, confidences, suppressions,
remediation text — live in config/rules.json; changing a rule must never
require touching this file. Detectors skip rather than guess when the data
they need is absent (the gap is reported by normalize)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .validate import validate_finding

DEFAULT_RULES_PATH = Path(__file__).parent / "config" / "rules.json"


def load_rules(path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _state(ev: dict) -> str | None:
    """state_hash, treating empty/whitespace strings as absent — an empty
    fingerprint must never satisfy an equality check."""
    s = ev.get("state_hash")
    if isinstance(s, str) and s.strip():
        return s
    return None


def _tokens_total(ev: dict) -> int | None:
    if "token_in" in ev and "token_out" in ev:
        return int(ev["token_in"] + ev["token_out"])
    return None


def _sum_tokens(events: list[dict]) -> int | None:
    """Exact sum, or None if any event lacks token fields (never guess)."""
    totals = [_tokens_total(ev) for ev in events]
    if any(t is None for t in totals):
        return None
    return sum(totals)  # type: ignore[arg-type]


# --- detectors: each returns a list of evidence groups -----------------------
# evidence group: {"events": [event, ...], "notes": {event_id: str},
#                  "waste_tokens": int | None, "waste_basis": str}


def detect_hard_hat_loop(events: list[dict], params: dict) -> list[dict]:
    """Chain of retries with unchanged state. Only the configured
    chain_breaking_event_types (evidence gathering / fixes) interrupt a
    chain; mere thinking (llm_call) or unrelated activity does not make a
    blind retry less blind."""
    min_chain = params["min_retry_chain"]
    breakers = set(params["chain_breaking_event_types"])
    groups, chain = [], []
    prev = None

    def flush() -> None:
        if len(chain) >= min_chain:
            waste = _sum_tokens(chain)
            groups.append({
                "events": list(chain),
                "notes": {
                    ev["event_id"]: "retry with state_hash unchanged from the "
                    "previous event; no evidence gathering in between"
                    for ev in chain
                },
                "waste_tokens": waste,
                "waste_basis": (
                    "sum of token_in+token_out across the blind retry chain "
                    "(initial attempt not counted)"
                    if waste is not None
                    else "token fields missing on chain events — waste unknown"
                ),
            })

    for ev in events:
        if ev["type"] == "retry":
            prev_hash = _state(prev) if prev else None
            cur_hash = _state(ev)
            if prev_hash is not None and cur_hash is not None and prev_hash == cur_hash:
                chain.append(ev)
            else:
                flush()
                chain = []
        elif ev["type"] in breakers:
            flush()
            chain = []
        # any other event type leaves the chain open: per config, only
        # evidence-gathering / fixing events interrupt blindness
        prev = ev
    flush()
    return groups


def detect_state_unchanged_retry(events: list[dict], params: dict) -> list[dict]:
    """A single no-op retry. A retry directly following an evidence or fix
    step (configurable justifying_prev_event_types) is a legitimate
    re-attempt and is not flagged."""
    justifying = set(params["justifying_prev_event_types"])
    groups = []
    prev = None
    for ev in events:
        if (ev["type"] == "retry" and prev is not None
                and prev["type"] not in justifying):
            ph, ch = _state(prev), _state(ev)
            if ph is not None and ch is not None and ph == ch:
                waste = _tokens_total(ev)
                groups.append({
                    "events": [ev],
                    "notes": {ev["event_id"]: "state_hash identical to previous event"},
                    "waste_tokens": waste,
                    "waste_basis": "tokens of the no-op retry"
                    if waste is not None
                    else "token fields missing — waste unknown",
                })
        prev = ev
    return groups


def _writes_without_evidence(events, params, size_pred):
    lookback = params["lookback_events"]
    evidence_types = set(params["evidence_event_types"])
    groups = []
    for i, ev in enumerate(events):
        if ev["type"] != "write":
            continue
        if "token_out" not in ev:
            continue  # size unknown -> skip, never guess (gap is reported upstream)
        if not size_pred(int(ev["token_out"])):
            continue
        window = events[max(0, i - lookback):i]
        if any(w["type"] in evidence_types for w in window):
            continue
        groups.append({
            "events": [ev],
            "notes": {ev["event_id"]: "write with no read/grep/test in the "
                      f"preceding {lookback} events"},
            "waste_tokens": None,
            "waste_basis": "unverified edit — cost is rework risk, not directly "
                           "countable in tokens",
        })
    return groups


def detect_lucky_guess(events: list[dict], params: dict) -> list[dict]:
    return _writes_without_evidence(
        events, params, lambda out: out <= params["max_write_tokens"]
    )


def detect_agent_piling_on(events: list[dict], params: dict) -> list[dict]:
    return _writes_without_evidence(
        events, params, lambda out: out >= params["min_write_tokens"]
    )


def detect_full_file_read_before_grep(events: list[dict], params: dict) -> list[dict]:
    """Big read followed by a search. If ANY grep already happened before the
    read, the flow is grep-first compliant and is not flagged."""
    threshold = params["big_read_tokens"]
    groups = []
    for i, ev in enumerate(events):
        if ev["type"] != "read":
            continue
        total = _tokens_total(ev)
        if total is None or total < threshold:
            continue
        if any(e["type"] == "grep" for e in events[:i]):
            continue
        later_grep = next((e for e in events[i + 1:] if e["type"] == "grep"), None)
        if later_grep is None:
            continue
        groups.append({
            "events": [ev, later_grep],
            "notes": {
                ev["event_id"]: f"full read of {total} tokens before any search",
                later_grep["event_id"]: "grep issued after the full read — "
                                         "search should have come first",
            },
            "waste_tokens": total,
            "waste_basis": "upper bound: tokens of the full-file read; a "
                           "targeted grep-first flow avoids most of it",
        })
    return groups


def detect_redundant_tool_call(events: list[dict], params: dict) -> list[dict]:
    grouped_types = set(params["grouped_event_types"])
    buckets: dict[tuple, list[dict]] = {}
    for ev in events:
        if ev["type"] not in grouped_types:
            continue
        tool = (ev.get("tool_name") or "").strip()
        summary = (ev.get("summary") or "").strip().lower()
        if not tool and not summary:
            continue  # no identity data — skip rather than guess sameness
        key = (ev["type"], tool, summary)
        buckets.setdefault(key, []).append(ev)
    groups = []
    for key, evs in buckets.items():
        if len(evs) < params["min_repeats"]:
            continue
        repeats = evs[1:]
        waste = _sum_tokens(repeats)
        groups.append({
            "events": evs,
            "notes": {e["event_id"]: ("first occurrence (legitimate)" if e is evs[0]
                                       else "identical repeat of the same call")
                      for e in evs},
            "waste_tokens": waste,
            "waste_basis": "tokens of repeated occurrences (first call not counted)"
            if waste is not None
            else "token fields missing on repeats — waste unknown",
        })
    return groups


def detect_completion_claim_without_verification(events: list[dict], params: dict) -> list[dict]:
    """Completion language with no verification event anywhere before it.
    Keywords match on word boundaries ('done' must not match 'abandoned').
    Verification events themselves (e.g. a test reporting 'all checks done')
    are exempt — a verification stating its own result is not a blind claim."""
    keywords = [k.lower() for k in params["claim_keywords"]]
    if not keywords:
        return []
    claim_re = re.compile(
        r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")\b")
    verify_types = set(params["verification_event_types"])
    groups = []
    for i, ev in enumerate(events):
        if ev["type"] in verify_types:
            continue
        summary = (ev.get("summary") or "").lower()
        if not claim_re.search(summary):
            continue
        if any(e["type"] in verify_types for e in events[:i]):
            continue
        groups.append({
            "events": [ev],
            "notes": {ev["event_id"]: "completion claim with no verification "
                      "event anywhere before it"},
            "waste_tokens": None,
            "waste_basis": "cost is unverified-completion risk, not directly "
                           "countable in tokens",
        })
    return groups


DETECTORS = {
    "hard_hat_loop": detect_hard_hat_loop,
    "state_unchanged_retry": detect_state_unchanged_retry,
    "lucky_guess": detect_lucky_guess,
    "agent_piling_on": detect_agent_piling_on,
    "full_file_read_before_grep": detect_full_file_read_before_grep,
    "redundant_tool_call": detect_redundant_tool_call,
    "completion_claim_without_verification": detect_completion_claim_without_verification,
}


# --- engine ------------------------------------------------------------------

def _evidence_span(ev: dict, note: str) -> dict:
    span = {"trace_event_id": ev["event_id"], "note": note}
    for key in ("start_time", "end_time"):
        if key in ev:
            span[key] = ev[key]
    for key in ("token_in", "token_out"):
        if key in ev:
            span[key] = int(ev[key])
    return span


def run_detectors(trace: dict, gaps: list[dict], rules: dict) -> list[dict]:
    """Run all enabled detectors, apply suppression, emit contract-valid
    findings. Every finding is self-validated against finding_schema_v1 —
    an invalid finding (e.g. no evidence) crashes the run, by design."""
    events = trace["events"]
    engine_cfg = rules["engine"]
    gap_keys = {g["key"] for g in gaps}

    raw: list[tuple[str, dict]] = []
    for pattern, rule in rules["patterns"].items():
        if not rule.get("enabled", True):
            continue
        detector = DETECTORS.get(pattern)
        if detector is None:
            continue  # config names a pattern this engine version doesn't know
        for group in detector(events, rule.get("params", {})):
            raw.append((pattern, group))

    # suppression: drop a finding whose evidence is fully covered by a
    # suppressor pattern's evidence (no double reporting of the same events)
    suppressed_idx: set[int] = set()
    for sup_pattern, sup_rule in rules["patterns"].items():
        targets = set(sup_rule.get("suppresses", []))
        if not targets:
            continue
        sup_ids = set()
        for pattern, group in raw:
            if pattern == sup_pattern:
                sup_ids.update(ev["event_id"] for ev in group["events"])
        if not sup_ids:
            continue
        for idx, (pattern, group) in enumerate(raw):
            if pattern in targets:
                ids = {ev["event_id"] for ev in group["events"]}
                if ids <= sup_ids:
                    suppressed_idx.add(idx)

    findings = []
    seq = 0
    for idx, (pattern, group) in enumerate(raw):
        if idx in suppressed_idx:
            continue
        rule = rules["patterns"][pattern]
        confidence = rule["base_confidence"]
        for gap_key, penalty in rule.get("degraded_by", {}).items():
            if gap_key in gap_keys:
                confidence *= 1 - penalty
        confidence = max(confidence, engine_cfg["min_confidence_floor"])

        seq += 1
        finding = {
            "finding_id": f"{engine_cfg['finding_id_prefix']}-{trace['trace_id']}-{seq:03d}",
            "pattern": pattern,
            "severity": rule["severity"],
            "confidence": round(confidence, 2),
            "evidence_spans": [
                _evidence_span(ev, group["notes"].get(ev["event_id"], ""))
                for ev in group["events"]
            ],
            "impacted_metric": rule.get("impacted_metric", "token_waste"),
            "estimated_waste": {
                "tokens": group["waste_tokens"],
                "usd": None,
                "basis": group["waste_basis"]
                + "; USD unavailable (no pricing table configured)",
            },
            "remediation": rule["remediation"],
            "replay": {
                "detector_id": pattern,
                "detector_version": rules["rules_version"],
                "rule_snapshot": json.dumps(rule.get("params", {}), sort_keys=True),
            },
        }
        validate_finding(finding)
        findings.append(finding)
    return findings
