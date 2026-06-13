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

# publish: analyze + push report to UiPath Test Cloud (needs .uipath/app.json)
python -m agentclinic publish RaidMeter-UiPath\examples\golden_traces\01_hard_hat_loop.golden.json --budget-input RaidMeter-UiPath\examples\golden_budget\04_time_race_parallel_amplifier.golden.json
```

Dependency for `publish`: `python -m pip install --user requests`

Dependency: `python -m pip install --user jsonschema`

## Architecture（一功能一檔）

| File | Role |
|---|---|
| `normalize.py` | input boundary — validate trace against contract, surface data gaps (never guess) |
| `detect.py` | 7 waste-pattern detectors + suppression engine; emits contract-valid findings |
| `score.py` | deterministic scorecard (severity weights → level L0–L3 → level cap) |
| `report.py` | six-section report; Section 5 (gaps) is guaranteed non-empty by validator |
| `validate.py` | schema boundary — every input trace and every output finding is validated |
| `cli.py` | `analyze` + `budget` + `golden` + `publish` commands; golden auto-dispatches trace vs budget by `"kind"` field |
| `budget/guardian.py` | Budget Guardian v0.1 — deterministic burn-rate forecaster. Input → projection → warning level → recommended action; each output number carries `basis` (how + uncertainty). Same blood as the judge: no LLM, offline. |
| `uipath/config.py` | resolve `.uipath/app.json` + `UIPATH_*` env overrides; validate required fields (app_id / app_secret / token_endpoint / scope / base_url) |
| `uipath/auth.py` | client_credentials OAuth exchange + in-process token cache (keyed by token_endpoint+app_id, refreshed 60s early). PAT path is documented dead-end (see `docs/P2_SPIKE_RESULT.md`). |
| `uipath/client.py` | thin Test Manager REST wrapper — `list_projects`, `find_project_by_name`, `create_project`, `ensure_project` (idempotent), `create_testcase`, `upload_attachment`. No business logic. |
| `uipath/publish.py` | report → Test Cloud full chain: ensure project (idempotent on name) → ensure testcase per detected pattern (idempotent on `pattern:<name>`) → create TestSet (`run:<trace>/<run>`) → assign testcases → create TestExecution → create TestCaseLog per testcase → override-result (Failed if pattern fired, Passed if clean) → attach markdown report on TestExecution. Returns flat tracking ids + UI url. |

## 配置驅動（調規則不動 code）

| Config | Controls |
|---|---|
| `config/rules.json` | per-pattern: enabled / severity / confidence / thresholds / keywords / suppression / remediation text |
| `config/scorecard.json` | severity weights, level rules, level caps |
| `config/report_templates.json` | section titles, gap texts, next-step suggestions |
| `config/model_pricing.json` | model -> {input, output} per-million-tokens USD; Section 3 uses trace in/out ratio to weight a per-token blended price (override: `--pricing path`) |
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

- ✅ **P2 spike (2026-06-13)**: Test Cloud write proven via REST + External
  App; see `docs/P2_SPIKE_RESULT.md`.
- ✅ **P2 v1 (2026-06-13)**: spike chain Python-ised as `uipath/` module +
  `publish` CLI; idempotent project, foreignReference-tracked testcase,
  markdown report attachment.
- ✅ **P2 v2 (2026-06-13)**: full Test Cloud chain — project → per-pattern
  testcase → testset → execution → testcaselog with Passed/Failed override
  derived from findings → markdown attachment on the execution. Each
  AgentClinic detector becomes a reusable Quality Test in Test Manager;
  each trace is one run of that suite.
- **P2 v3 (6/15–18)**: Studio Web Orchestrator Agent as host body, this
  core packaged as a Coded Agent (`uipath pack` / `uipath publish`).
- **P4 (6/22–24)**: bounded LLM coaching — LLM may rewrite wording of
  deterministic findings; it may not re-judge, re-score, or add findings.
- ✅ **Model pricing (2026-06-13)**: trace-aggregate USD via
  `config/model_pricing.json`. trace.model + in/out token ratio drive
  a weighted per-token price; pricing entry missing emits
  `pricing_entry_missing` gap with the model name baked in.
- Redaction layer before anything leaves the machine.

— Code 阿寶 2026-06-13 · part of UiPath AgentHack 2026 Track 3 (PRD: ../PRD_AgentClinic_v1.md)
