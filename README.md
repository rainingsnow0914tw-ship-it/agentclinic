# AgentClinic — UiPath AgentHack 2026 · Track 3 (Agentic Testing)

> **AI agent 上線前的「體檢診所」.** Drop a trace in, get a forensic
> report where every finding points at the trace event it came from,
> published natively into UiPath Test Cloud as Test Sets, Executions,
> and per-pattern Test Case Logs. Quality is no longer a late-stage
> checkpoint — it's a continuous, governed capability you can wire into
> any release gate.

---

## 1 · Project Description

**The problem.** AI agents are entering production without the
testing discipline traditional software has had for decades.
"It worked on my machine" gets multiplied by "and the LLM happened to
behave that day." Existing test harnesses score outputs but rarely
explain *why* a run was wasteful, where the evidence for that judgment
lives in the trace, or what to change next time. The result: review
PRs by feel, ship and pray, debug post-incident.

**What AgentClinic does.** Given an agent's execution trace, it runs
a fixed forensic pipeline:

1. **Normalize** the trace against a versioned schema
   (`contracts/trace_schema_v1.json`).
2. **Detect** seven well-defined waste patterns
   (`hard_hat_loop`, `state_unchanged_retry`, `lucky_guess`,
   `agent_piling_on`, `full_file_read_before_grep`,
   `redundant_tool_call`, `completion_claim_without_verification`),
   each finding bound to specific `trace_event_id`s as evidence —
   **no finding may exist without an evidence span**.
3. **Score** the run on a deterministic L0–L3 scorecard, with token-
   waste accounting in tokens *and* USD.
4. **Coach** (optional) — an LLM translates findings into actionable
   remediation, hard-bounded to the deterministic verdict (no new
   findings, no reversed scores).
5. **Publish** the report natively into UiPath Test Cloud: one
   reusable Test Case per pattern, one Test Set + Execution per
   publish run, per-testcase log with override-result reason
   containing the finding chain, plus the full markdown report
   attached to the execution.

**Why this matters for Track 3.** The Track 3 brief asks for agentic
testing that "shifts quality from a late-stage checkpoint into a
continuous, intelligent, and governed capability." AgentClinic is
**meta-testing**: a UiPath-orchestrated agent that tests other AI
agents, with every claim traceable back to evidence in the trace and
every result landing in Test Cloud where existing release gates can
already act on it. The same pipeline validates UiPath-native agents,
third-party agents, and AI-infused workflows — the trace schema is the
boundary, not the agent framework.

---

## 2 · UiPath Components Used

| Component | Role |
|---|---|
| **UiPath Test Cloud (Test Manager)** | System of record — Test Set / Test Execution / Test Case Log / attachment chain via REST API v2 |
| **UiPath Coded Agent (Function)** | Deployable unit — `uipath pack` packages `main.py` + `core/agentclinic/`, `uipath publish -t` lands it on the tenant package feed |
| **UiPath Orchestrator Process** | Runtime — Coded Agent registered as a Process under Shared folder, env-var-injected credentials, `Start now` triggers a Cloud job |
| **UiPath AgentHub LLM Gateway** | Native LLM path — `UiPathCoach` calls `{base}/agenthub_/llm/api/chat/completions` with an OR.* token (`X-UiPath-LlmGateway-NormalizedApi-ModelName` header). No external API key, no Platform Usage demerit. |
| **UiPath AI Trust Layer** | Governance — every coach call rides Trust Layer audit + PII redaction by virtue of going through the platform's LLM Gateway |
| **UiPath External Application + client_credentials** | Service-account auth for Test Manager publish path (TM.* scope) and Coach path (OR.* scope); see "External App scope rule" note below |
| **UiPath Python SDK (`uipath` 2.10.x)** | `uipath init`, `uipath run`, `uipath pack`, `uipath publish` CLI for the Coded Agent dev → deploy cycle |

**External App scope rule (verified live).** UiPath identity rejects
mixed-audience client_credentials exchanges with
`{"error":"invalid_scope"}`. Test Manager publish must filter scope to
`TM.*` only; LLM Gateway coach must filter to `OR.*` only. Each
backend therefore caches its own token. See `core/agentclinic/uipath/
auth.py:50` (C1 commit `9a6c3df`).

---

## 3 · Agent Type

**Coded Agent.** Built with the UiPath Python SDK 2.10.x.
`main.py` defines Pydantic `Input` / `Output` models (per
`.agent/REQUIRED_STRUCTURE.md`), wraps `analyze_pipeline()` from the
core module and conditionally invokes `publish_report()` against
Test Cloud. Deployed as `agentclinic-coded-agent.0.1.1.nupkg` to the
hackathon tenant package feed (`hackathon26_596`), registered as a
Process in the Shared folder, triggered via Orchestrator UI or
`sdk.processes.invoke()`.

No low-code agent component is used. The Track 3 framing decision
documented in `PRD_AgentClinic_v1.md` §6.2 originally targeted a
Studio Web *Orchestrator Agent* as the visible main body; during P2/P3
implementation the Studio Web "Coded Agent inside Function Project"
binding UI was found to still be in Preview and unstable (specifically:
the Call activity → Function Preview binding silently fails to wire
arguments). The project pivoted to **Coded Agent → `uipath pack /
publish` → Orchestrator Process → Cloud runtime** — still a first-
class Studio Web ecosystem deployment unit, but avoiding the Preview
surface. This is documented as a deliberate, evidence-based
production-readiness decision, not a shortcut.

---

## 4 · Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      UiPath Automation Cloud                    │
│                                                                 │
│   ┌──────────────────┐         ┌─────────────────────────┐      │
│   │  Orchestrator    │         │  AgentHub LLM Gateway   │      │
│   │  Process:        │  OR.*   │  /agenthub_/llm/api/    │      │
│   │  agentclinic-    │ ───────▶│  chat/completions       │      │
│   │  coded-agent     │  token  │  (gpt-5.4 / gemini-2.5) │      │
│   │  v0.1.1          │         └─────────────────────────┘      │
│   │                  │                                          │
│   │  env-injected    │         ┌─────────────────────────┐      │
│   │  creds:          │  TM.*   │  Test Cloud (Test Mgr)  │      │
│   │  UIPATH_APP_*    │ ───────▶│  /testmanager_/api/v2/  │      │
│   │  UIPATH_BASE_URL │  token  │  Project / TestCase /   │      │
│   │  UIPATH_SCOPE    │         │  TestSet / Execution /  │      │
│   └────────┬─────────┘         │  Log / Attachment       │      │
│            │                   └─────────────────────────┘      │
│            ▼ invoke main(Input)                                 │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  Coded Agent runtime (Python 3.11+)                      │  │
│   │  main.py: analyze_pipeline → (optional) UiPathCoach      │  │
│   │           → publish_report                               │  │
│   │  core/agentclinic/                                       │  │
│   │    normalize  detect  score  report  validate  coach     │  │
│   │    budget  uipath{auth,client,config,publish}            │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Four roles, no overlap** (PRD §4.2):

- **Judge** = deterministic rule engine (`core/agentclinic/detect.py`,
  `score.py`) — runs without an LLM.
- **Coach** = LLM, bounded — translates findings into remediation,
  forbidden from creating new findings or revising the score.
- **Recorder** = Test Cloud — execution + case log + evidence
  attachment.
- **Orchestrator** = UiPath — Process + AI Trust Layer + Orchestrator
  logs.

---

## 5 · Track 3 Alignment

| Track 3 brief asks for | AgentClinic implementation |
|---|---|
| "Evaluate requirements and turn them into meaningful test scenarios" | Each detected waste pattern is materialized as a reusable Test Case in Test Cloud — re-running the same trace re-uses ACR2:1..7, only writing a new TestSet + Execution row |
| "Identify fragile or outdated tests before they slow down a release" | Seven deterministic detectors with versioned `rule_snapshot` in every finding — drift is detectable across releases via golden regression |
| "Recommend fixes when automation breaks" | Report §4 (Remediation) — per-finding, bounded by `coach/validator.py` to forbid judge-reserved phrasing |
| "Orchestrate the right tests at the right time based on risk, coverage, and change impact" | Coded Agent is invokable from any UiPath process; the Trust Layer + Orchestrator logs provide the audit trail; per-pattern testcases give risk-weighted coverage views in Test Manager |
| "Validate AI-infused workflows, including third-party agents" | Trace schema is the only boundary — any agent that can emit `event_id` / `tool_name` / `state_hash` is testable. `source_signature` records which adapter produced the trace |

---

## 6 · Setup Instructions

### Prerequisites
- Python 3.11+
- A UiPath Automation Cloud tenant (the hackathon staging tenant works)
- An External Application registered in the tenant with **both** TM.*
  and OR.* application scopes granted (you'll cache two tokens, one
  per audience)

### Local development run

```bash
# 1. Clone
git clone https://github.com/<your-handle>/agentclinic.git
cd agentclinic

# 2. Install
pip install -e .            # or: pip install -r requirements
                            # (uipath, jsonschema, rfc3339-validator, requests, pydantic)

# 3. Configure credentials
mkdir -p .uipath
cat > .uipath/app.json <<EOF
{
  "app_id":          "<your External App id>",
  "app_secret":      "<your External App secret>",
  "token_endpoint":  "https://<region>.uipath.com/identity_/connect/token",
  "scope":           "TM.Projects TM.Projects.Read TM.Projects.Write TM.TestCases TM.TestCases.Read TM.TestCases.Write TM.TestSets TM.TestSets.Read TM.TestSets.Write TM.TestExecutions TM.TestExecutions.Read TM.TestExecutions.Write TM.Attachments TM.Attachments.Read TM.Attachments.Write OR.Execution",
  "base_url":        "https://<region>.uipath.com/<org>/<tenant>/testmanager_",
  "org":             "<org>",
  "tenant":          "<tenant>"
}
EOF

# 4. Sanity check — analyze one trace, no publish
PYTHONPATH=core python -m agentclinic analyze \
  examples/golden_traces/01_hard_hat_loop.golden.json \
  --report /tmp/report.md

# 5. Run the full regression suite (5 trace goldens + 5 budget goldens)
PYTHONPATH=core python -m agentclinic golden examples/golden_traces

# 6. Publish a trace to Test Cloud (real write)
PYTHONPATH=core python -m agentclinic publish \
  examples/golden_traces/01_hard_hat_loop.golden.json \
  --project-name "AgentClinic Reports v2" \
  --project-prefix ACR2 \
  --coach uipath
```

### Coded Agent deployment (Automation Cloud)

```bash
# 1. Build schema from Pydantic models
uipath init --no-agents-md-override

# 2. Local validation through the SDK runtime
uipath run main --file <wrapped_input>.json --output-file out.json

# 3. Package
uipath pack          # → .uipath/agentclinic-coded-agent.<version>.nupkg

# 4. Authenticate as the External App (OR.* scope only for publish path)
uipath auth --staging \
  --client-id <APP_ID> --client-secret <APP_SECRET> \
  --base-url "https://<region>.uipath.com/<org>/<tenant>/" \
  --scope "<OR.* scopes only>"

# 5. Publish to tenant package feed
uipath publish -t
```

### Wiring the Process for Cloud runtime

In Orchestrator → Shared folder → **Deploy** the package as a Process,
then in **Process Configuration → Environment Configuration** paste
the dotenv block (the same five fields from `.uipath/app.json`):

```dotenv
UIPATH_APP_ID=...
UIPATH_APP_SECRET="..."
UIPATH_TOKEN_ENDPOINT=https://.../identity_/connect/token
UIPATH_BASE_URL=https://.../testmanager_
UIPATH_SCOPE=TM.Projects TM.Projects.Read ... TM.Attachments.Write
```

Then **Start now** with input `{"trace": <trace dict>,
"publish_to_test_cloud": true, "project_name": "AgentClinic Reports
v2", "project_prefix": "ACR2"}`. Output contains `report` (always),
`test_cloud` (publish receipt with `ui_url`), and `publish_error`
(null on success).

---

## 7 · Claude Code Usage (Coding Agents bonus +2)

**Coding agent used:** Anthropic Claude (via Claude Code).

**How it contributed:** every line of source code, every commit
message, every documentation file in this repository was written by
Claude Code in a long-running session-based pair-programming
collaboration. The human role was driver / reviewer / domain
oracle ("司機先生" + Chloe) — describing the problem space, vetting
LLM platform discoveries, approving architectural pivots, performing
the GUI actions Claude cannot. Claude Code produced the code, the
detector logic, the schemas, the REST integration, the production
error matrix, the CLI, and this README.

**Evidence:**

- **16 commits** across 11 days (`git log`), each one a discrete
  Claude-Code-driven milestone:

  ```
  0185de6  P1: AgentClinic core v0.1.0 — deterministic evidence-bound forensics
  b33de34  docs: P2 plan + Budget Guardian PRD v0.1
  3fd7b00  docs: Budget Guardian adds route_to_secondary_pool action
  7a0cdbd  P2 spike: Test Cloud write verification
  737ab08  Budget Guardian v0.1: deterministic burn-rate forecaster + golden gate
  cb4b9e6  Report Section 7: Budget & Runway Analysis -- close the loop
  3825dc8  P2 v1: uipath module + publish CLI
  33d454c  P2 v2: full Test Cloud chain -- per-pattern testcases with PASS/FAIL
  0d251d1  USD pricing: Section 3 quotes dollars, not just tokens
  8db3bdd  P4: LLM coaching layer -- the COACH role, with hard boundary
  f8decfa  P4 native: UiPathCoach via AgentHub LLM Gateway -- platform LLM
  953697f  UiPathCoach: default model gpt-5.4-2026-03-05
  9a6c3df  C1: evidence-bound testcaselog reason + structured metadata
  d29b1bb  V3-2: Studio Web Coded Agent scaffolding
  8ca19ae  C3: Coded Agent runtime invokes publish
  aefb1f4  C3 hotfix 0.1.1: add requests to runtime deps
  ```

- **`docs/P2_SPIKE_RESULT.md`** is a Claude-Code-authored forensic
  write-up of how the Test Manager API was reverse-engineered from
  SDK source code (PAT auth dead-ended → External App + client_
  credentials worked, found via grep'ing the SDK).

- **`scripts/`** — five investigative probes Claude Code wrote on
  June 22 2026 to verify project access, override-result behaviour,
  and the (logId, currentResult) unique constraint while solving
  the "evaluator can't see the testcase reason in the UI" issue.
  Each script has a docstring header explaining the hypothesis it
  was testing.

- **`PRD_AgentClinic_v1.md` §13 — Three iron rules** ("Zero
  hallucination / No single-signal verdict / Coach not surveillance")
  were proposed by Claude Code during the P1 design conversation and
  ratified by the driver as project DNA. They directly shape the
  detector logic and the bounded-coach validator.

**Substantively integrated, not advisory.** Claude Code didn't
"suggest snippets" — it produced and committed the complete working
solution. The driver pushed back when it overreached (e.g. when
Claude Code tried to redact PII without checking that Trust Layer
already does it natively, the driver caught the duplication; when
Claude Code proposed running 36 verification subagents and burned
5 hours of the driver's Claude API window, the driver added a
"hand-raised" protocol now codified in the project memory). That
back-and-forth — Claude proposing, driver correcting, both updating
the project's memory of what works — is the actual collaboration
pattern, and is evidence of substantive integration rather than
cargo-culted code generation.

---

## 8 · Repository Layout

```
.
├── main.py                       Coded Agent entry (Pydantic Input/Output)
├── pyproject.toml                Coded Agent package metadata + deps
├── entry-points.json             UiPath SDK-generated Pydantic schema
├── uipath.json                   Coded Agent function mapping
├── project.uiproj                UiPath Function project descriptor
├── bindings.json                 Resource bindings (empty in v0.1.x)
├── main.mermaid                  Auto-generated agent graph
├── LICENSE                       MIT
├── PRD_AgentClinic_v1.md         Production PRD (June 12 sign-off)
│
├── core/                         Deterministic Python engine
│   └── agentclinic/
│       ├── cli.py                argparse entry: analyze / publish / golden / budget
│       ├── normalize.py          trace → internal Evidence Contract
│       ├── detect.py             seven waste-pattern detectors
│       ├── score.py              L0–L3 scorecard with severity weights
│       ├── report.py             six-section report builder
│       ├── validate.py           schema validators (trace + finding)
│       ├── coach/                Coach role (LLM-bounded translation)
│       │   ├── base.py           Coach protocol + CoachResult
│       │   ├── mock.py           Deterministic stub (testing)
│       │   ├── vertex.py         GCP Vertex fallback
│       │   ├── uipath_llm.py     Native AgentHub LLM Gateway
│       │   ├── apply.py          Apply coach to report
│       │   └── validator.py      Boundary validator (forbid judge-phrases)
│       ├── budget/               Budget Guardian (PLAN_P2 §2)
│       └── uipath/               Test Cloud REST integration
│           ├── auth.py           External App + client_credentials, TM-scope filter
│           ├── client.py         Test Manager v2 REST wrapper
│           ├── config.py         load_config (file + env override)
│           └── publish.py        Full chain: project → testcase → testset → execution → log → override → attachment
│
├── contracts/                    Schemas
│   ├── trace_schema_v1.json      Input contract
│   ├── finding_schema_v1.json    Finding output contract (evidence required)
│   └── README.md
│
├── examples/golden_traces/       Regression suite
│   ├── 01_hard_hat_loop.golden.json
│   ├── 02_clean_run.golden.json           (negative sample)
│   ├── 03_redundant_and_full_read.golden.json
│   ├── 04_unverified_claim_missing_tokens.golden.json
│   └── 05_interleaved_think_retry.golden.json
│
├── scripts/                      Investigative probes (June 22 ACL debugging)
│   ├── probe_project_access.py
│   ├── d_assign_ck_owner.py
│   ├── probe_override_result.py
│   ├── d1_overwrite_acr2_1_reason.py
│   └── verify_two_executions.py
│
├── docs/
│   ├── PLAN_P2_and_BudgetGuardian.md
│   ├── P2_SPIKE_RESULT.md
│   ├── ERROR_MATRIX.md           Production error handling (PRD §7)
│   ├── front_door_vs_back_office.svg
│   └── p2_spike_evidence.png
│
├── .agent/                       UiPath SDK reference (auto-generated)
├── .claude/commands/             In-IDE slash commands
└── AGENTS.md / CLAUDE.md         UiPath SDK pattern documentation
```

---

## 9 · Three Iron Rules

These come from the project's RaidMeter DNA (the predecessor in the
GCP / Arize ecosystem) and govern every implementation decision when
ambiguity arises:

1. **Zero hallucination** — when data is missing, the report says
   "unknown" with a specific gap entry, never a confident guess.
2. **No single-signal verdict** — pattern detection requires multi-
   factor evidence; one suspicious event is logged, not judged.
3. **Coach not surveillance** — AgentClinic is a consultant. The
   engineer keeps every decision. The coach translates, it doesn't
   command.

See `PRD_AgentClinic_v1.md` §13.

---

## 10 · Production Error Handling

The seven failure modes called out in PRD §7 — broken JSON,
unsupported schema, missing fields, LLM timeout, duplicate writes,
partial publish failure, golden suite crash — each have a
documented implementation site and a verifiable test artifact.

See **[`docs/ERROR_MATRIX.md`](docs/ERROR_MATRIX.md)**.

---

## 11 · Acknowledgments

- **Driver:** 司機先生 — domain framing, GUI actions Claude cannot
  perform, the "hand-raised" protocol that saved the project from
  burning the API window.
- **Product lead:** Chloe Kao — vision, voice, and the iron rules.
- **Platform intelligence:** Percy (Perplexity) — UiPath ecosystem
  reconnaissance, hackathon rule interpretation.
- **Production architecture review:** 曦 (GPT-5.5) — the 4-roles-no-
  overlap discipline, the 17-day milestone plan, the Evidence
  Contract framing.
- **Code & docs:** Claude Code (Anthropic) — every commit, every
  schema, every page of this repository.

---

## License

MIT — see [LICENSE](LICENSE).

The MIT license covers the original AgentClinic solution code only.
UiPath proprietary tools, activities, SDK packages, and platform
components referenced or used within remain subject to their own
license terms.
