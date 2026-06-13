"""Deterministic scorecard. Same findings + same scorecard config = same
score, always. All weights, level rules and caps live in config/scorecard.json."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_SCORECARD_PATH = Path(__file__).parent / "config" / "scorecard.json"

SEVERITIES = ("critical", "high", "medium", "low")


def load_scorecard(path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_SCORECARD_PATH, encoding="utf-8") as f:
        return json.load(f)


def score(findings: list[dict], scorecard: dict) -> dict:
    counts = {sev: 0 for sev in SEVERITIES}
    for f in findings:
        counts[f["severity"]] += 1

    weights = scorecard["severity_weights"]
    deduction = sum(weights[f["severity"]] for f in findings)
    raw = scorecard["base_score"] - deduction

    level = scorecard["default_level"]
    for rule in scorecard["levels"]:
        if any(
            all(counts[sev] >= n for sev, n in cond.items())
            for cond in rule["any_of"]
        ):
            level = rule["level"]
            break

    cap = scorecard["level_caps"][level]
    value = max(0.0, min(raw, cap))
    return {
        "value": round(value, 1),
        "level": level,
        "weighted_deduction": deduction,
        "severity_counts": counts,
        "scorecard_version": scorecard["scorecard_version"],
    }
