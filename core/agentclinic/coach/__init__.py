"""LLM coaching layer -- the **coach** role of the four-role architecture.

Hard contract (enforced by validator, not aspiration):
- May rewrite finding `remediation` text only.
- May NOT add findings, drop findings, or change ids.
- May NOT change pattern / severity / confidence / evidence_spans /
  estimated_waste.tokens / score.
- May NOT introduce new judgements (no "this might be fine", no
  "actually I think this is worse").
- On any boundary violation, the original deterministic remediation is
  used; the coached attempt is recorded in `_coach_diagnostics` for
  audit but does NOT touch the canonical finding."""
from .apply import coach_report
from .base import Coach, CoachResult
from .mock import MockCoach
from .uipath_llm import UiPathCoach
from .validator import BoundaryViolation, validate_coached_finding
from .vertex import VertexCoach

__all__ = [
    "Coach", "CoachResult", "MockCoach", "VertexCoach", "UiPathCoach",
    "coach_report", "validate_coached_finding", "BoundaryViolation",
]


def make_coach(name: str | None):
    """Resolve a coach name (mock|vertex|uipath|none|None) to an instance.

    Centralises the lookup so CLI + publish + future tests share one map."""
    if not name or name == "none":
        return None
    if name == "mock":
        return MockCoach()
    if name == "vertex":
        return VertexCoach()
    if name == "uipath":
        return UiPathCoach()
    raise ValueError(f"unknown coach backend: {name}")
