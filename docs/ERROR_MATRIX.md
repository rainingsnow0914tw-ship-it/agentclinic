# Error Matrix — Production-Grade Error Handling

Maps the seven production-grade failure modes to their concrete
implementation sites. Each row is the actual code path, not a planning
claim.

The governing principle is **graceful degradation, never silent
hallucination**: when a load-bearing input is missing or malformed,
AgentClinic either drops confidence + flags the gap, or fails fast with
a distinct exit code — but never invents data to fill the hole.

---

## Matrix

| # | Failure mode | Where it's caught | What happens |
|---|---|---|---|
| 1 | **Broken JSON input** (malformed trace file, BOM, truncated upload) | `cli.py:73,170,202` — `except (json.JSONDecodeError, FileNotFoundError, OSError)` | Print `INPUT ERROR: <msg>` to stderr, exit code **2**. No partial analysis. CI / wrapper scripts distinguish from analysis-level failures (exit 1) and clean runs (exit 0). |
| 2 | **Unsupported / unknown schema** (trace doesn't match `contracts/trace_schema_v1.json`) | `validate.py:55` raises `TraceSchemaError` → `cli.py:69,166` catches | Print `SCHEMA ERROR (input rejected, nothing analyzed): <validator detail>`, exit **2**. The schema's `format: date-time` is enforced live (rfc3339-validator), not just declared. |
| 3 | **Missing token / state fields** (events without `token_in`/`token_out`/`state_hash`) | `detect.py:34` `_tokens_total` returns `None` if either field absent; `_sum_tokens` returns `None` rather than 0; `normalize.py` emits a `gap` entry | Report §3 `events_missing_token_fields` count + `waste_unknown_findings` list. §5 (Information Gaps) explicitly names what was missing and what to provide next time. **Score never guesses across the hole.** |
| 4 | **LLM timeout / 429 / coach backend down** | `cli.py:42` only calls `coach_report` if `make_coach(name)` returns non-None; coach failure is isolated — the deterministic analyze pipeline already produced the full report before the coach is invoked | Report still returns with sections 1-7 complete. Coach is strictly additive ("translate findings into readable remediation"); its absence does not change findings, scores, or evidence. This is the §13 rule "Coach not surveillance" in code form. |
| 5 | **Duplicate writes to Test Cloud** (re-running the same trace_id) | `client.py:65` `ensure_project` checks `find_project_by_name` first; `client.py:112` `ensure_testcase` same pattern per (project, name); `override-result POST` returns HTTP 409 `duplicateUniqueConstraint` on (logId, currentResult) re-write | Re-running the same trace reuses the existing project + per-pattern testcase row; only a new TestSet + Execution + Log are written. The 409 on override-result is a known UiPath constraint, documented in `scripts/probe_override_result.py` evidence; recovery path is PUT against the existing override id (follow-up, not blocking). |
| 6 | **Partial failure mid-publish** (network glitch overriding result on log N of M) | `publish.py:126` — `except Exception` per testcaselog override; failure is recorded as `_result_override_error` on that log but does not abort the publish; `main.py:76` wraps the entire publish step in `try/except` and surfaces as `publish_error: <type>: <msg>` while still returning the analyze report | Output object has `report` populated (always) + `test_cloud: null` + `publish_error: <string>` when the push step fails. The Coded Agent (Cloud runtime) caller sees a structured signal it can act on. **Analyze never dies because publish died.** |
| 7 | **One golden in the suite crashes** (corrupt golden file, transient analyzer bug) | `cli.py:270` — `except Exception` inside `cmd_golden` per-file loop, records as FAIL + continues with remaining files | Suite returns exit code 1 if any FAIL, 0 if all PASS. The crash is reported with file name + traceback summary; the rest of the suite still runs (don't let one broken golden block CI). |

---

## Exit-code contract

| Code | Meaning |
|---|---|
| 0 | All ok (golden suite green / analyze published / report written) |
| 1 | Analysis-level failure (publish error, golden suite had ≥1 FAIL) |
| 2 | Input-level failure (broken JSON, schema rejected, file missing) |

CI gates and shell pipelines can distinguish "your trace is wrong" (2)
from "the analyzer hit something it can't handle" (1) without parsing
stderr.

---

## What's deliberately **not** caught

- **Logic bugs in detectors.** A wrong rule that produces a wrong
  finding should surface in the golden regression suite, not be hidden
  by a try/except. Detectors fail loud.

- **Schema migrations.** Bumping `report-v1` → `report-v2` is a code
  change, not an exception path; the validator enforces version
  strictly so silent drift is impossible.

- **External LLM key leakage.** Credentials read by `auth.py` come from
  `.uipath/app.json` (gitignored) or `UIPATH_*` env vars (Coded Agent
  runtime in Automation Cloud). If env is missing, `load_config()`
  raises `ConfigError` listing exactly which fields are absent —
  consumed by main.py's wrapper as `publish_error`, never silently
  swallowed.

---

## Test evidence

- `examples/golden_traces/01_hard_hat_loop.golden.json` — hard_hat_loop
  fires; row 6 (duplicate) verified by re-running the same trace into
  ACR2 multiple times (testset ACR2:78, ACR2:79, ACR2:84 reuse same
  testcase ACR2:1).
- `examples/golden_traces/02_clean_run.golden.json` — negative sample,
  L0 score 100, no findings, no false positives.
- `examples/golden_traces/03_redundant_and_full_read.golden.json` — two
  patterns fire on one trace (testcaselog 2 Failed, exec ACR2:81).
- `examples/golden_traces/04_unverified_claim_missing_tokens.golden.json`
  — exercises row 3 (events missing token fields) + row 4 (claim
  without verification pattern).
- `examples/golden_traces/05_interleaved_think_retry.golden.json` —
  exercises the chain-breaking event detector configuration.

All five live in Test Cloud project ACR2 as concrete artifacts (project
id `a9034ddc-bbc5-0000-5d9e-0b49c3618104`); not paper claims.

