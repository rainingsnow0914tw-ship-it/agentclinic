# AgentClinic Core (v0.1.0)

Deterministic, evidence-bound forensic analysis of AI agent execution traces.
This is the **judge** of the four-role architecture — it runs with no LLM, no
network, no cloud. Same trace + same config = same report, every time.

```
Trace Evidence Contract → Deterministic Score → Evidence-backed Finding → (P2) Test Cloud Record
判官 = rule engine（這個包）｜教練 = LLM（P4，受約束）｜紀錄 = Test Cloud（P2）｜編排 = UiPath（P2）
```

## Quickstart

```powershell
# from the AI情報員 directory
$env:PYTHONPATH = "RaidMeter-UiPath\core"

# analyze one trace → six-section report
python -m agentclinic analyze RaidMeter-UiPath\examples\golden_traces\01_hard_hat_loop.golden.json

# budget guardian: pre-run token-budget burn-rate forecast + warning level
python -m agentclinic budget RaidMeter-UiPath\examples\golden_budget\04_time_race_parallel_amplifier.golden.json

# CI gate: run all golden suites (trace + budget auto-dispatch by "kind" field)
python -m agentclinic golden RaidMeter-UiPath\examples\golden_traces
python -m agentclinic golden RaidMeter-UiPath\examples\golden_budget
```

Dependency: `python -m pip install --user jsonschema`

## Architecture（一功能一檔）

| File | Role |
|---|---|
| `normalize.py` | input boundary — validate trace against contract, surface data gaps (never guess) |
| `detect.py` | 7 waste-pattern detectors + suppression engine; emits contract-valid findings |
| `score.py` | deterministic scorecard (severity weights → level L0–L3 → level cap) |
| `report.py` | six-section report; Section 5 (gaps) is guaranteed non-empty by validator |
| `validate.py` | schema boundary — every input trace and every output finding is validated |
| `cli.py` | `analyze` + `budget` + `golden` commands; golden auto-dispatches trace vs budget by `"kind"` field |
| `budget/guardian.py` | Budget Guardian v0.1 — deterministic burn-rate forecaster. Input → projection → warning level → recommended action; each output number carries `basis` (how + uncertainty). Same blood as the judge: no LLM, offline. |

## 配置驅動（調規則不動 code）

| Config | Controls |
|---|---|
| `config/rules.json` | per-pattern: enabled / severity / confidence / thresholds / keywords / suppression / remediation text |
| `config/scorecard.json` | severity weights, level rules, level caps |
| `config/report_templates.json` | section titles, gap texts, next-step suggestions |
| `budget/budget_rules.json` | budget thresholds (yellow/orange/red/freeze %), action map per user_goal, level shifts per task_mode/user_goal, deadline floor escalation, first-sample calibration (2026-06-13 token incident) |

Override at runtime: `--rules path --scorecard path`, contracts dir via
`AGENTCLINIC_CONTRACTS` env var.

## Honesty guarantees (enforced, not aspirational)

- **No finding without evidence**: every finding is validated against
  `finding_schema_v1` — missing evidence span = crash, by design.
- **Never guess**: missing token fields → waste = `null` + basis says why;
  missing state_hash → loop detectors skip and the gap is reported.
- **Section 5 never empty**: the report validator rejects a report that
  claims to see everything.
- **No single-signal verdict**: e.g. `hard_hat_loop` requires a chain of
  retries with unchanged state, not one event.
- **Budget Guardian refuses to guess usage**: if user did not read the
  Claude App settings page (`current_app_usage_percent: null`), engine emits
  `warning_level: unknown` + `recommended_action: ask_human_decision`.
  Better than fabricating a percent that misleads the next decision.
- **Deadline floor beats personal preference**: in Budget Guardian, the
  task-mode and user-goal can lower the warning level (more aggressive),
  but the deadline-based escalation is a floor — objective risk can't be
  cancelled by preference. Prevents `time_race_parallel` blind spots.

## Error matrix (per 曦's production review)

| Input | Behavior |
|---|---|
| broken / non-contract JSON | exit 2, schema error message, nothing analyzed |
| missing token fields | analysis proceeds, waste marked unknown, gap reported |
| missing state_hash | state-based detectors skip (no guessing), gap reported |
| duplicate run | `idempotency_key` carried in contract (dedup is the P2 service's job) |

## Roadmap

- **P2 (6/15–18)**: UiPath wrap — Studio Web Orchestrator Agent 為主體,
  this core packaged as a Coded Agent (`uipath pack` / `uipath publish`),
  findings written to **Test Cloud** (Test Set / Execution / Case Log).
  ⚠️ Test Cloud write spike due **before 6/15**.
- **P4 (6/22–24)**: bounded LLM coaching — LLM may rewrite wording of
  deterministic findings; it may not re-judge, re-score, or add findings.
- Redaction layer before anything leaves the machine (P2).
- Model pricing table config → USD waste estimates.

— Code 阿寶 2026-06-13 · part of UiPath AgentHack 2026 Track 3 (PRD: ../PRD_AgentClinic_v1.md)
