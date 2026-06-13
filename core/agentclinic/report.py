"""Six-section report builder (deterministic; the LLM coaching layer of P4
may rewrite wording later but is never allowed to add findings or change
numbers). Section text templates live in config/report_templates.json.

Hard guarantees enforced by validate_report():
- all six sections present, in order
- Section 5 (information gaps) is never empty"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .normalize import detect_pricing_gap

DEFAULT_TEMPLATES_PATH = Path(__file__).parent / "config" / "report_templates.json"
DEFAULT_PRICING_PATH = Path(__file__).parent / "config" / "model_pricing.json"


class ReportContractError(ValueError):
    """Raised when a built report violates the report contract."""


def load_templates(path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_TEMPLATES_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_pricing(path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_PRICING_PATH, encoding="utf-8") as f:
        return json.load(f)


def _calc_section_3_usd(trace: dict, known_wasted_tokens: int,
                        pricing: dict) -> tuple[float | None, str]:
    """Return (usd, usd_note). None usd is the honest answer when any of the
    following is true: trace has no model, pricing table has no entry for
    that model, zero known waste. Weighting uses the trace-level in/out
    ratio because per-finding fields don't split in/out -- the report is
    transparent about this approximation in usd_note."""
    if not known_wasted_tokens:
        return None, "no known waste tokens to price"
    model = trace.get("model")
    if not model:
        return None, ("trace has no `model` field -- per-finding USD cannot "
                      "be priced; see Section 5")
    entry = pricing.get("models", {}).get(model)
    if entry is None:
        return None, (f"no pricing entry for model `{model}` in pricing "
                      f"table {pricing.get('pricing_version', 'unknown')}; "
                      "see Section 5")
    events = trace["events"]
    total_in = sum(ev["token_in"] for ev in events if "token_in" in ev)
    total_out = sum(ev["token_out"] for ev in events if "token_out" in ev)
    total = total_in + total_out
    if total > 0:
        in_ratio = total_in / total
        out_ratio = total_out / total
        ratio_note = f"trace in/out ratio {in_ratio:.0%}/{out_ratio:.0%}"
    else:
        in_ratio = out_ratio = 0.5
        ratio_note = "no per-event tokens -- 50/50 assumed"
    weighted_per_token = (
        in_ratio * entry["input"] + out_ratio * entry["output"]
    ) / 1_000_000
    usd = round(known_wasted_tokens * weighted_per_token, 4)
    note = (f"model={model}; {ratio_note}; "
            f"weighted price ${entry['input']}/M in + "
            f"${entry['output']}/M out "
            f"(pricing snapshot {pricing.get('pricing_version', 'unknown')}, "
            "not billing-grade -- see config/model_pricing.json)")
    return usd, note


def _infer_goal(trace: dict) -> str:
    events = trace["events"]
    tool_counts = Counter(
        ev.get("tool_name") for ev in events if ev.get("tool_name")
    )
    type_counts = Counter(ev["type"] for ev in events)
    dominant_tool = tool_counts.most_common(1)[0][0] if tool_counts else None
    parts = [
        f"The trace contains {len(events)} event(s): "
        + ", ".join(f"{n}x {t}" for t, n in type_counts.most_common())
        + "."
    ]
    if dominant_tool:
        parts.append(f"Dominant tool: {dominant_tool}.")
    if type_counts.get("retry"):
        parts.append("The run shows repeated retry activity.")
    if type_counts.get("test"):
        parts.append("The run includes verification steps.")
    return " ".join(parts)


def _gap_entries(gaps: list[dict], templates: dict) -> list[dict]:
    entries = []
    for gap in gaps:
        spec = templates["data_gap_text"].get(gap["key"])
        if spec is None:
            entries.append({
                "missing": gap["key"],
                "impact": "unspecified impact (template missing)",
                "next_step": "n/a",
                "priority": templates.get("fallback_gap_priority", 9),
            })
            continue
        # gap may carry extra fields (e.g. "model" for pricing_entry_missing)
        # that the template references via {model} placeholders
        ctx = {k: v for k, v in gap.items() if k not in ("key", "count")}
        ctx["count"] = gap.get("count", 0)
        entries.append({
            "missing": spec["missing"].format(**ctx),
            "impact": spec["impact"].format(**ctx) if "{" in spec["impact"]
                      else spec["impact"],
            "next_step": (spec["next_step"].format(**ctx)
                          if "{" in spec["next_step"]
                          else spec["next_step"]),
            "priority": spec["priority"],
        })
    entries.extend(templates["standing_gaps"])
    return entries


def _build_section_7(sec3: dict, findings: list[dict],
                     budget_assessment: dict | None, t: dict) -> dict:
    """Section 7 (Budget & Runway Analysis) is always present. With a budget
    assessment it shows variance + next-run recommendation; without one it
    shows trace burn estimate only and explains how to enable the rest."""
    waste_ratio = (
        round(sec3["known_wasted_tokens"] / sec3["total_known_tokens"], 3)
        if sec3["total_known_tokens"] else None
    )
    top = sorted(
        (f for f in findings if f["estimated_waste"]["tokens"] is not None),
        key=lambda f: f["estimated_waste"]["tokens"],
        reverse=True,
    )[:3]
    trace_burn = {
        "total_known_tokens": sec3["total_known_tokens"],
        "known_wasted_tokens": sec3["known_wasted_tokens"],
        "waste_ratio": waste_ratio,
        "top_burn_patterns": [
            {"finding_id": f["finding_id"], "pattern": f["pattern"],
             "tokens": f["estimated_waste"]["tokens"]}
            for f in top
        ],
    }
    section = {
        "title": t["section_titles"]["7"],
        "trace_burn_estimate": trace_burn,
        "budget_assessment": None,
        "variance": None,
        "next_run_recommendation": None,
        "missing_note": None,
    }
    if budget_assessment is None:
        section["missing_note"] = t["budget_missing_note"]
        return section

    section["budget_assessment"] = budget_assessment
    section["variance"] = {
        "budget_projected_exhaustion_min":
            budget_assessment.get("projected_exhaustion_minutes"),
        "actual_trace_known_tokens": sec3["total_known_tokens"],
        "note": ("budget projects window-level exhaustion in minutes; trace "
                 "tokens are this-run only -- not direct apples-to-apples, "
                 "they are companion signals, not the same axis"),
    }
    section["next_run_recommendation"] = _recommend_next_run(
        budget_assessment, waste_ratio, t)
    return section


def _recommend_next_run(budget: dict, waste_ratio: float | None,
                        t: dict) -> dict:
    level = budget.get("warning_level", "unknown")
    rec_map = t.get("next_run_recommendation_map", {})
    mode, goal = rec_map.get(level, ["balanced", "balanced"])
    rationale = [f"current level={level}"]
    high_thresh = t.get("high_waste_ratio_threshold", 0.3)
    if waste_ratio is not None and waste_ratio > high_thresh:
        rationale.append(
            f"waste ratio {waste_ratio:.0%} > {high_thresh:.0%} "
            "-- cap parallel agents next run")
    return {
        "suggested_task_mode": mode,
        "suggested_user_goal": goal,
        "rationale": "; ".join(rationale),
    }


def build_report(trace: dict, gaps: list[dict], findings: list[dict],
                 score_result: dict, templates: dict | None = None,
                 budget_assessment: dict | None = None,
                 pricing: dict | None = None) -> dict:
    t = templates or load_templates()
    pr = pricing if pricing is not None else load_pricing()

    total_known = sum(
        ev["token_in"] + ev["token_out"]
        for ev in trace["events"]
        if "token_in" in ev and "token_out" in ev
    )
    events_missing_tokens = sum(
        1 for ev in trace["events"]
        if "token_in" not in ev or "token_out" not in ev
    )
    known_waste = sum(
        f["estimated_waste"]["tokens"] for f in findings
        if f["estimated_waste"]["tokens"] is not None
    )
    # findings may cite overlapping events; never report more waste than the
    # trace actually shows — clamp and say so instead of double counting
    waste_note = None
    if total_known and known_waste > total_known:
        known_waste = total_known
        waste_note = t["waste_overlap_note"]
    unknown_waste_findings = [
        f["finding_id"] for f in findings
        if f["estimated_waste"]["tokens"] is None
    ]
    biggest = max(
        (f for f in findings if f["estimated_waste"]["tokens"] is not None),
        key=lambda f: f["estimated_waste"]["tokens"],
        default=None,
    )

    pricing_gap = detect_pricing_gap(trace, pr)
    effective_gaps = list(gaps) + ([pricing_gap] if pricing_gap else [])
    gap_entries = sorted(_gap_entries(effective_gaps, t),
                         key=lambda g: g["priority"])

    usd, usd_note = _calc_section_3_usd(trace, known_waste, pr)
    section_3 = {
        "title": t["section_titles"]["3"],
        "total_known_tokens": total_known,
        "events_missing_token_fields": events_missing_tokens,
        "known_wasted_tokens": known_waste,
        "waste_note": waste_note,
        "waste_unknown_findings": unknown_waste_findings,
        "biggest_waste_point": (
            {
                "finding_id": biggest["finding_id"],
                "pattern": biggest["pattern"],
                "tokens": biggest["estimated_waste"]["tokens"],
            }
            if biggest else None
        ),
        "usd": usd,
        "usd_note": usd_note,
        "pricing_version": pr.get("pricing_version"),
    }

    report = {
        "schema_version": t.get("report_schema_version", "report-v2"),
        "trace_id": trace["trace_id"],
        "run_id": trace["run_id"],
        "agent_type": trace["agent_type"],
        "sections": {
            "1": {
                "title": t["section_titles"]["1"],
                "inferred_activity": _infer_goal(trace),
                "confidence_note": t["goal_confidence_note"],
            },
            "2": {
                "title": t["section_titles"]["2"],
                "findings": findings,
                "note": t["empty_findings_note"] if not findings else None,
            },
            "3": section_3,
            "4": {
                "title": t["section_titles"]["4"],
                "note": t["no_remediation_note"] if not findings else None,
                "items": [
                    {
                        "finding_id": f["finding_id"],
                        "pattern": f["pattern"],
                        "remediation": f["remediation"],
                    }
                    for f in findings
                ],
            },
            "5": {
                "title": t["section_titles"]["5"],
                "gaps": gap_entries,
            },
            "6": {
                "title": t["section_titles"]["6"],
                "suggestions": [
                    {"priority": g["priority"], "provide": g["next_step"]}
                    for g in gap_entries
                ],
            },
            "7": _build_section_7(section_3, findings, budget_assessment, t),
        },
        "score": score_result,
    }
    validate_report(report)
    return report


def validate_report(report: dict) -> None:
    sections = report.get("sections", {})
    for key in ("1", "2", "3", "4", "5", "6", "7"):
        if key not in sections:
            raise ReportContractError(f"report missing section {key}")
    if not sections["5"]["gaps"]:
        raise ReportContractError(
            "Section 5 (information gaps) must never be empty — honesty about "
            "what we cannot see is the product's core guarantee"
        )
    s7 = sections["7"]
    if s7.get("budget_assessment") is None and not s7.get("missing_note"):
        raise ReportContractError(
            "Section 7 missing both budget_assessment and missing_note — "
            "either provide a budget input or explain why none was given"
        )


def to_markdown(report: dict) -> str:
    s = report["sections"]
    sc = report["score"]
    lines = [
        f"# AgentClinic Report — trace `{report['trace_id']}` "
        f"(run `{report['run_id']}`, agent: {report['agent_type']})",
        "",
        f"**Score: {sc['value']} / 100 — Level {sc['level']}**  "
        f"(deduction {sc['weighted_deduction']}, "
        + ", ".join(f"{n} {sev}" for sev, n in sc["severity_counts"].items() if n)
        + (")" if any(sc["severity_counts"].values()) else "no findings)"),
        "",
        f"## 1. {s['1']['title']}",
        s["1"]["inferred_activity"],
        "",
        f"> {s['1']['confidence_note']}",
        "",
        f"## 2. {s['2']['title']}",
    ]
    if not s["2"]["findings"]:
        lines += [s["2"]["note"], ""]
    for f in s["2"]["findings"]:
        waste = f["estimated_waste"]
        waste_txt = (f"{waste['tokens']} tokens" if waste["tokens"] is not None
                     else "unknown")
        lines += [
            f"### {f['finding_id']} — `{f['pattern']}` "
            f"({f['severity']}, confidence {f['confidence']})",
            f"- estimated waste: {waste_txt} — {waste['basis']}",
            "- evidence:",
        ]
        for span in f["evidence_spans"]:
            tok = (f", tokens {span['token_in']}+{span['token_out']}"
                   if "token_in" in span and "token_out" in span else "")
            lines.append(f"  - `{span['trace_event_id']}`{tok}: {span['note']}")
        lines.append("")
    sec3 = s["3"]
    lines += [
        f"## 3. {sec3['title']}",
        f"- total known tokens: {sec3['total_known_tokens']}"
        + (f" ({sec3['events_missing_token_fields']} event(s) missing token "
           f"fields — totals are partial)" if sec3["events_missing_token_fields"]
           else ""),
        f"- known wasted tokens: {sec3['known_wasted_tokens']}",
    ]
    if sec3.get("waste_note"):
        lines.append(f"- note: {sec3['waste_note']}")
    if sec3["waste_unknown_findings"]:
        lines.append(
            "- findings with unknown waste (not guessed): "
            + ", ".join(sec3["waste_unknown_findings"])
        )
    if sec3["biggest_waste_point"]:
        b = sec3["biggest_waste_point"]
        lines.append(
            f"- biggest waste point: {b['finding_id']} (`{b['pattern']}`, "
            f"{b['tokens']} tokens)"
        )
    if sec3.get("usd") is not None:
        lines.append(f"- **USD waste: ${sec3['usd']:.4f}** "
                     f"({sec3['usd_note']})")
    else:
        lines.append(f"- USD: {sec3['usd_note']}")
    lines += ["", f"## 4. {s['4']['title']}"]
    if not s["4"]["items"]:
        lines.append(s["4"]["note"])
    for i, item in enumerate(s["4"]["items"], 1):
        lines.append(
            f"{i}. **{item['pattern']}** ({item['finding_id']}): "
            f"{item['remediation']}"
        )
    lines += ["", f"## 5. {s['5']['title']}"]
    for g in s["5"]["gaps"]:
        lines.append(f"- **{g['missing']}** → {g['impact']}")
    lines += ["", f"## 6. {s['6']['title']}"]
    for i, sug in enumerate(s["6"]["suggestions"], 1):
        lines.append(f"{i}. {sug['provide']}")
    sec7 = s["7"]
    lines += ["", f"## 7. {sec7['title']}"]
    tb = sec7["trace_burn_estimate"]
    lines.append(
        f"- trace burn: {tb['known_wasted_tokens']} wasted / "
        f"{tb['total_known_tokens']} known total"
        + (f" ({tb['waste_ratio']:.0%} ratio)"
           if tb["waste_ratio"] is not None else "")
    )
    if tb["top_burn_patterns"]:
        lines.append("- top burn patterns:")
        for p in tb["top_burn_patterns"]:
            lines.append(
                f"  - `{p['pattern']}` ({p['finding_id']}): {p['tokens']} tokens")
    if sec7["missing_note"]:
        lines.append(f"- {sec7['missing_note']}")
    if sec7["budget_assessment"] is not None:
        ba = sec7["budget_assessment"]
        lines.append(
            f"- pre-run gauge: **{ba['warning_level']}** "
            f"(action: `{ba['recommended_action']}`, "
            f"projected exhaustion: {ba['projected_exhaustion_minutes']}min)"
        )
        v = sec7["variance"]
        lines.append(f"- variance: {v['note']}")
        nr = sec7["next_run_recommendation"]
        lines.append(
            f"- next run: task_mode=`{nr['suggested_task_mode']}`, "
            f"user_goal=`{nr['suggested_user_goal']}` ({nr['rationale']})"
        )
    lines.append("")
    return "\n".join(lines)
