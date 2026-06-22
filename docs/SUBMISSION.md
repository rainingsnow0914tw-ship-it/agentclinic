# AgentClinic — Devpost Submission Pack

Everything you'd paste into the Devpost submission form, plus a five-
minute demo video outline. Each section below maps to a field on the
Devpost project page; copy-paste verbatim or trim per the field's
character budget.

---

## Project name

```
AgentClinic
```

## Tagline / Elevator pitch  (≤ 200 chars)

```
A pre-production clinic for AI agents — drop a trace in, get a forensic report where every claim is bound to a trace event, published natively into UiPath Test Cloud.
```

(195 chars, fits)

## Built with  (tags / technology stack)

```
uipath-test-cloud
uipath-coded-agent
uipath-orchestrator
uipath-llm-gateway
uipath-ai-trust-layer
python
pydantic
jsonschema
claude-code
anthropic-claude
```

---

## Inspiration

AI agents are entering production faster than any prior software
category, but the testing discipline that traditional software earned
over decades hasn't followed them in. "It worked on my machine" gets
multiplied by "and the LLM happened to behave that day." Engineers
review agent runs by feel; the same blind retry burns the same tokens
release after release; nobody can say *why* a run was wasteful or
where the evidence for that judgment lives in the trace.

We've sat through enough post-incident reviews to know the gap. What
we wanted: a piece of infrastructure where every score points at the
trace event it came from, every remediation is tied to a real waste
pattern, and the whole result lands in the existing release-gate
system that the team already uses — UiPath Test Cloud — rather than
yet another dashboard nobody opens.

That became AgentClinic: a pre-production clinic for AI agents, with
the discipline of a forensic lab.

---

## What it does

Given an AI agent's execution trace, AgentClinic runs a fixed forensic
pipeline:

1. **Normalize** the trace against a versioned schema
   (`trace_schema_v1`). Any agent framework — UiPath-native, third-
   party, or in-house — can plug in by writing an adapter to this
   schema; the core engine never branches on agent type.

2. **Detect** seven well-defined waste patterns (`hard_hat_loop`,
   `state_unchanged_retry`, `lucky_guess`, `agent_piling_on`,
   `full_file_read_before_grep`, `redundant_tool_call`,
   `completion_claim_without_verification`). **Every finding is
   bound to specific `trace_event_id`s as evidence** — a finding
   without an evidence span is a contract violation and is rejected.

3. **Score** the run deterministically on an L0–L3 scorecard
   (severity-weighted), with token-waste accounting in tokens *and*
   USD (using a trace-aggregate in/out ratio and a versioned pricing
   snapshot).

4. **Coach (optional)** — an LLM rides UiPath's AgentHub LLM Gateway
   (so it stays inside the platform's AI Trust Layer for audit + PII
   redaction) and translates findings into actionable remediation,
   strictly forbidden from inventing new findings or revising the
   score.

5. **Publish** the report natively into UiPath Test Cloud: one
   reusable Test Case per pattern, one Test Set + Execution per
   publish, per-pattern Test Case Log with override-result reason
   containing the finding chain (finding_id | severity | confidence |
   trace_event_ids), and the full markdown report attached to the
   execution. Re-running the same trace re-uses Test Cases, only
   writing a new Test Set + Execution row — quality history is
   queryable in Test Cloud forever.

The agent runs on **UiPath Automation Cloud** as a Coded Agent
(`uipath pack` / `uipath publish` / `Orchestrator Process`), so any
existing UiPath workflow can call it as a quality gate — the same way
existing UiPath tests integrate into release pipelines.

---

## How we built it

**Architecture: four roles, no overlap.**

- **Judge** = deterministic rule engine (Python). Runs without an
  LLM. Cannot be tricked into a wrong verdict because the rules are
  source-controlled and golden-tested.
- **Coach** = LLM, bounded. Translates findings into remediation.
  Forbidden from creating new findings or revising the score, enforced
  by a boundary validator (`coach/validator.py`) that blocks judge-
  reserved phrasing.
- **Recorder** = UiPath Test Cloud — execution + case log + evidence
  attachment via Test Manager REST v2.
- **Orchestrator + governance** = UiPath Orchestrator Process + AI
  Trust Layer.

**Stack.** Python 3.11+, Pydantic for the Coded Agent boundary,
jsonschema + rfc3339-validator for the trace/finding contracts,
the UiPath Python SDK 2.10.x for `pack` / `publish` / `run`. No
external LLM API key — the coach calls
`{base}/agenthub_/llm/api/chat/completions` with an OR.* token,
keeping everything inside UiPath's governance plane.

**Test Cloud integration was reverse-engineered.** The Personal Access
Token path didn't work on the hackathon staging tenant (five separate
401 evidence points). We pivoted to External Application +
client_credentials, then discovered UiPath identity rejects mixed-
audience scopes (`TM.*` + `OR.*` in one exchange returns
`invalid_scope`). The fix: each backend caches its own token, scoped
to a single audience. That investigation is documented as a forensic
write-up in `docs/P2_SPIKE_RESULT.md` and codified in `auth.py`'s
TM-scope filter.

**A development-pipeline-driven-by-Claude-Code.** Every line of
source, every commit message, every documentation file in this
repository was produced by Claude Code in a long-running pair-
programming session — sixteen commits across eleven days, ranging
from the P1 deterministic core to the C3 Coded Agent runtime that
ties everything together. The human role was driver / reviewer /
domain oracle: framing the problem, vetting platform discoveries
("UiPath actually puts LLM Gateway under `/agenthub_/llm/api` not
`/llmgateway_/`, here's the source-code grep that found it"),
approving architecture pivots, performing the GUI actions Claude
cannot, and stepping in when Claude overreached (the day Claude
proposed running 36 verification subagents and burned 5 hours of
the driver's Claude API window directly produced the project's
"hand-raised" protocol now codified in the memory).

---

## Challenges we ran into

**Studio Web's Coded-Agent-inside-Function-Project binding UI is
still in Preview, and it's unstable.** The Call activity → Function
binding silently fails to wire arguments. We had bet the project's
"Studio Web Orchestrator Agent as visible main body" framing on this
working. After two days fighting it, we pivoted to **Coded Agent →
`uipath pack/publish` → Orchestrator Process → Cloud runtime** —
still first-class Studio Web ecosystem deployment, but going around
the Preview surface entirely. The pivot is documented and defended in
`README.md §3` as a production-readiness decision.

**Test Cloud's permission model has three independent layers, and
none of them error in a way that tells you which layer is denying.**
Project-level role assignment (which we automated via API) wasn't
enough; the user also needed Tenant Administrator role to access the
Test Manager *application* at all; and on top of that, Test Manager
needed a **license seat** (separate from access). We discovered all
three by hitting the same "You do not have the necessary rights to
access this application" error from three different starting states.
The result: the README's "Setup Instructions" now walks future users
through all three layers in one go.

**Override-result API has a (logId, currentResult) unique constraint
that's not in the docs.** Re-posting an override returns HTTP 409
`duplicateUniqueConstraint`. We discovered it by re-running a publish
during testing; the recovery path is documented in
`docs/ERROR_MATRIX.md` row 5.

**The Cloud runtime's Python environment is a fresh install — only
deps in `pyproject.toml` are present.** Our first cloud job crashed
on `ModuleNotFoundError: No module named 'requests'` because we'd
relied on local pip state. Hotfix v0.1.1 added `requests` to
`pyproject.toml` and confirmed the rule: local-dev parity is paper
parity, only the Cloud runtime is real.

---

## Accomplishments we're proud of

**Three Track 3 risks fully closed.** The hackathon Track 3 brief
calls out three failure modes — thin-shell ("UiPath as webhook"),
Test Cloud not actually integrated, and external LLM acting like a
BYOM shell. AgentClinic closes all three: native Coded Agent + Process
deployment + Cloud runtime (not a webhook); full Test Cloud chain
(project / test case / test set / execution / case log /
override-result / attachment), with five golden traces covering
score levels L0 through L3 all visible in `ACR2:79-84`; LLM rides
the AgentHub Gateway under AI Trust Layer governance, no external
API key.

**Every claim in the report is bound to evidence.** Not a single
finding exists without an `evidence_spans` list pointing at concrete
`trace_event_id`s in the source trace. The override-result reason
written into each Test Case Log is multi-line and explicit:

```
AgentClinic detected pattern `hard_hat_loop` -- 1 finding(s):
  RM-F-trace_gold_001-001 | severity=critical confidence=0.9 | events: evt_0002, evt_0003, evt_0004
Evidence-bound by finding_schema_v1; see attached report.
```

A reviewer opening Test Cloud doesn't see "agent looks bad" — they
see exactly which trace events drove the verdict and can jump back
to those events in the source trace.

**Production-grade error handling, written down.** The seven failure
modes called out in the PRD (broken JSON / unsupported schema /
missing fields / LLM timeout / duplicate writes / partial publish
failure / golden suite crash) each have a documented implementation
site with line numbers in `docs/ERROR_MATRIX.md`. Exit codes are a
strict contract: 0 = ok, 1 = analysis-level failure, 2 = input-level
failure.

**Coded with a coding agent, end-to-end, with substantive
integration.** Sixteen commits authored by Claude Code, documented
in the README with a 16-line commit-by-commit ledger and a candid
section describing where Claude proposed, where the driver corrected,
and how the project's internal memory grew out of that back-and-
forth. This is meant as evidence for the AgentHack Coding Agents
bonus.

---

## What we learned

**UiPath has a deep platform story under the hood that the official
docs underplay.** The real LLM Gateway endpoint lives at
`/agenthub_/llm/api/chat/completions`, not `/llmgateway_/`, and you
only find it by grep'ing the SDK source. The TM/OR mixed-scope
rejection isn't in the API reference. Every one of these was a
half-day investigation that, once written down, becomes a thirty-
second decision for the next person. We turned each into a docs/
artifact (`P2_SPIKE_RESULT.md`, `ERROR_MATRIX.md`) precisely so the
next team doesn't repeat the dig.

**Bounded coaches are dramatically more useful than free-form
LLM judges.** Early in the project we tried letting the LLM judge
runs end-to-end. It happily produced confident-sounding judgments
unrelated to the evidence. The "Judge = deterministic, Coach = LLM
bounded" split (PRD §4.2) — refusing to let the LLM revise the
verdict, only translate the findings — was the highest-leverage
design decision in the entire project. It's also exactly the
shape of governance the Track 3 brief is asking for.

**Pairing with a coding agent for eleven days teaches you what
the human role actually is.** Not "give it a prompt and wait" —
it's framing, vetting, correcting, and remembering. The driver's
job is to push back when the agent overreaches and to make sure
the right lessons land in the project memory so they survive
context windows. We codified that pattern in our project memory
files; if anything else here is reusable for future teams, that
process discipline is what we'd point to first.

---

## What's next for AgentClinic

**Adapters for more agent frameworks.** The trace schema is the
only boundary; today we ship one adapter (`adapter_claude_code_v1`).
LangGraph, AutoGen, CrewAI, and OpenAI Agents SDK each need a thin
adapter that produces conformant `trace_schema_v1.json` documents.
The detector core never changes — that was the point of the schema.

**Secrets graduate to Orchestrator Assets.** The Cloud runtime
currently reads credentials via environment variables on the
Process. The cleaner production path is `sdk.assets.retrieve_
credential()` against an Orchestrator Asset of type Credential —
one line in `main.py`, but it earns the right to ship to a real
tenant.

**Budget Guardian integration in the report.** `docs/PLAN_P2_and_
BudgetGuardian.md` §3 describes a Report Section 7 that ties
deterministic burn-rate forecasts to the same findings — "this run
burned 7470 tokens in `hard_hat_loop`, you have 22% of the window
left, projection puts you over budget in 14 minutes." The engine
is built (`core/agentclinic/budget/`); we ran out of clock to wire
it into the published Test Cloud record. v0.2.

**CI regression on every PR.** A GitHub Actions workflow that
runs `python -m agentclinic golden` against the five trace +
five budget goldens, gating the merge. The local gate already
runs green; promoting it to CI is a fifteen-minute change once
the repo is permanent.

**Adversarial waste-pattern coverage.** Seven patterns is the
floor, not the ceiling. The next layer is automatically *finding*
new patterns from a corpus of failed agent runs and proposing
them as new detectors with golden traces — meta-learning for the
testing layer itself.

---

## Try it out

- **Live code:** https://github.com/rainingsnow0914tw-ship-it/agentclinic
- **Test Cloud evidence:** `ACR2` project on UiPath staging
  (hackathon26_596), executions `0bffe91c` / `938e66e5` /
  `608a0b2e` / `8951d57b` / `822668cc` covering score levels
  L0–L3 with full evidence-bound reasons.
- **Setup:** `README.md §6` walks through local dev, Coded Agent
  packaging, and Cloud runtime configuration.

---
---

# Demo Video — five-minute outline

Total budget: **4:45 max** (give yourself 15s buffer; Devpost is
strict about the five-minute cap).

Tone: confident, plain English, no music with copyright. Screen
recording with clear voiceover. Pre-record everything; don't try to
live-debug on camera.

## 0:00 — 0:30 · The hook (30s)

Open on the Test Manager UI, ACR2 project, executions list with
five completed runs. Pan over the row showing the failed
`hard_hat_loop` test case log.

Voiceover:
> "AI agents are shipping to production faster than any prior
> software category, but the testing discipline traditional software
> built over decades hasn't caught up. AgentClinic is a pre-
> production clinic for AI agents — every finding bound to evidence
> in the trace, published natively into UiPath Test Cloud as the
> system of record. Five minutes; here's how it works."

## 0:30 — 1:15 · The problem (45s)

Slide or short live demo of an agent trace going wrong:
- Agent retries `gcloud run deploy` four times, no reads between,
  state hash never changes, ~7,400 wasted tokens.
- Cut to a typical "ChatGPT review" reading the same trace and
  producing confident-but-unsourced opinions.

Voiceover:
> "This is the trace of an agent burning seven thousand tokens
> retrying the same broken command. A general-purpose LLM can talk
> about it but can't tell you *which event* drove the verdict, or
> verify its own claim. We need an audit trail — and we need it in
> the release-gate system the team already uses."

## 1:15 — 2:30 · The forensic pipeline (75s)

Live demo (or pre-recorded `uipath run`):
- Show `main.py` Input — `trace` + `publish_to_test_cloud=true`
- Run it locally first: `python -m agentclinic publish ...
  --coach uipath`
- Pan through the seven detectors briefly (`detect.py` filename
  bar)
- Open the resulting `report.md`: §2 finding RM-F-trace_gold_001-001,
  show the `evidence_spans` list with the three trace_event_ids it's
  bound to. §5 information gaps — what the report explicitly admits
  it cannot judge.

Voiceover:
> "Seven detectors, deterministic, source-controlled. Every finding
> has to point at specific trace events as evidence — a finding
> without evidence is a contract violation and is rejected. Section
> five is the unmovable rule: when data is missing, we say so. Zero
> hallucination."

## 2:30 — 3:30 · UiPath Test Cloud integration (60s)

Live demo:
- Show Orchestrator → Processes → `agentclinic-coded-agent` 0.1.1
- Trigger `Start now` with the same trace input
- Watch the job complete (~30 seconds — cut if needed)
- Open Test Manager → ACR2 → Executions → newest row
- Click the failed Test Case Log → Override Result dialog
- **Slow down here**: show the multi-line evidence-bound reason
  text on screen for 4-5 seconds, let viewers read it
- Pan to the attached `report.md` — full audit trail in Test Cloud

Voiceover:
> "Same agent, this time triggered from Automation Cloud, runs the
> exact same pipeline as the Coded Agent runtime, writes the result
> straight into Test Manager. Reusable Test Case per pattern; one
> Test Set, one Execution per publish; a per-pattern log with the
> evidence-bound reason visible right in the dialog the reviewer
> already uses; the full markdown report attached. Quality is no
> longer a late-stage checkpoint."

## 3:30 — 4:15 · The four roles (45s)

Quick slide showing the architecture:

```
JUDGE     deterministic rule engine — runs without an LLM
COACH     LLM, bounded — translate findings, forbidden to judge
RECORDER  UiPath Test Cloud — execution + log + attachment
ORCHESTRATOR  UiPath — Process + AI Trust Layer + Orchestrator
```

Voiceover:
> "Four roles, no overlap. The judge is deterministic — the LLM
> can't revise the verdict. The coach rides UiPath's AgentHub LLM
> Gateway, so the LLM call stays inside the AI Trust Layer for
> audit and PII redaction. Test Cloud is the system of record.
> UiPath is the orchestration and governance layer that ties
> everything together. That's the Track 3 framing — quality as a
> continuous, governed capability across the enterprise."

## 4:15 — 4:45 · Close (30s)

Open the GitHub repo page; pan over: README → LICENSE → docs/
ERROR_MATRIX → 16 commits in `git log` (each one Claude-Code-
authored).

Voiceover:
> "The whole codebase was written by Claude Code over eleven days
> in pair-programming with a human driver, sixteen commits, every
> commit on this screen. Repository is public, MIT licensed, full
> setup instructions, production error matrix documented. Drop a
> trace in, get an audit trail. Thank you."

End frame: GitHub URL + Track 3 hashtag, hold for 2 seconds.

---

## Recording checklist

- [ ] Screen at 1080p minimum
- [ ] Voiceover separate audio track if possible (cleaner mix)
- [ ] No copyrighted music — silence or a CC0 ambient loop
- [ ] Trim total to **under 5:00** (Devpost rule, hard cap)
- [ ] Upload to YouTube as Public or Unlisted (rules require
      "publicly visible")
- [ ] Test the link in a private browser window before submitting
