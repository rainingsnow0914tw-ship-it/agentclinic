# Devpost Submission — copy / paste guide

Each H2 below is a Devpost form field. The **blockquoted block** under
each is what you paste into that field; the rest is just framing for
your eyes. No mental overhead — open the file, find the field, copy
the quote.

Demo video outline lives at the bottom (it's not a paste-target, it's
a recording script).

---

## Field: `Project name`

> AgentClinic

## Field: `Elevator pitch` (≤ 200 chars)

> Drop an AI agent's trace in. Get a forensic report where every claim points at a trace event. Published natively into UiPath Test Cloud as the system of record. Coach, not surveillance.

(197 chars ✓)

## Field: `Built with` (tags)

> uipath-test-cloud, uipath-coded-agent, uipath-orchestrator, uipath-llm-gateway, uipath-ai-trust-layer, python, pydantic, jsonschema, claude-code, anthropic-claude

## Field: `Try it out links`

> Public repo: https://github.com/rainingsnow0914tw-ship-it/agentclinic
>
> Test Cloud evidence (ACR2 project on hackathon staging): executions `0bffe91c` / `938e66e5` / `608a0b2e` / `8951d57b` / `822668cc` — five published goldens covering score levels L0 through L3, full evidence-bound chain visible in Test Manager UI.

---

## Field: `Inspiration`

> 🔍 Every team I've worked with ships AI agents the same way: hope it works, pray it scales, debug post-incident. Existing eval harnesses score outputs — they don't tell you **which trace event drove the verdict**, or admit when they can't tell.
>
> The turning question wasn't "is this agent good?" but **"can the review point at the evidence?"** If the answer is no, you're judging vibes.
>
> AgentClinic is what happens when you build a clinic instead of a courtroom — every finding tied to a specific event in the trace, every score reproducible from source-controlled rules, every coaching line forbidden from inventing diagnoses.

(118 words ✓)

---

## Field: `What it does`

> 🩺 Drop an AI agent's execution trace in. AgentClinic runs a fixed forensic pipeline:
>
> **Detect** — seven deterministic waste patterns (`hard_hat_loop`, `state_unchanged_retry`, `lucky_guess`, `agent_piling_on`, `full_file_read_before_grep`, `redundant_tool_call`, `completion_claim_without_verification`). Every finding bound to specific `trace_event_id`s as evidence. **No finding may exist without an evidence span** — it's a contract.
>
> **Score** — L0 to L3 scorecard, severity-weighted. Token waste accounted in tokens *and* USD using a versioned pricing snapshot.
>
> **Coach (optional)** — LLM rides UiPath's AgentHub LLM Gateway, so it stays inside the AI Trust Layer for audit + PII redaction. The coach is forbidden from inventing findings or reversing the score — enforced by a boundary validator that blocks judge-reserved phrasing.
>
> **Publish** — native to UiPath Test Cloud. One reusable Test Case per pattern, one Test Set + Execution per publish, per-pattern Test Case Log with override-result reason containing the finding chain, full report.md attached. Re-running the same trace re-uses Test Cases — quality history queryable forever in Test Manager.
>
> Track 3's brief asks for "quality as a continuous, intelligent, governed capability." That's the design.

(190 words ✓)

---

## Field: `How we built it`

> ⚙️ **Four roles, no overlap.**
>
> - **Judge** = deterministic Python rule engine. Runs without an LLM. Can't be tricked into a wrong verdict because rules are source-controlled and golden-tested.
> - **Coach** = LLM, bounded. Translates findings into remediation. Forbidden from judging, enforced by `coach/validator.py`.
> - **Recorder** = UiPath Test Cloud via Test Manager REST v2.
> - **Orchestrator** = UiPath Orchestrator Process + AI Trust Layer.
>
> **Stack:** Python 3.11+, Pydantic for the Coded Agent boundary, jsonschema for the trace/finding contracts, UiPath Python SDK 2.10.x for `pack` / `publish` / `run`. **No direct LLM provider API key** — every coach call routes through UiPath's AgentHub LLM Gateway, so the LLM stays inside the AI Trust Layer for audit and PII redaction.
>
> **Test Cloud integration was reverse-engineered.** PAT didn't work on the hackathon tenant; pivoted to External Application + client_credentials; discovered UiPath identity rejects mixed-audience scopes (`TM.*` + `OR.*` in one exchange returns `invalid_scope`). Each backend caches its own audience-scoped token. Full forensic write-up of auth + scope landmines in `docs/P2_SPIKE_RESULT.md`.
>
> **End-to-end with Claude Code.** Every line of source, every commit, every doc in this repo was written by Claude Code in an 11-day pair-programming session. Human role was driver — framing, vetting, correcting, performing GUI actions Claude can't.

(193 words ✓)

---

## Field: `Challenges we ran into`

> 💣 **Studio Web's Coded-Agent-in-Function-Project binding is still Preview, and unstable.** Call activity → Function arguments silently drop. After two days fighting it, we pivoted to **Coded Agent → `uipath pack/publish` → Orchestrator Process → Cloud runtime**. Still first-class Studio Web ecosystem, but going around the broken Preview surface.
>
> 🔒 **Test Cloud's permission model has three independent layers, none of which error helpfully.** Project member role wasn't enough — also need Tenant Administrator role to open the Test Manager *application*, **plus** a license seat. We discovered all three by hitting the same "You do not have the necessary rights" from three different starting states. README now walks future users through all three.
>
> 🌀 **Override-result API has an undocumented `(logId, currentResult)` unique constraint.** Re-posting an override returns HTTP 409 `duplicateUniqueConstraint`. Found it by re-running a publish during testing; recovery path documented in `docs/ERROR_MATRIX.md`.
>
> 📦 **Cloud runtime is a fresh Python install — only `pyproject.toml` deps present.** Our first Cloud job crashed on `ModuleNotFoundError: requests` because local pip state had it but pyproject didn't list it. Hotfix v0.1.1 added `requests` + the rule: local-dev parity is paper parity, only Cloud runtime is real.

(173 words ✓)

---

## Field: `Accomplishments that we're proud of`

> 🎯 **Three Track 3 risks fully closed.** Track 3 calls out three failure modes — thin-shell (UiPath as webhook), Test Cloud not actually integrated, external LLM as BYOM shell. AgentClinic closes all three: native Coded Agent + Process deployment + Cloud runtime; full Test Cloud chain visible in `ACR2:79-84` covering score levels L0 through L3; LLM rides AgentHub LLM Gateway under Trust Layer governance — no direct provider API key, full audit trail.
>
> 🔍 **Every claim bound to evidence.** Not a single finding exists without an `evidence_spans` list pointing at concrete `trace_event_id`s. The override-result reason in each Test Case Log is multi-line and explicit. A reviewer opening Test Cloud doesn't see "agent looks bad" — they see exactly which trace events drove the verdict.
>
> 📜 **Production error handling, written down.** Seven failure modes mapped to concrete line numbers in `docs/ERROR_MATRIX.md`. Exit codes are a strict contract: 0 ok, 1 analysis failure, 2 input failure. CI gates can act on it.
>
> 🤖 **Coded with Claude Code, end-to-end, substantively integrated.** 20+ commits authored by Claude Code, README includes a commit-by-commit ledger + candid section describing where Claude proposed and where the driver corrected.

(173 words ✓)

---

## Field: `What we learned`

> 💡 **Bounded coaches beat free-form judges by an embarrassing margin.** Early on we let the LLM judge runs end-to-end. It produced confident-sounding judgments unrelated to the evidence. The split — judge deterministic, coach LLM-bounded — was the highest-leverage decision in the whole project. It's also exactly the governance shape Track 3 is asking for.
>
> 🗺️ **The official docs underplay the platform.** Real LLM Gateway is at `/agenthub_/llm/api/`, not `/llmgateway_/`. TM/OR mixed-scope is rejected silently in the docs. Each was a half-day investigation; once written into `docs/`, it's a thirty-second decision for the next team.
>
> 🤝 **Pair-programming with a coding agent teaches you what the human role actually is.** Not "prompt and wait" — it's framing, vetting, correcting, and remembering. Our project memory grew out of the corrections; if anything else here is reusable, that process discipline is what we'd point to first.

(130 words ✓)

---

## Field: `What's next for AgentClinic`

> 🛣️ **More adapters.** Trace schema is the only boundary; today we ship one adapter (`adapter_claude_code_v1`). LangGraph, AutoGen, CrewAI, OpenAI Agents SDK each need a thin adapter — the detector core doesn't change.
>
> 🔑 **Secrets graduate to Orchestrator Assets.** Env vars work for the demo; production path is `sdk.assets.retrieve_credential()` against a Credential-typed Asset. One line in `main.py`.
>
> 📊 **Budget Guardian section in the published report.** The deterministic burn-rate engine is built (`core/agentclinic/budget/`); we ran out of clock to wire it into the Test Cloud record. v0.2.
>
> 🔁 **Self-discovered patterns.** Seven detectors is the floor. Next layer: automatically *find* new patterns from a corpus of failed runs and propose them as detector candidates — meta-learning for the testing layer itself.
>
> 🌐 **Never against the engineer.** Team-level views show workflow patterns, never individual leaderboards. AgentClinic is a quality gate for agents — not a sentinel against the people who build them. Coach, not surveillance.

(140 words ✓)

---

## Optional: Before / After framing (paste into `What it does` or `Inspiration` if there's room)

> **Without AgentClinic** — agent fails, engineer reads logs by feel, writes a Slack post-mortem, ships the fix, hopes the next regression catches it.
>
> **With AgentClinic** — agent fails, trace lands in Test Cloud as an Execution + Failed Log, override-result reason names the exact `evt_0002, evt_0003, evt_0004` events that drove the verdict, full `report.md` attached. Re-runnable. Auditable. CI-gateable.

---
---

# Demo Video — 5-minute outline (NOT a Devpost paste-target)

Recording script for the < 5 min YouTube/Vimeo upload required by
hackathon rules. Pre-record everything, don't live-debug on camera,
no copyrighted music.

**Hard cap: 4:45 on the timeline** — leave 15s buffer before the
Devpost 5:00 limit.

## 0:00 — 0:30 · Hook (30s)

Open on Test Manager UI, ACR2 project, executions list. Pan over the
row showing `exec:trace_gold_001/run_deploy_4x` — Failed, red Results
bar. Click the failed Test Case Log, show the multi-line evidence-
bound reason for 4 seconds (let viewers read it).

> "AI agents are shipping to production faster than any prior software
> category. The testing discipline that traditional software earned
> over decades hasn't caught up. AgentClinic is a pre-production
> clinic — every finding bound to evidence in the trace, every result
> published natively into UiPath Test Cloud as the system of record.
> Coach, not surveillance. Five minutes; here's how it works."

## 0:30 — 1:15 · The problem (45s)

Slide or short clip of an agent retrying `gcloud run deploy` four
times, never reading the error, 7,400 wasted tokens. Cut to a typical
ChatGPT "review this trace" producing confident-but-unsourced
opinions.

> "An agent retried the same broken deploy four times. ChatGPT can
> talk about this trace — it can't tell you *which event* drove the
> verdict, or verify its own claim. We need an audit trail, in the
> release-gate system the team already uses."

## 1:15 — 2:30 · Forensic pipeline (75s)

Live or pre-recorded: `main.py`, `python -m agentclinic publish ...
--coach uipath`. Pan through the seven detectors quickly. Open
`report.md`: §2 finding, show the `evidence_spans` list with three
`trace_event_id`s, §5 information gaps where the report admits what
it can't judge.

> "Seven deterministic detectors, source-controlled. Every finding
> must point at specific trace events as evidence — a finding without
> a span is a contract violation. Section five is the iron rule: when
> data is missing, we say so. Zero hallucination."

## 2:30 — 3:30 · UiPath Test Cloud integration (60s)

Live: Orchestrator → Processes → `agentclinic-coded-agent 0.1.1` →
Start now with golden input → job completes ~30s (cut to fit). Open
Test Manager → ACR2 → newest Execution row → Failed log → Override
Result dialog. **Hold here 5 seconds** — let the multi-line evidence-
bound reason text breathe on screen. Pan to attached `report.md`.

> "Same agent, this time triggered from Automation Cloud, runs the
> exact same pipeline as the Coded Agent runtime, writes the result
> straight into Test Manager. Reusable Test Case per pattern; per-
> pattern log with the evidence-bound reason visible right in the
> dialog the reviewer already uses; full markdown report attached.
> Quality isn't a late-stage checkpoint anymore."

## 3:30 — 4:15 · Four roles (45s)

Slide:

```
👨‍⚖️ JUDGE        deterministic rule engine — runs without an LLM
🏃 COACH        LLM, bounded — translate findings, forbidden to judge
📋 RECORDER     UiPath Test Cloud — execution + log + attachment
🎼 ORCHESTRATOR  UiPath — Process + AI Trust Layer audit
```

> "Four roles, no overlap. Judge is deterministic — the LLM can't
> revise the verdict. Coach rides UiPath's AgentHub LLM Gateway, so
> every LLM call stays inside the AI Trust Layer for audit and PII
> redaction. Test Cloud is the system of record. UiPath is the
> orchestration and governance layer. That's the Track 3 framing —
> quality as a continuous, governed capability."

## 4:15 — 4:45 · Close (30s)

Open GitHub repo page; pan over CI badge (green), README,
`docs/ERROR_MATRIX.md`, `git log --oneline` showing every commit
authored by Claude Code.

> "The whole codebase was written by Claude Code over eleven days,
> every commit visible in the git log. Repository public, MIT
> licensed, CI green, error matrix documented. Drop a trace in, get
> an audit trail. Thank you."

End frame: GitHub URL + `Track 3 · AgentHack 2026`, hold 2 seconds.

## Recording checklist

- [ ] 1080p screen capture minimum
- [ ] Separate audio track if possible (cleaner mix)
- [ ] No copyrighted music — silence or CC0 loop
- [ ] **Trim total to under 5:00** — Devpost hard cap, judges aren't
      obligated to watch past it
- [ ] Upload to YouTube as Public or Unlisted ("publicly visible"
      per rules)
- [ ] Test the link in a private browser before pasting into Devpost
