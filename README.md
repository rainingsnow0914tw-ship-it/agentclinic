# AgentClinic

[![CI](https://github.com/rainingsnow0914tw-ship-it/agentclinic/actions/workflows/ci.yml/badge.svg)](https://github.com/rainingsnow0914tw-ship-it/agentclinic/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![UiPath: Coded Agent](https://img.shields.io/badge/UiPath-Coded%20Agent-FA4616.svg)](https://docs.uipath.com/)
[![Hackathon: Track 3](https://img.shields.io/badge/AgentHack%202026-Track%203-9333EA.svg)](https://uipath-agenthack.devpost.com/)

> Drop a trace in. Get a forensic report where every claim points at a trace event. Published natively into UiPath Test Cloud.

A pre-production clinic for AI agents. Every finding is bound to specific `trace_event_id`s as evidence — **no finding may exist without a span**. Reports land natively in UiPath Test Cloud as Test Sets / Executions / per-pattern Test Case Logs, so release gates that already use Test Cloud get agent quality for free.

**[繁體中文 README](README.zh-TW.md)** *(coming)* · **[Submission text](docs/SUBMISSION.md)** · **[Error matrix](docs/ERROR_MATRIX.md)** · **[PRD](PRD_AgentClinic_v1.md)**

---

## Why AgentClinic

- **Evidence-bound, not vibes-bound** — every finding has an `evidence_spans` list pointing at concrete trace events. A finding without an evidence span is a contract violation and is rejected by the schema.
- **Deterministic judge, bounded coach** — the rule engine produces the verdict; the LLM is only allowed to translate findings into remediation. No revising the score, no inventing findings.
- **Lives in the release gate you already have** — Test Cloud is the system of record. Re-running the same trace re-uses per-pattern Test Cases; quality history is queryable forever in Test Manager.
- **Native to UiPath, not a webhook shell** — Coded Agent on Automation Cloud. LLM rides AgentHub LLM Gateway under AI Trust Layer governance. No external API key.

## Why not [other approach]?

| Approach | Audit trail | Test Cloud integration | Score determinism | Governance | Re-runnable |
| --- | --- | --- | --- | --- | --- |
| **AgentClinic** | **Per-finding `trace_event_id` chain** | **Native Test Set + Execution + Case Log + attachment** | **Deterministic L0–L3 + versioned `rule_snapshot`** | **AI Trust Layer + Orchestrator audit** | **Idempotent on (project, pattern); re-uses Test Cases** |
| "Ask ChatGPT to review" | Free-form prose | None | LLM-mood | None | Different output each call |
| Eval harnesses (e.g. RAGAS) | Per-metric, no trace anchor | None | Mostly, but no Test Cloud surface | Local | Yes |
| Naive `langsmith` traces | Span-level view | None | N/A (it's a viewer) | Vendor cloud | Yes |
| In-house unit tests | Whatever you write | If you wire it | Whatever you write | Whatever you wire | Yes |

## How it works

```
Agent trace (JSON, schema: trace_schema_v1)
        ↓
  normalize  →  internal Evidence Contract
        ↓
   detect    →  7 waste-pattern detectors  →  findings (each with evidence_spans)
        ↓
    score    →  L0–L3 + token-waste $$ accounting
        ↓
    coach    →  (optional) LLM via UiPath AgentHub LLM Gateway, bounded
        ↓
  publish    →  UiPath Test Cloud
                  Project (idempotent)
                  └ Test Case (per waste pattern, reusable)
                    └ Test Set (per publish run)
                      └ Execution
                        └ Test Case Log + override-result reason
                          └ Attachment: full report.md
```

## Architecture · four roles, no overlap

| Role | What | Where |
| --- | --- | --- |
| 👨‍⚖️ **Judge** | Deterministic rule engine. Runs without an LLM. | `core/agentclinic/detect.py` + `score.py` |
| 🏃 **Coach** | LLM-bounded translator. Forbidden from judging. | `core/agentclinic/coach/uipath_llm.py` + `validator.py` |
| 📋 **Recorder** | Test Set + Execution + Case Log + Attachment chain. | UiPath Test Cloud (Test Manager REST v2) |
| 🎼 **Orchestrator** | Deployment runtime + audit + governance. | UiPath Orchestrator Process + AI Trust Layer |

## UiPath components used

| Component | Role |
| --- | --- |
| **Test Cloud (Test Manager)** | System of record — full chain via REST v2 |
| **Coded Agent (Function)** | Deployable unit — `uipath pack` / `uipath publish -t` |
| **Orchestrator Process** | Runtime — env-var-injected creds, `Start now` triggers a Cloud job |
| **AgentHub LLM Gateway** | Native LLM path — `{base}/agenthub_/llm/api/chat/completions`, OR.* scope, in-platform |
| **AI Trust Layer** | Audit + PII redaction — coach calls ride the platform's governance plane |
| **External Application + client_credentials** | Service-account auth (TM.* for publish, OR.* for coach; **mixed-audience is rejected**, each backend caches its own token — see `auth.py`) |
| **UiPath Python SDK 2.10.x** | `uipath init` / `run` / `pack` / `publish` |

## Agent type

**Coded Agent** (Python SDK, Function project type). No low-code agent component is used.

> **PRD pivot note.** `PRD_AgentClinic_v1.md` §6.2 originally targeted a Studio Web *Orchestrator Agent* as the visible main body. During P2/P3 the Coded-Agent-inside-Function-Project binding UI was found to still be in Preview and unstable (Call activity → Function binding silently drops arguments). The project pivoted to **Coded Agent → `uipath pack/publish` → Orchestrator Process → Cloud runtime** — still a first-class Studio Web ecosystem deployment unit, but avoiding the Preview surface. This is a production-readiness call, documented as `c3-coded-agent-runtime` tag.

## Track 3 alignment

| Track 3 brief asks for | AgentClinic |
| --- | --- |
| "Evaluate requirements → meaningful test scenarios" | Each waste pattern = one reusable Test Case in Test Cloud |
| "Identify fragile or outdated tests before they slow down a release" | 7 deterministic detectors with versioned `rule_snapshot` per finding — drift caught by golden regression |
| "Recommend fixes when automation breaks" | Report §4 (Remediation), per-finding, bounded by `coach/validator.py` |
| "Orchestrate the right tests at the right time based on risk, coverage, change impact" | Coded Agent invokable from any UiPath process; per-pattern Test Cases give risk-weighted coverage; Trust Layer + Orchestrator logs = audit trail |
| "Validate AI-infused workflows including third-party agents" | Trace schema is the only boundary; `source_signature` records which adapter produced the trace |

> **Shifts quality from a late-stage checkpoint into a continuous, intelligent, governed capability.** That's the brief, and that's the design.

---

## Install

### Option 1: Local dev (Python)

```powershell
git clone https://github.com/rainingsnow0914tw-ship-it/agentclinic.git
cd agentclinic
pip install jsonschema rfc3339-validator pydantic requests
mkdir .uipath
# Populate .uipath/app.json with your External App credentials (see Configuration below)
PYTHONPATH=core python -m agentclinic golden examples/golden_traces  # regression
PYTHONPATH=core python -m agentclinic publish examples/golden_traces/01_hard_hat_loop.golden.json --project-name "AgentClinic Reports v2" --project-prefix ACR2 --coach uipath
```

### Option 2: Coded Agent → Automation Cloud

```powershell
pip install "uipath>=2.10.0,<2.11.0"
uipath init --no-agents-md-override               # regenerate schema from main.py Pydantic
uipath run main --file <input>.json               # local SDK runtime validate
uipath pack                                       # → .uipath/agentclinic-coded-agent.0.1.1.nupkg
uipath auth --staging --client-id … --client-secret … --base-url … --scope "<OR.* only>"
uipath publish -t                                 # land on tenant package feed
```

Then in Orchestrator → folder → **Add process** → pick `agentclinic-coded-agent 0.1.1` → set Environment Configuration (see below) → **Start now** with `{"trace": <…>, "publish_to_test_cloud": true, "project_name": "AgentClinic Reports v2", "project_prefix": "ACR2"}`.

### Option 3: From a UiPath workflow

```python
from uipath.platform import UiPath
sdk = UiPath()
job = sdk.processes.invoke(
    name="agentclinic-coded-agent",
    input_arguments={"trace": trace_dict, "publish_to_test_cloud": True},
)
# Output object: {report: {...}, test_cloud: {ui_url: ...}, publish_error: None}
```

## Configuration

### Local dev — `.uipath/app.json`

```json
{
  "app_id":         "<External App id>",
  "app_secret":     "<External App secret>",
  "token_endpoint": "https://<region>.uipath.com/identity_/connect/token",
  "scope":          "TM.Projects TM.Projects.Read … TM.Attachments.Write OR.Execution",
  "base_url":       "https://<region>.uipath.com/<org>/<tenant>/testmanager_",
  "org":            "<org>",
  "tenant":         "<tenant>"
}
```

Gitignored. Each backend filters this scope to its own audience (TM.* for publish, OR.* for coach).

### Automation Cloud runtime — Process Environment Configuration

Paste into Orchestrator → Process → Environment Configuration (dotenv format):

```dotenv
UIPATH_APP_ID=<External App id>
UIPATH_APP_SECRET="<secret with special chars>"
UIPATH_TOKEN_ENDPOINT=https://<region>.uipath.com/identity_/connect/token
UIPATH_BASE_URL=https://<region>.uipath.com/<org>/<tenant>/testmanager_
UIPATH_SCOPE=TM.Projects TM.Projects.Read … TM.Attachments.Write
```

`load_config()` reads file first, env overrides field-by-field. Same code path, two deployment surfaces.

## Repository layout

```
.
├ main.py                    Coded Agent entry (Pydantic Input/Output)
├ pyproject.toml             Package metadata + runtime deps
├ entry-points.json          UiPath SDK schema (regenerated by `uipath init`)
├ LICENSE                    MIT
│
├ core/agentclinic/
│  ├ cli.py                  argparse: analyze / publish / golden / budget
│  ├ normalize.py            trace → Evidence Contract
│  ├ detect.py               7 waste-pattern detectors
│  ├ score.py                L0–L3 scorecard
│  ├ report.py               6-section report builder
│  ├ validate.py             schema validators
│  ├ coach/                  Coach role (mock / vertex / uipath_llm / validator)
│  ├ budget/                 Budget Guardian (deterministic burn-rate)
│  └ uipath/                 Test Cloud REST integration (auth/client/config/publish)
│
├ contracts/                 trace_schema_v1 + finding_schema_v1
├ examples/golden_traces/    5 regression goldens (L0–L3 score coverage)
├ scripts/                   Investigative probes (June 22 ACL debugging)
└ docs/                      PRD, plan, P2 spike, error matrix, submission pack
```

## Test Cloud evidence

Five golden traces published with `--coach uipath` to project **ACR2** on hackathon staging tenant `hackathon26_596`:

| Golden | Test Set | Execution | Result | Score |
| --- | --- | --- | --- | --- |
| `01_hard_hat_loop` | ACR2:79 | `0bffe91c` | 1 Failed | 0.0 / L3 |
| `02_clean_run` | ACR2:80 | `938e66e5` | 0 Failed | 100 / L0 |
| `03_redundant_and_full_read` | ACR2:81 | `608a0b2e` | 2 Failed | 70 / L1 |
| `04_unverified_claim_missing_tokens` | ACR2:82 | `8951d57b` | 1 Failed | 40 / L2 |
| `05_interleaved_think_retry` | ACR2:84 | `822668cc` | 1 Failed | 0.0 / L3 |

Each Test Case Log's override-result reason is multi-line, evidence-bound:

```
AgentClinic detected pattern `hard_hat_loop` -- 1 finding(s):
  RM-F-trace_gold_001-001 | severity=critical confidence=0.9 | events: evt_0002, evt_0003, evt_0004
Evidence-bound by finding_schema_v1; see attached report.
```

Plus full `report.md` attached to each execution.

## Three iron rules

These come from the project's RaidMeter DNA and govern every implementation decision:

1. **Zero hallucination** — missing data → `unknown` + gap entry, never a guess.
2. **No single-signal verdict** — pattern detection needs multi-factor evidence.
3. **Coach not surveillance** — engineer keeps every decision; coach translates, doesn't command.

See `PRD_AgentClinic_v1.md` §13.

## Coding agent · Claude Code (AgentHack +2 bonus)

**Every line of source, every commit message, every documentation file in this repository was written by Claude Code** in a long-running pair-programming session with the project driver. Sixteen commits across eleven days:

```
0185de6  P1: AgentClinic core v0.1.0 — deterministic evidence-bound forensics
7a0cdbd  P2 spike: Test Cloud write verification
737ab08  Budget Guardian v0.1: deterministic burn-rate forecaster
cb4b9e6  Report Section 7: Budget & Runway Analysis
3825dc8  P2 v1: uipath module + publish CLI
33d454c  P2 v2: full Test Cloud chain
8db3bdd  P4: LLM coaching layer with hard boundary
f8decfa  P4 native: UiPathCoach via AgentHub LLM Gateway
9a6c3df  C1: evidence-bound testcaselog reason
8ca19ae  C3: Coded Agent runtime invokes publish
aefb1f4  C3 hotfix 0.1.1: add requests to runtime deps
+ 5 more (init, docs, tagging, scope-filter fix)
```

The human role was **driver / domain oracle**: framing the problem space, vetting LLM platform discoveries ("UiPath puts LLM Gateway under `/agenthub_/llm/api`, not `/llmgateway_/` — here's the source-code grep that found it"), approving architecture pivots, performing the GUI actions Claude cannot, and stepping in when Claude overreached (the day Claude proposed running 36 verification subagents and burned 5 hours of the driver's API window directly produced the project's "hand-raised" protocol).

That back-and-forth — Claude proposing, driver correcting, both updating the project memory of what works — is the actual collaboration pattern. Not "snippet suggestions," but substantive integration where Claude Code produced and committed the complete working solution.

Investigative scripts and docs are also Claude-Code-authored: `docs/P2_SPIKE_RESULT.md` (the forensic write-up of how the Test Manager API was reverse-engineered from SDK source), `scripts/probe_*.py` (the five debug scripts that surfaced the (logId, currentResult) unique constraint), and the three iron rules in PRD §13.

## Production error handling

The seven failure modes called out in PRD §7 — broken JSON / unsupported schema / missing fields / LLM timeout / duplicate writes / partial publish failure / golden suite crash — each map to a concrete implementation site with line numbers in **[`docs/ERROR_MATRIX.md`](docs/ERROR_MATRIX.md)**.

Exit-code contract:

| Code | Meaning |
| --- | --- |
| 0 | Ok — golden suite green / analyze published / report written |
| 1 | Analysis-level failure (publish error, golden FAIL) |
| 2 | Input-level failure (broken JSON, schema rejected, file missing) |

## Privacy & security

- `.uipath/app.json` and `.env` are gitignored. `git ls-files | grep -E '\.uipath/|\.env'` returns nothing.
- The Coded Agent runtime reads credentials from env vars set on the Orchestrator Process (or, in production, from Orchestrator Asset credentials via `sdk.assets.retrieve_credential()`).
- All LLM calls go through UiPath AI Trust Layer — audit log + PII redaction handled at the platform layer, not the application.
- No external LLM API key. No third-party billing. No data leaves the UiPath tenant.

## Troubleshooting

### `invalid_scope` on `client_credentials` token exchange

You're mixing TM.* and OR.* audiences in one exchange. UiPath identity rejects that. Filter to one audience per backend; see `auth.py:50`.

### `ModuleNotFoundError: No module named 'requests'` on Cloud runtime

Your `pyproject.toml` is missing `requests`. The Cloud runtime is a fresh install; only `pyproject.toml` deps are present. Fixed in v0.1.1.

### "You do not have the necessary rights to access this application" in Test Manager UI

Three independent permission layers, none of which error helpfully on its own:

1. Project member with a role (set via `/api/v2/{projectId}/permissions/project/assignroles`).
2. Tenant Administrator role (set via Admin → Manage Access → Assign role).
3. Test Manager license seat (set via Admin → Licenses → Edit license allocation → Allocate to User → Pro).

You need all three. The setup section above walks through it; `scripts/d_assign_ck_owner.py` automates #1.

### Override-result POST returns HTTP 409 `duplicateUniqueConstraint`

`(testCaseLogId, currentResult)` is a unique constraint. Re-posting an override fails. Recovery path: PUT against the existing override row, or write a new TestCaseLog under a new Execution. See `docs/ERROR_MATRIX.md` row 5.

## Acknowledgements

- **Driver:** 司機先生 — domain framing, GUI actions, the hand-raised protocol that saved the project from burning the API window.
- **Product lead:** Chloe Kao — vision, voice, and the three iron rules.
- **Platform intelligence:** Percy (Perplexity) — UiPath ecosystem reconnaissance, hackathon rule interpretation.
- **Production architecture review:** 曦 (GPT-5.5) — the 4-roles-no-overlap discipline, the 17-day milestone plan, the Evidence Contract framing.
- **Code & docs:** [Claude Code](https://claude.com/claude-code) (Anthropic) — every commit, every schema, every page of this repository.

## License

MIT — see [LICENSE](LICENSE).

The MIT license covers AgentClinic original solution code only. UiPath proprietary tools, activities, SDK packages, and platform components referenced or used within remain subject to their own license terms.
