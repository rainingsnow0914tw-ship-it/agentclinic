"""Mock coach -- deterministic template-based rephrasing.

Production use: the CI gate. Demo use: when no live LLM is configured.
Same backend interface as VertexCoach so swapping in / out is a one-line
config change."""
from __future__ import annotations

from .base import CoachResult


class MockCoach:
    """Deterministic, offline, no-LLM coach. Wraps the original remediation
    with a coaching framing -- enough to be visibly *different* (so report
    consumers see the coach ran) without altering meaning or judgement."""

    backend_name = "mock"

    def __init__(self, prefix: str = "Try this:",
                 suffix: str = "(Coached by Mock; no LLM involved.)"):
        self.prefix = prefix
        self.suffix = suffix

    def coach(self, finding: dict, trace: dict) -> CoachResult:
        original = finding["remediation"]
        pattern = finding["pattern"]
        sev = finding["severity"]
        # action verbs vary by severity so different findings read differently
        opener = {
            "critical": "Stop and fix immediately:",
            "high":     "Address this before merging:",
            "medium":   "Address this in the next iteration:",
            "low":      "Worth a small refactor:",
        }.get(sev, self.prefix)
        rewritten = (
            f"{opener} {original} (Pattern: `{pattern}`, severity {sev}. "
            f"{self.suffix})"
        )
        return CoachResult(
            remediation=rewritten,
            backend=self.backend_name,
            model="mock-deterministic",
            extra={"pattern": pattern, "severity": sev},
        )
