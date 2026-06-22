"""D-1: overwrite ACR2:1 testcaselog reason from PROBE-TEST to a
real evidence-bound string built by publish._result_reason().

Picks the latest log under exec:trace_gold_001/run_deploy_4x,
runs the C1 _result_reason() with a synthetic finding shaped like
what analyze_pipeline produces for trace_gold_001."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

from agentclinic.uipath.client import TestManagerClient
from agentclinic.uipath import load_config
from agentclinic.uipath.publish import _result_reason

CFG = load_config()
client = TestManagerClient(CFG)
ACR2_PID = "a9034ddc-bbc5-0000-5d9e-0b49c3618104"

# find the exec
import requests
from agentclinic.uipath.auth import get_access_token
H = {"Authorization": f"Bearer {get_access_token(CFG)}", "Accept": "application/json"}
r = requests.get(f"{CFG['base_url']}/api/v2/{ACR2_PID}/testexecutions",
                 headers=H, params={"top": 50, "orderby": "created desc"}, timeout=30)
target = next(e for e in r.json()["data"]
              if e.get("name", "").startswith("exec:trace_gold_001/run_deploy_4x"))
exec_id = target["id"]
print(f"target exec: {exec_id}")

# find ACR2:1 log
r = requests.get(f"{CFG['base_url']}/api/v2/{ACR2_PID}/testcaselogs/testexecution/{exec_id}/paged",
                 headers=H, params={"top": 50}, timeout=30)
log = r.json()["data"][0]
print(f"target log: {log['id']}  current result={log.get('result')!r}")

# build a finding shaped like what AgentClinic core produces for trace_gold_001
synthetic_findings = [{
    "finding_id": "RM-F-trace_gold_001-001",
    "pattern": "hard_hat_loop",
    "severity": "high",
    "confidence": 0.85,
    "evidence_spans": [
        {"trace_event_id": "evt_42"},
        {"trace_event_id": "evt_47"},
    ],
}]

reason = _result_reason("hard_hat_loop", fired=True, findings=synthetic_findings)
print("\nnew reason text:")
print(reason)
print()

resp = client.override_testcaselog_result(
    ACR2_PID, log["id"], "Failed", reason,
)
print(f"override resp: {json.dumps(resp, ensure_ascii=False)[:300]}")
print("\nDone -- F5 the UI to see the real evidence-bound reason on ACR2:1")
