"""Probe what currentResult actually means.

Find ACR2:1 testcaselog under execution exec:trace_gold_001/run_deploy_4x.
POST override with currentResult='Failed' + a test reason.
GET the testcaselog back. Did result flip to Failed? Did reason show?
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

import requests
from agentclinic.uipath.auth import get_access_token

CFG = json.load(open(ROOT / ".uipath" / "app.json", encoding="utf-8"))
BASE = CFG["base_url"]
H = {"Authorization": f"Bearer {get_access_token(CFG)}",
     "Accept": "application/json", "Content-Type": "application/json"}

ACR2_PID = "a9034ddc-bbc5-0000-5d9e-0b49c3618104"

# 1) find the execution by name
r = requests.get(f"{BASE}/api/v2/{ACR2_PID}/testexecutions",
                 headers=H, params={"top": 50, "orderby": "created desc"},
                 timeout=30)
print("list executions HTTP", r.status_code)
target_exec = None
for e in r.json().get("data", []):
    if e.get("name", "").startswith("exec:trace_gold_001/run_deploy_4x"):
        target_exec = e
        break
if not target_exec:
    sys.exit("target execution not found")
exec_id = target_exec["id"]
print(f"  exec id: {exec_id}  objKey: {target_exec.get('objKey')}")

# 2) list its testcaselogs
r = requests.get(f"{BASE}/api/v2/{ACR2_PID}/testcaselogs/testexecution/{exec_id}/paged",
                 headers=H, params={"top": 50}, timeout=30)
print("\nlist testcaselogs HTTP", r.status_code)
logs = r.json().get("data", [])
print(f"  {len(logs)} logs under execution:")
for lg in logs:
    print(f"   - log id={lg.get('id')} testCaseId={lg.get('testCaseId')} "
          f"result={lg.get('result')!r} reason={lg.get('resultReason')!r}")

if not logs:
    sys.exit("no logs to probe")

target_log = logs[0]
log_id = target_log["id"]

# 3) POST override: currentResult='Failed' + reason
TEST_REASON = (
    "PROBE-TEST: AgentClinic detected pattern hard_hat_loop -- 1 finding(s):\n"
    "  RM-F-trace_gold_001-001 | severity=high confidence=0.85 | events: evt_42, evt_47\n"
    "Evidence-bound by finding_schema_v1; see attached report."
)
body = {"currentResult": "Failed", "reason": TEST_REASON}
print(f"\nPOST override-result on log {log_id}")
print(f"  body: {json.dumps(body, ensure_ascii=False)[:200]}")
r = requests.post(
    f"{BASE}/api/v2/{ACR2_PID}/testcaselogs/{log_id}/override-result",
    headers=H, json=body, timeout=30,
)
print(f"  HTTP {r.status_code}")
print(f"  resp: {r.text[:400]}")

# 4) re-GET the same log -- did result/reason update?
r = requests.get(f"{BASE}/api/v2/{ACR2_PID}/testcaselogs/{log_id}",
                 headers=H, timeout=30)
print(f"\nGET single log {log_id} HTTP {r.status_code}")
if r.status_code < 400:
    lg = r.json()
    print("  full log keys:", list(lg.keys()))
    for k in ("result", "resultReason", "overrideResult", "overriddenResult",
              "currentResult", "overrides", "resultOverrides"):
        if k in lg:
            print(f"   {k}={lg[k]!r}"[:300])

# 5) re-list logs under execution -- compare
r = requests.get(f"{BASE}/api/v2/{ACR2_PID}/testcaselogs/testexecution/{exec_id}/paged",
                 headers=H, params={"top": 50}, timeout=30)
print(f"\nrelist logs under exec  HTTP {r.status_code}")
for lg in r.json().get("data", []):
    if lg.get("id") == log_id:
        print(f"  THIS log keys: {list(lg.keys())}")
        for k in ("result", "resultReason", "overrideResult", "overrides"):
            if k in lg:
                print(f"   {k}={lg[k]!r}"[:300])
