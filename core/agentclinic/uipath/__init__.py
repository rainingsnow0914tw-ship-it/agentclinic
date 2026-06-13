"""UiPath Test Cloud integration -- one-way push of AgentClinic reports.

Production version of the 2026-06-13 P2 spike (PowerShell). Same 4-step
chain (token -> project -> testcase -> attachment), now wrapped as a
deterministic Python module with one-file-per-job discipline."""
from .config import load_config
from .client import TestManagerClient
from .publish import publish_report

__all__ = ["load_config", "TestManagerClient", "publish_report"]
