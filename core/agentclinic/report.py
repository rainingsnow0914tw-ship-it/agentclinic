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

DEFAULT_TEMPLATES_PATH = Path(__file__).parent / "config" / "report_templates.json"


class ReportContractError(ValueError):
    """Raised when a built report violates the report contract."""


def load_templates(path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_TEMPLATES_PATH, encoding="utf-8") as f:
        return json.load(f)


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
        entries.append({
            "missing": spec["missing"].format(count=gap.get("count", 0)),
            "impact": spec["impact"],
            "next_step": spec["next_step"],
            "priority": spec["priority"],
        })
    entries.extend(templates["standing_gaps"])
    return entries


def build_report(trace: dict, gaps: list[dict], findings: list[dict],
                 score_result: dict, templates: dict | None = None) -> dict:
    t = templates or load_templates()

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

    gap_entries = sorted(_gap_entries(gaps, t), key=lambda g: g["priority"])

    report = {
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
            "3": {
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
                "usd": None,
                "usd_note": t["usd_note"],
            },
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
        },
        "score": score_result,
    }
    validate_report(report)
    return report


def validate_report(report: dict) -> None:
    sections = report.get("sections", {})
    for key in ("1", "2", "3", "4", "5", "6"):
        if key not in sections:
            raise ReportContractError(f"report missing section {key}")
    if not sections["5"]["gaps"]:
        raise ReportContractError(
            "Section 5 (information gaps) must never be empty — honesty about "
            "what we cannot see is the product's core guarantee"
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
    lines += [f"- USD: {sec3['usd_note']}", "", f"## 4. {s['4']['title']}"]
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
    lines.append("")
    return "\n".join(lines)
