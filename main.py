"""AgentClinic Coded Agent entry -- UiPath Studio Web boundary.

A single run does both: analyze the trace into a deterministic forensic
report, then publish that report into UiPath Test Cloud (Test Set +
Execution + per-pattern TestCase Log + report attachment).

Credential resolution is delegated to core/agentclinic/uipath/config.py
load_config():
  - local dev: reads .uipath/app.json
  - Automation Cloud runtime: set the same fields as env vars
    (UIPATH_APP_ID / UIPATH_APP_SECRET / UIPATH_TOKEN_ENDPOINT /
    UIPATH_SCOPE / UIPATH_BASE_URL) and the file path is skipped.

If publish_to_test_cloud=True but publish fails (no creds, network,
schema mismatch, etc.) the analyze report still returns -- the
deterministic core is the load-bearing part and must not be lost to
an optional push step."""
from __future__ import annotations

import os
import sys
from typing import Any

from pydantic import BaseModel, Field

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"),
)

from agentclinic.cli import analyze_pipeline  # noqa: E402
from agentclinic.uipath import load_config, publish_report  # noqa: E402


class Input(BaseModel):
    trace: dict[str, Any] = Field(
        ..., description="Normalized agent trace dict (schema: TraceSchema v1)")
    publish_to_test_cloud: bool = Field(
        True,
        description="If true, push the report to UiPath Test Cloud after analyze")
    project_name: str = Field(
        "AgentClinic Reports v2",
        description="UiPath Test Manager project name (idempotent on name)")
    project_prefix: str = Field(
        "ACR2",
        description="Project prefix used when creating the project")


class Output(BaseModel):
    report: dict[str, Any] = Field(
        ..., description="Deterministic forensic report (schema: report-v2)")
    test_cloud: dict[str, Any] | None = Field(
        None,
        description="publish_report() result -- project/testset/execution/log "
                    "ids + attachment + ui_url. None if publish skipped/failed.")
    publish_error: str | None = Field(
        None,
        description="Error class+message if publish was requested but failed. "
                    "Analyze report still returns regardless.")


def main(input: Input) -> Output:
    report = analyze_pipeline(input.trace)

    test_cloud: dict[str, Any] | None = None
    publish_error: str | None = None
    if input.publish_to_test_cloud:
        try:
            cfg = load_config()
            test_cloud = publish_report(
                report,
                project_name=input.project_name,
                project_prefix=input.project_prefix,
                config=cfg,
            )
        except Exception as e:  # noqa: BLE001 -- analyze must survive
            # any push failure; surface error so caller can act
            publish_error = f"{type(e).__name__}: {e}"

    return Output(
        report=report,
        test_cloud=test_cloud,
        publish_error=publish_error,
    )
