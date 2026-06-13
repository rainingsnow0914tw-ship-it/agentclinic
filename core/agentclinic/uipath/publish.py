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
    testset = client.create_testset(
        project_id, name=testset_name,
        description=(f"AgentClinic run -- schema={schema_version}, "
                     f"score={score['value']}/100, "
                     f"{len(findings)} finding(s)"),
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
    execution = client.create_testexecution(
        project_id, testset_id, testcase_id_list,
        name=f"exec:{trace_id}/{run_id}",
        description=(f"AgentClinic execution for trace {trace_id}, "
                     f"run {run_id}; result mapping: pattern fired = "
                     f"Failed, pattern clean = Passed"),
        source="ThirdParty",
        source_details=f"AgentClinic core / {schema_version}",
    )
    execution_id = execution["id"]

    # 6) TestCaseLog per testcase, then override result based on findings
    fired_patterns = {f["pattern"] for f in findings}
    logs: list[dict] = []
    for pattern, tc in pattern_to_testcase.items():
        log = client.create_testcaselog(
            project_id, testcase_id=tc["id"],
            testexecution_id=execution_id,
            testcase_version=schema_version,
            external_execution_id=f"{trace_id}::{run_id}",
        )
        fired = pattern in fired_patterns
        target_result = "Failed" if fired else "Passed"
        reason = _result_reason(pattern, fired, findings)
        try:
            client.override_testcaselog_result(
                project_id, log["id"], target_result, reason)
        except Exception as e:  # noqa: BLE001 -- one log failing to
            # set its result shouldn't abort the whole publish; surface
            # the log id and continue, the attachment still lands
            log["_result_override_error"] = (
                f"{type(e).__name__}: {e}")
        log["_target_result"] = target_result
        log["_pattern"] = pattern
        logs.append(log)

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
        "logs": [
            {"id": lg["id"], "pattern": lg["_pattern"],
             "result": lg["_target_result"],
             "result_override_error": lg.get("_result_override_error")}
            for lg in logs
        ],
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
    confidences = sorted({f.get("confidence") for f in matching
                          if f.get("confidence") is not None})
    return (f"AgentClinic detected pattern `{pattern}` -- "
            f"{n} finding(s); confidence: {confidences}. "
            "Evidence-bound by finding_schema_v1; see attached report.")
