"""Demo hotfix: manually write the real publish_report reason onto
the testcaselog that UiPath's UI actually shows for ACR2:86.

Root cause (also captured in task #13): `client.create_testcaselog`
POST causes the server to create TWO duplicate logs under the same
(testCaseId, testExecutionId). The fallback `_fetch_log` reads the
paged endpoint and returns the FIRST entry (the older / un-overridden
one). Subsequent override-result writes succeed against the "correct"
freshly-created log id — but UiPath UI and the paged endpoint list
the OTHER (stale, un-overridden) log. Result: UI Override Result
dialog is blank even though publish_report claims `result_override_
error: null`.

This script is a one-off: write the real publish-generated reason
onto the log id that UI actually shows for ACR2:86 execution
16ae3abb, so the demo video's climax shot has the right text.

Long-term fix (task #13) is in client.py — either read the new log
id from the POST Location header, or order paged DESC and take [0],
or check both logs and pick the one with originalResult=None.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

import requests
from agentclinic.uipath.auth import get_access_token
from agentclinic.uipath import load_config
from agentclinic.uipath.publish import _result_reason

CFG = load_config()
H = {"Authorization": f"Bearer {get_access_token(CFG)}",
     "Accept": "application/json", "Content-Type": "application/json"}
PID = "a9034ddc-bbc5-0000-5d9e-0b49c3618104"  # ACR2 project
LOG_ID = "d706ff3e-d744-5d00-1d67-0b49cca9bfa5"  # UI-visible log under ACR2:86

# Reproduce the exact reason publish_report() would have produced
findings = [{
    "finding_id": "RM-F-trace_gold_001-001",
    "pattern": "hard_hat_loop",
    "severity": "critical",
    "confidence": 0.9,
    "evidence_spans": [
        {"trace_event_id": "evt_0002"},
        {"trace_event_id": "evt_0003"},
        {"trace_event_id": "evt_0004"},
    ],
}]
reason = _result_reason("hard_hat_loop", fired=True, findings=findings)
print("Writing this reason to log", LOG_ID[:8])
print("---")
print(reason)
print("---")

body = {"currentResult": "Failed", "reason": reason}
r = requests.post(
    f"{CFG['base_url']}/api/v2/{PID}/testcaselogs/{LOG_ID}/override-result",
    headers=H, json=body, timeout=30,
)
print(f"\nHTTP {r.status_code}")
if r.status_code >= 400:
    print(r.text[:500])
else:
    print("OK — F5 the Override Result dialog in UI to see the new reason.")
