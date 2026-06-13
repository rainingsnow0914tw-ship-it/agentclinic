"""Apply a coach to every finding in a report.

The report dict mutates in place under section 2 (`findings`):
- finding["remediation"] is replaced with the coached text if the coach
  succeeded and the boundary validator accepted it
- finding["_coach_provenance"] is added with backend + model fingerprint
- report["_coach_diagnostics"] (top-level, prefixed with _ to mark
  metadata) collects per-finding pass/fall outcomes -- the audit trail

The contract is "coach can only improve wording". If the coach errors
or violates the boundary, the deterministic remediation is kept and the
diagnostic captures why."""
from __future__ import annotations

from .base import Coach, CoachResult
from .validator import BoundaryViolation, validate_coached_finding


def coach_report(report: dict, coach: Coach,
                 trace: dict | None = None) -> dict:
    """Run `coach` over each finding in `report`; return the same report
    object with coached remediations + diagnostics attached. Passing
    `coach=None` is allowed and skips coaching (no-op)."""
    if coach is None:
        return report
    findings = report["sections"]["2"]["findings"]
    diagnostics: list[dict] = []
    trace_ctx = trace if trace is not None else {}
    # build_report copies remediation text into sections["4"]["items"];
    # keep that copy in sync so the rendered Section 4 reflects coaching
    s4_index: dict[str, dict] = {
        item["finding_id"]: item
        for item in report["sections"]["4"]["items"]
    }
    for finding in findings:
        original_remediation = finding["remediation"]
        outcome = _run_one(coach, finding, trace_ctx, original_remediation)
        diagnostics.append(outcome)
        if outcome["applied"]:
            finding["remediation"] = outcome["coached_remediation"]
            s4_item = s4_index.get(finding["finding_id"])
            if s4_item is not None:
                s4_item["remediation"] = outcome["coached_remediation"]
        finding["_coach_provenance"] = {
            "backend": outcome["backend"],
            "model": outcome["model"],
            "applied": outcome["applied"],
            "reason": outcome.get("reason"),
        }
    report["_coach_diagnostics"] = {
        "backend": coach.backend_name,
        "total": len(diagnostics),
        "applied": sum(1 for d in diagnostics if d["applied"]),
        "fallback": sum(1 for d in diagnostics if not d["applied"]),
        "per_finding": diagnostics,
    }
    return report


def _run_one(coach: Coach, finding: dict, trace: dict,
             original_remediation: str) -> dict:
    finding_id = finding["finding_id"]
    try:
        result: CoachResult = coach.coach(finding, trace)
    except Exception as e:  # noqa: BLE001 -- one coach call failing must
        # never abort the report; capture and fall back
        return _fallback(finding_id, coach, error=f"{type(e).__name__}: {e}",
                         reason="coach call raised", original=original_remediation)
    if result.error or not result.remediation:
        return _fallback(finding_id, coach,
                         error=result.error or "coach returned empty",
                         reason="coach reported error",
                         original=original_remediation,
                         model=result.model)
    try:
        validate_coached_finding(finding, result.remediation)
    except BoundaryViolation as e:
        return _fallback(finding_id, coach, error=str(e),
                         reason="boundary violation",
                         original=original_remediation,
                         model=result.model,
                         coached_attempt=result.remediation)
    return {
        "finding_id": finding_id,
        "backend": coach.backend_name,
        "model": result.model,
        "applied": True,
        "coached_remediation": result.remediation,
        "original_remediation": original_remediation,
    }


def _fallback(finding_id: str, coach: Coach, *, error: str | None,
              reason: str, original: str, model: str | None = None,
              coached_attempt: str | None = None) -> dict:
    return {
        "finding_id": finding_id,
        "backend": coach.backend_name,
        "model": model,
        "applied": False,
        "error": error,
        "reason": reason,
        "original_remediation": original,
        "coached_attempt": coached_attempt,
    }
