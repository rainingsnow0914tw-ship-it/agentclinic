"""Boundary check between an original finding and its coached version.

The coach may only touch `remediation` (free-text). Everything else must
be byte-for-byte identical. A violation is recorded; the finding falls
back to its original remediation."""
from __future__ import annotations

# fields the coach is forbidden to change; this is the contract
IMMUTABLE_FIELDS = (
    "finding_id", "pattern", "severity", "confidence",
    "evidence_spans", "estimated_waste", "impacted_metric", "replay",
)

# words that hint at re-judgement and are banned from coached text
JUDGE_RESERVED_WORDS = (
    "might be fine", "could be fine", "i think this is",
    "actually this is", "downgrade", "upgrade severity",
    "reclassify", "re-classify", "more severe than",
    "less severe than", "not actually a problem",
    "false positive", "false-positive",
)


class BoundaryViolation(ValueError):
    """Raised by validate_coached_finding when the coach overstepped."""


def validate_coached_finding(original: dict, coached_remediation: str) -> None:
    """Pure-check the coach's output. Pass the *string* it produced;
    we never let the coach return a dict that could shadow other fields.
    Raises BoundaryViolation with a specific message on the first bad
    signal we hit."""
    if not isinstance(coached_remediation, str):
        raise BoundaryViolation(
            f"coached remediation must be str, got "
            f"{type(coached_remediation).__name__}")
    stripped = coached_remediation.strip()
    if not stripped:
        raise BoundaryViolation("coached remediation is empty")
    if len(stripped) > 2000:
        raise BoundaryViolation(
            f"coached remediation length {len(stripped)} exceeds 2000-char "
            "ceiling (suspect runaway model)")
    lower = stripped.lower()
    for word in JUDGE_RESERVED_WORDS:
        if word in lower:
            raise BoundaryViolation(
                f"coached remediation contains judge-reserved phrase "
                f"`{word}` -- coach attempted to re-judge")
    # paranoid sanity check: original finding fields must still be the
    # ones we'll keep; this is called pre-application so the contract
    # is on `original` staying untouched downstream
    for field in IMMUTABLE_FIELDS:
        if field not in original:
            raise BoundaryViolation(
                f"original finding missing required field `{field}` -- "
                "cannot validate coach safely")
