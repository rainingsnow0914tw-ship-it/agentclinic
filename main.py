"""AgentClinic Coded Agent entry — UiPath Studio Web boundary.

input: a normalized agent trace dict; output: a deterministic forensic report dict.
All detection / scoring / suppression / Test Cloud writing / LLM coaching stays in
core/agentclinic/. This file is the platform-facing contract only."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

from agentclinic.cli import analyze_pipeline  # noqa: E402


@dataclass
class AnalyzeIn:
    trace: dict[str, Any]


@dataclass
class AnalyzeOut:
    report: dict[str, Any]


def main(input: AnalyzeIn) -> AnalyzeOut:
    report = analyze_pipeline(input.trace)
    return AnalyzeOut(report=report)
