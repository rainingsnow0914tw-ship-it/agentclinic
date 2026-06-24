"""Hotfix: write the real publish_report reason onto the testcaselog
under execution 4ab12aca (the Cloud Coded Agent run UiPath's eval
team triggered on 2026-06-23). That run hit the Cloud-runtime race
window in publish.py L130 (list_testcaselogs returning [] right
after POST), the override branch raised TestManagerError, and main.py
swallowed it into publish_error -- leaving the log with result=None
and reason='' even though server happily accepts override-result on
that log id (verified via probe).

The publish.py + client.py fix landed in the same change as this
script (retries + union POST-returned id). This script is a one-off
to clean up the already-published bad execution; future Cloud runs
won't need it.
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
PID = "a9034ddc-bbc5-0000-5d9e-0b49c3618104"           # ACR2
LOG_ID = "cc406f56-4c6f-5d00-f8c9-0b49cd988b99"        # log under 4ab12aca

# Same findings shape publish_report would have generated for
# 01_hard_hat_loop.golden.json (mirror of hotfix_acr2_86_reason.py).
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
print(f"Writing reason to log {LOG_ID[:8]}")
print("---")
print(reason)
print("---")

body = {"currentResult": "Failed", "reason": reason}
url = (f"{CFG['base_url']}/api/v2/{PID}/testcaselogs/"
       f"{LOG_ID}/override-result")
r = requests.post(url, headers=H, json=body, timeout=30)
# (logId, currentResult) is unique-constrained; if there's already a
# Failed override (e.g. earlier hotfix attempt), GET it, DELETE it,
# then retry. Endpoint discovered by probing:
#   GET  /override-result          -> the current override record
#   DELETE /override-result/{ovid} -> 204 No Content
if r.status_code == 409:
    existing = requests.get(url, headers=H, timeout=30).json()
    ovid = existing.get("id")
    print(f"409: existing override {ovid[:8] if ovid else '?'} -- "
          f"deleting and retrying")
    d = requests.delete(f"{url}/{ovid}", headers=H, timeout=30)
    if d.status_code not in (200, 204):
        print(f"DELETE failed HTTP {d.status_code}: {d.text[:200]}")
    r = requests.post(url, headers=H, json=body, timeout=30)

print(f"\nHTTP {r.status_code}")
if r.status_code >= 400:
    print(r.text[:500])
else:
    print("OK -- F5 the Override Result dialog in UI to confirm.")
