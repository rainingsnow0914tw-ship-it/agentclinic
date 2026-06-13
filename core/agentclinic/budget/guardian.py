"""Budget Guardian -- deterministic, offline burn-rate forecaster.

Inputs come from the user (the only honest source for window usage percent is
the Claude App settings page, which the user reads and types in). Outputs are
evidence-bound projections + a warning level + a recommended action; every
number's provenance lives in the `basis` field, matching the trace-finding
contract.

No LLM, no cloud, no random."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_RULES_PATH = Path(__file__).parent / "budget_rules.json"

LEVELS = ["green", "yellow", "orange", "red", "freeze"]
_ICONS = {
    "green": "G", "yellow": "Y", "orange": "O", "red": "R", "freeze": "F",
    "unknown": "?",
}


def load_rules(path: str | Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_RULES_PATH
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def assess(inp: dict, rules: dict | None = None) -> dict:
    rules = rules or load_rules()

    usage = inp.get("current_app_usage_percent")
    minutes_into = inp.get("minutes_into_window")
    deadline = inp.get("deadline_minutes")
    parallel = inp.get("planned_parallel_agents") or 1
    task_mode = inp.get("task_mode", "balanced")
    user_goal = inp.get("user_goal", "balanced")
    reserve = inp.get("reserve_percent",
                      rules.get("default_reserve_percent", 15))

    if usage is None:
        return _unknown(
            inp,
            reason="current_app_usage_percent missing -- Claude App settings "
            "page must be manually read; refuse to guess",
        )

    remaining = 100 - usage
    burn = _burn_rate(usage, minutes_into)
    projected = _projected_exhaustion(remaining, burn, parallel)

    base_level_idx = _classify_level(usage, rules["thresholds"])

    if remaining <= reserve:
        level_idx = 4
        deadline_shift = 0
        mode_shift = 0
        goal_shift = 0
        level_basis_extra = (f"remaining {remaining:.1f}% <= reserve "
                             f"{reserve}% -- freeze floor")
    else:
        shifts = rules.get("level_shift", {})
        mode_shift = shifts.get("by_task_mode", {}).get(task_mode, 0)
        goal_shift = shifts.get("by_user_goal", {}).get(user_goal, 0)
        deadline_shift, deadline_note = _deadline_escalation(
            projected, deadline, rules)
        # personal preference (mode/goal) can lower level; objective deadline
        # risk is a floor that personal preference cannot cancel
        personal_level = _clamp(base_level_idx + mode_shift + goal_shift)
        objective_level = _clamp(base_level_idx + deadline_shift)
        level_idx = max(personal_level, objective_level)
        if objective_level > personal_level and deadline_note:
            level_basis_extra = (f"deadline floor wins: objective "
                                 f"{LEVELS[objective_level]} > personal "
                                 f"{LEVELS[personal_level]} ({deadline_note})")
        else:
            level_basis_extra = deadline_note

    level = LEVELS[level_idx]
    action = _pick_action(level, user_goal, rules)

    basis = _build_basis(
        usage=usage, remaining=remaining, burn=burn, projected=projected,
        parallel=parallel, minutes_into=minutes_into,
        base_level=LEVELS[base_level_idx], level=level,
        task_mode=task_mode, user_goal=user_goal,
        mode_shift=mode_shift, goal_shift=goal_shift,
        deadline_shift=deadline_shift, level_basis_extra=level_basis_extra,
        action=action,
    )
    alerts = _build_alerts(
        level=level, burn=burn, projected=projected, deadline=deadline,
        remaining=remaining, parallel=parallel, reserve=reserve)

    return {
        "schema_version": "budget-v0.1",
        "estimated_remaining_percent": _round(remaining, 1),
        "burn_rate_percent_per_min": _round(burn, 3),
        "projected_exhaustion_minutes": _round(projected, 0),
        "warning_level": level,
        "recommended_action": action,
        "basis": basis,
        "alerts": alerts,
        "inputs_echo": {
            "plan_name": inp.get("plan_name"),
            "current_app_usage_percent": usage,
            "current_session_tokens": inp.get("current_session_tokens"),
            "window_minutes": inp.get("window_minutes"),
            "minutes_into_window": minutes_into,
            "deadline_minutes": deadline,
            "reserve_percent": reserve,
            "planned_parallel_agents": parallel,
            "task_mode": task_mode,
            "user_goal": user_goal,
        },
    }


def _classify_level(usage: float, thresholds: dict) -> int:
    for i in range(len(LEVELS) - 1, 0, -1):
        if usage >= thresholds.get(LEVELS[i], 999):
            return i
    return 0


def _burn_rate(usage: float, minutes_into: float | None) -> float | None:
    if minutes_into is None or minutes_into <= 0:
        return None
    return usage / minutes_into


def _projected_exhaustion(
    remaining: float, burn: float | None, parallel: int,
) -> float | None:
    if burn is None or burn <= 0:
        return None
    effective_burn = burn * max(1, parallel)
    return remaining / effective_burn


def _deadline_escalation(
    projected: float | None, deadline: float | None, rules: dict,
) -> tuple[int, str | None]:
    if projected is None or deadline is None or deadline <= 0:
        return 0, None
    esc = rules.get("deadline_escalation", {})
    if projected < deadline * 0.5:
        shift = esc.get("shift_if_projected_lt_half_deadline", 2)
        return shift, (f"projected exhaustion {projected:.0f}min < 50% of "
                       f"deadline {deadline}min -- +{shift}")
    if projected < deadline:
        shift = esc.get("shift_if_projected_lt_deadline", 1)
        return shift, (f"projected exhaustion {projected:.0f}min < deadline "
                       f"{deadline}min -- +{shift}")
    return 0, None


def _clamp(i: int, lo: int = 0, hi: int = 4) -> int:
    return max(lo, min(hi, i))


def _pick_action(level: str, user_goal: str, rules: dict) -> str:
    pref = rules.get("primary_by_user_goal", {}).get(user_goal, {})
    if level in pref:
        return pref[level]
    actions = rules["level_actions"].get(level, ["continue"])
    return actions[0]


def _round(x: float | None, ndigits: int) -> float | None:
    return None if x is None else round(x, ndigits)


def _basis(value: Any, how: str, uncertainty: str) -> dict:
    return {"value": value, "how": how, "uncertainty": uncertainty}


def _build_basis(*, usage, remaining, burn, projected, parallel, minutes_into,
                 base_level, level, task_mode, user_goal,
                 mode_shift, goal_shift, deadline_shift, level_basis_extra,
                 action) -> dict:
    burn_how = (
        f"current_app_usage_percent / minutes_into_window "
        f"(={usage}% / {minutes_into}min)"
        if burn is not None else
        "minutes_into_window missing or 0 -- burn rate unknown"
    )
    proj_how = (
        f"remaining_percent / (burn x max(1, parallel)) "
        f"(={remaining:.1f}% / {burn:.3f} x {parallel})"
        if projected is not None else
        "burn rate unknown -- projection unavailable"
    )
    level_how_parts = [f"base {base_level} from thresholds"]
    if mode_shift:
        level_how_parts.append(f"task_mode={task_mode} ({mode_shift:+d})")
    if goal_shift:
        level_how_parts.append(f"user_goal={user_goal} ({goal_shift:+d})")
    if deadline_shift:
        level_how_parts.append(f"deadline ({deadline_shift:+d})")
    return {
        "estimated_remaining_percent": _basis(
            round(remaining, 1),
            f"100 - current_app_usage_percent (={usage}%)",
            "user-supplied percent -- Claude App may lag 5-10 min; window "
            "reset boundary not exact"),
        "burn_rate_percent_per_min": _basis(
            _round(burn, 3), burn_how,
            "assumes linear burn from window start; actual is often slower "
            "early (setup) and faster late (parallel work)"),
        "projected_exhaustion_minutes": _basis(
            _round(projected, 0), proj_how,
            "extrapolates current burn rate; large changes in parallel "
            "agent count or task shape break the projection"),
        "warning_level": _basis(
            level, " + ".join(level_how_parts),
            level_basis_extra or "thresholds in budget_rules.json"),
        "recommended_action": _basis(
            action,
            f"level={level} mapped via primary_by_user_goal[{user_goal}] "
            f"or level_actions[{level}][0]",
            "user_goal + task_mode shape action choice; override by passing "
            "different goal/mode"),
    }


def _build_alerts(*, level, burn, projected, deadline, remaining,
                  parallel, reserve) -> list[str]:
    icon = _ICONS.get(level, "?")
    parts = [f"[{icon}] {level}"]
    if burn is not None:
        parts.append(f"burn rate {burn:.2f}%/min")
    if projected is not None:
        parts.append(f"projected exhaustion in {projected:.0f}min")
    if deadline is not None and projected is not None:
        gap = projected - deadline
        if gap < 0:
            parts.append(f"deadline {deadline}min -- {-gap:.0f}min short")
        else:
            parts.append(f"deadline {deadline}min -- {gap:.0f}min slack")
    if parallel > 1:
        parts.append(f"parallel={parallel}x amplifier")
    if remaining is not None and remaining <= reserve:
        parts.append(f"reserve {reserve}% floor hit")
    return [" -- ".join(parts)]


def _unknown(inp: dict, reason: str) -> dict:
    return {
        "schema_version": "budget-v0.1",
        "estimated_remaining_percent": None,
        "burn_rate_percent_per_min": None,
        "projected_exhaustion_minutes": None,
        "warning_level": "unknown",
        "recommended_action": "ask_human_decision",
        "basis": {
            "warning_level": _basis(
                "unknown", "input insufficient", reason),
            "recommended_action": _basis(
                "ask_human_decision",
                "level=unknown -- never auto-recommend; defer to user",
                reason),
        },
        "alerts": [f"[?] unknown: {reason}"],
        "inputs_echo": dict(inp),
    }


def to_markdown(assessment: dict) -> str:
    lines = [
        f"# Budget Guardian -- {assessment['warning_level']}",
        "",
        f"**Action**: `{assessment['recommended_action']}`",
        "",
    ]
    if assessment["alerts"]:
        lines.append("## Alerts")
        for a in assessment["alerts"]:
            lines.append(f"- {a}")
        lines.append("")
    rem = assessment["estimated_remaining_percent"]
    burn = assessment["burn_rate_percent_per_min"]
    proj = assessment["projected_exhaustion_minutes"]
    lines.extend([
        "## Numbers",
        "| remaining | burn rate | projected exhaustion |",
        "|---|---|---|",
        f"| {rem}% | {burn}%/min | {proj}min |",
        "",
        "## Basis (evidence-bound)",
    ])
    for k, v in assessment["basis"].items():
        lines.append(f"- **{k}** = `{v['value']}`")
        lines.append(f"  - how: {v['how']}")
        lines.append(f"  - uncertainty: {v['uncertainty']}")
    return "\n".join(lines)
