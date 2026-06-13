"""Coach protocol -- duck-typed callable returning a `CoachResult`.

A coach takes a single finding (already validated against finding_schema_v1)
and returns either a rewritten remediation string or an explicit failure
marker. The orchestrator (`apply.coach_report`) handles fallback when a
coach fails or its output violates the boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class CoachResult:
    """A coach's output for one finding.

    `remediation` is the rewritten text (None if the coach declined / failed).
    `provenance` carries enough info to audit later: which backend, which
    model, any error. It is attached to the report's `_coach_diagnostics`
    array, never to the finding itself."""
    remediation: str | None
    backend: str
    model: str | None = None
    error: str | None = None
    raw_response: str | None = None
    extra: dict = field(default_factory=dict)


class Coach(Protocol):
    """Anything callable with `.coach(finding, trace) -> CoachResult` is
    a coach. Use the Protocol for typing only; subclassing is not required."""

    backend_name: str

    def coach(self, finding: dict, trace: dict) -> CoachResult: ...
