"""Publish an AgentClinic report to UiPath Test Cloud via the full chain.

v2 walks the entire Test Cloud hierarchy:

  Project (idempotent on name)
    -> TestCases  (idempotent on name, one per detected pattern)
    -> TestSet    (one per publish run, named after trace_id+run_id)
    -> assign TestCases to TestSet
    -> TestExecution (source=ThirdParty, sourceDetails=AgentClinic)
    -> TestCaseLog per testcase in the set
    -> override-result per log (Failed if pattern fired in this trace,
       Passed otherwise)
    -> attachment: full markdown report on the TestExecution

Framing for Track 3 meta-testing: each AgentClinic pattern is a quality
test; a trace is a run of that test suite; findings are FAIL signals
with evidence; the report.md attachment is the run's audit trail."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from ..report import to_markdown
from .client import TestManagerClient
from .config import load_config


def publish_report(report: dict, *,
                   project_name: str = "AgentClinic Reports",
                   project_prefix: str = "ACR",
                   config: dict | None = None,
                   markdown_override: str | None = None) -> dict:
    """Push one report through the full Test Cloud chain.

    Returns a flat tracking dict: ids for project/testset/execution/logs
    and the attachment, plus a UI URL pointing at the execution."""
    cfg = config or load_config()
    client = TestManagerClient(cfg)

    findings = report["sections"]["2"]["findings"]
    score = report["score"]
    schema_version = report.get("schema_version", "report-v2")
    trace_id = report["trace_id"]
    run_id = report["run_id"]

    # 1) Project — idempotent on name
    project, project_created = client.ensure_project(
        project_name, project_prefix,
        description=("Auto-managed by AgentClinic core; reports pushed by "
                     "publish_report(). Do not hand-edit."),
    )
    project_id = project["id"]

    # 2) TestCases — one per detected pattern (idempotent on name within
    #    project). Empty findings still need at least one log so the
    #    execution has shape; we synthesize a clean_run placeholder pattern.
    pattern_set = sorted({f["pattern"] for f in findings}) or ["clean_run"]
    pattern_to_testcase: dict[str, dict] = {}
    for pattern in pattern_set:
        tc, _created = client.ensure_testcase(
            project_id, name=f"pattern:{pattern}",
            description=(f"AgentClinic detector for `{pattern}`. "
                         "Owned by core/agentclinic/detect.py; do not "
                         "hand-edit -- regenerate via publish_report()."),
            version=schema_version,
            foreign_reference=f"pattern::{pattern}",
        )
        pattern_to_testcase[pattern] = tc

    # 3) TestSet — one per publish (named after trace+run, deterministic)
    testset_name = f"run:{trace_id}/{run_id}"
    finding_ids = sorted(f["finding_id"] for f in findings)
    finding_ids_str = ", ".join(finding_ids) if finding_ids else "(none)"
    testset = client.create_testset(
        project_id, name=testset_name,
        description=(
            f"AgentClinic run | schema={schema_version} | "
            f"score={score['value']}/100 | "
            f"findings={len(findings)} [{finding_ids_str}] | "
            f"trace_id={trace_id} run_id={run_id}"
        ),
        source="ThirdParty",
        source_details=f"AgentClinic core / trace {trace_id}",
    )
    testset_id = testset["id"]

    # 4) Assign testcases to the testset
    client.assign_testcases(
        project_id, testset_id,
        [tc["id"] for tc in pattern_to_testcase.values()],
    )

    # 5) TestExecution — one per publish, links back via foreign id form
    testcase_id_list = [tc["id"] for tc in pattern_to_testcase.values()]
    fired_patterns = {f["pattern"] for f in findings}
    fired_patterns_str = ", ".join(sorted(fired_patterns)) or "(none)"
    execution = client.create_testexecution(
        project_id, testset_id, testcase_id_list,
        name=f"exec:{trace_id}/{run_id}",
        description=(
            f"AgentClinic execution | trace {trace_id} run {run_id} | "
            f"schema {schema_version} | "
            f"result map: pattern fired -> Failed, clean -> Passed | "
            f"fired patterns: [{fired_patterns_str}]"
        ),
        source="ThirdParty",
        source_details=f"AgentClinic core / {schema_version}",
    )
    execution_id = execution["id"]

    # 6) TestCaseLog per testcase, then override result based on findings.
    #
    # Server quirk (reverse-engineered 2026-06-24, exec 4ab12aca + c003a2e2):
    # Test Manager auto-increments testcaselog.runId from 0 -> 1 shortly
    # after create_testcaselog. The POST response returns the runId=0
    # row; the paged endpoint then filters to runId=max and surfaces only
    # runId=1. UiPath's UI reads paged, so override writes to the POST-
    # returned id land on a phantom row the user never sees. The runId
    # promotion takes <~1s server-side but races against fast Cloud Coded
    # Agent runtimes.
    #
    # Defense:
    #   (1) Poll over a ~2s window collecting EVERY log id we ever observe
    #       for (execution, testcase) -- this catches runId=0 before
    #       promotion AND runId=1 after.
    #   (2) Always union in the POST-returned id as a baseline (in case
    #       the paged endpoint never surfaces it at all, which we've
    #       observed when server hasn't indexed yet).
    #   (3) Override EVERY collected id. The phantom runId=0 row being
    #       overridden too is harmless -- UI only reads runId=max.
    SETTLE_WINDOW_S = 2.0
    POLL_INTERVAL_S = 0.3

    logs: list[dict] = []
    for pattern, tc in pattern_to_testcase.items():
        created_log = client.create_testcaselog(
            project_id, testcase_id=tc["id"],
            testexecution_id=execution_id,
            testcase_version=schema_version,
            external_execution_id=f"{trace_id}::{run_id}",
        )
        fired = pattern in fired_patterns
        target_result = "Failed" if fired else "Passed"
        reason = _result_reason(pattern, fired, findings)

        seen_ids: set[str] = set()
        created_id = (created_log or {}).get("id")
        if created_id:
            seen_ids.add(created_id)

        deadline = time.monotonic() + SETTLE_WINDOW_S
        while True:
            for ui_log in client.list_testcaselogs(
                    project_id, execution_id, testcase_id=tc["id"]):
                lid = ui_log.get("id")
                if lid:
                    seen_ids.add(lid)
            if time.monotonic() >= deadline:
                break
            time.sleep(POLL_INTERVAL_S)

        if not seen_ids:
            raise TestManagerError(
                f"create_testcaselog returned no id AND paged list stayed "
                f"empty for {SETTLE_WINDOW_S}s under "
                f"(execution={execution_id[:8]}, testcase={tc['id'][:8]})")

        for log_id in sorted(seen_ids):
            entry = {
                "id": log_id,
                "pattern": pattern,
                "result": target_result,
                "result_override_error": None,
            }
            try:
                client.override_testcaselog_result(
                    project_id, log_id, target_result, reason)
            except Exception as e:  # noqa: BLE001 -- one log failing to
                # set its result shouldn't abort the whole publish; surface
                # the log id and continue, the attachment still lands
                entry["result_override_error"] = f"{type(e).__name__}: {e}"
            logs.append(entry)

    # 7) Attachment: full markdown report on the TestExecution
    markdown = markdown_override if markdown_override is not None \
        else to_markdown(report)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8",
        prefix=f"{trace_id}_",
    ) as f:
        f.write(markdown)
        tmp_path = f.name
    try:
        attachment = client.upload_attachment(
            project_id, "testExecution", execution_id, tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "project": {
            "id": project_id, "name": project["name"],
            "prefix": project.get("projectPrefix"),
            "created_now": project_created,
        },
        "testcases": [
            {"id": tc["id"], "objKey": tc.get("objKey"),
             "pattern": pattern}
            for pattern, tc in pattern_to_testcase.items()
        ],
        "testset": {
            "id": testset_id, "name": testset.get("name"),
            "objKey": testset.get("objKey"),
        },
        "execution": {
            "id": execution_id, "name": execution.get("name"),
            "objKey": execution.get("objKey"),
        },
        "logs": logs,
        "attachment": {
            "id": attachment["id"], "fileName": attachment["fileName"],
            "fileSize": attachment["fileSize"],
            "attached_to": "testExecution",
        },
        "ui_url": (
            f"{cfg['base_url']}/projects/{project.get('projectPrefix')}/"
            f"executions/{execution.get('objKey', execution_id)}"
        ),
    }


def _result_reason(pattern: str, fired: bool, findings: list[dict]) -> str:
    if not fired:
        return (f"AgentClinic did not detect pattern `{pattern}` in this "
                "trace; PASS by absence of evidence.")
    matching = [f for f in findings if f["pattern"] == pattern]
    n = len(matching)
    # Each finding line: RM-F-... | severity=X confidence=Y | events: evt_a, evt_b
    # — the trace_event_ids are the evidence anchors a reviewer can jump back to.
    lines = [f"AgentClinic detected pattern `{pattern}` -- {n} finding(s):"]
    for f in matching:
        fid = f.get("finding_id", "?")
        sev = f.get("severity", "?")
        conf = f.get("confidence")
        event_ids = [
            span.get("trace_event_id")
            for span in f.get("evidence_spans", [])
            if span.get("trace_event_id")
        ]
        events_str = ", ".join(event_ids) if event_ids else "(no spans)"
        lines.append(
            f"  {fid} | severity={sev} confidence={conf} | events: {events_str}"
        )
    lines.append("Evidence-bound by finding_schema_v1; see attached report.")
    return "\n".join(lines)
