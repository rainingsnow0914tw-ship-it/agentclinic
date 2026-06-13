"""Publish an AgentClinic report to UiPath Test Cloud.

One report -> one TestCase (named by trace_id/run_id, with foreignReference
for idempotent linkage) -> one markdown attachment. The project is reused
across reports (ensure_project is idempotent on name)."""
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
    """Push one report to Test Cloud and return tracking IDs.

    Returns a flat dict suitable for printing or storing as run metadata --
    ids for project, testcase, attachment + a UI-shaped URL so the user can
    open the testcase directly."""
    cfg = config or load_config()
    client = TestManagerClient(cfg)

    project, created = client.ensure_project(
        project_name, project_prefix,
        description=("Auto-managed by AgentClinic core; reports pushed by "
                     "publish_report(). Do not hand-edit."),
    )

    score = report["score"]
    findings = report["sections"]["2"]["findings"]
    s7 = report["sections"]["7"]
    has_budget = s7.get("budget_assessment") is not None

    tc_name = f"{report['trace_id']} / {report['run_id']}"
    description = (
        f"schema={report.get('schema_version', 'report-v?')}; "
        f"score={score['value']}/100 level={score['level']}; "
        f"{len(findings)} finding(s); "
        f"budget={'yes' if has_budget else 'no'}"
    )
    testcase = client.create_testcase(
        project["id"], tc_name,
        description=description,
        version=report.get("schema_version", "report-v2"),
        foreign_reference=f"{report['trace_id']}::{report['run_id']}",
    )

    markdown = markdown_override if markdown_override is not None \
        else to_markdown(report)
    # use a temp file so the upload API gets a real filename + the body
    # binary is streamed from disk, not memory
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8",
        prefix=f"{report['trace_id']}_",
    ) as f:
        f.write(markdown)
        tmp_path = f.name
    try:
        attachment = client.upload_attachment(
            project["id"], "testCase", testcase["id"], tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "project": {
            "id": project["id"],
            "name": project["name"],
            "prefix": project.get("projectPrefix"),
            "created_now": created,
        },
        "testcase": {
            "id": testcase["id"],
            "objKey": testcase["objKey"],
            "name": testcase["name"],
            "foreign_reference": testcase.get("foreignReference"),
        },
        "attachment": {
            "id": attachment["id"],
            "fileName": attachment["fileName"],
            "fileSize": attachment["fileSize"],
        },
        "ui_url": (
            f"{cfg['base_url']}/projects/{project.get('projectPrefix')}/"
            f"testCases/{testcase['objKey']}"
        ),
    }
