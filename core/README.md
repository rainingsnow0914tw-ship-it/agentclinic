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

# CI gate: run the golden-trace regression suite (all must pass before any deploy)
python -m agentclinic golden RaidMeter-UiPath\examples\golden_traces
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
| `cli.py` | `analyze` + `golden` commands; golden comparator is the CI gate |

## 配置驅動（調規則不動 code）

| Config | Controls |
|---|---|
| `config/rules.json` | per-pattern: enabled / severity / confidence / thresholds / keywords / suppression / remediation text |
| `config/scorecard.json` | severity weights, level rules, level caps |
| `config/report_templates.json` | section titles, gap texts, next-step suggestions |

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
