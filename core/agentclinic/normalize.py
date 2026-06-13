"""Input boundary: validate the raw trace and surface data gaps.

The normalizer never guesses. Absent fields stay absent and are reported as
gaps; each downstream stage decides per rule whether to skip, degrade
confidence, or mark an estimate unknown."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .validate import TraceSchemaError, validate_trace


def load_trace_file(path: str | Path) -> dict:
    """Load a trace JSON file. Golden-trace files (which wrap the trace in
    an ``input_trace`` key) are unwrapped automatically."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "input_trace" in data:
        return data["input_trace"]
    return data


def normalize(trace: dict) -> tuple[dict, list[dict]]:
    """Validate the trace against the contract and collect data gaps.

    Returns (trace, gaps). Each gap: {"key": str, "count": int}.
    Event order in the array is treated as execution order; events are not
    re-sorted by timestamp."""
    validate_trace(trace)

    events = trace["events"]
    id_counts = Counter(ev["event_id"] for ev in events)
    dupes = sorted(i for i, n in id_counts.items() if n > 1)
    if dupes:
        raise TraceSchemaError(
            f"duplicate event_id values {dupes} — event ids must be unique "
            "within a trace (evidence and suppression are keyed by event_id)"
        )
    missing_tokens = sum(
        1 for ev in events if "token_in" not in ev or "token_out" not in ev
    )
    missing_state = sum(1 for ev in events if "state_hash" not in ev)

    gaps: list[dict] = []
    if missing_tokens:
        gaps.append({"key": "missing_token_fields", "count": missing_tokens})
    if missing_state:
        gaps.append({"key": "missing_state_hash", "count": missing_state})
    if "model" not in trace:
        gaps.append({"key": "missing_model", "count": 1})
    return trace, gaps


def detect_pricing_gap(trace: dict, pricing: dict) -> dict | None:
    """Emitted by build_report after USD calculation. Lives here in
    normalize.py so all gap shapes stay in one place."""
    model = trace.get("model")
    if not model:
        return None
    if model in pricing.get("models", {}):
        return None
    return {"key": "pricing_entry_missing", "count": 1, "model": model}
