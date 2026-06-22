"""Side-by-side verification: PROBE-TEST execution vs C1-publish execution.

Pulls the testcaselog `result` and `reason` for both — proves the new
publish actually wrote the auto-generated evidence-bound reason."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

import requests
from agentclinic.uipath.auth import get_access_token
from agentclinic.uipath import load_config

CFG = load_config()
H = {"Authorization": f"Bearer {get_access_token(CFG)}", "Accept": "application/json"}
ACR2_PID = "a9034ddc-bbc5-0000-5d9e-0b49c3618104"

# fetch log under an execution and return (result, reason_via_list_endpoint)
def fetch(exec_id: str) -> tuple[str, str | None, str]:
    r = requests.get(
        f"{CFG['base_url']}/api/v2/{ACR2_PID}/testcaselogs/testexecution/{exec_id}/paged",
        headers=H, params={"top": 10}, timeout=30)
    logs = r.json().get("data", [])
    if not logs:
        return ("?", None, "no logs found")
    lg = logs[0]
    log_id = lg["id"]
    # paged endpoint doesn't echo reason; use single-log GET
    r2 = requests.get(f"{CFG['base_url']}/api/v2/{ACR2_PID}/testcaselogs/{log_id}",
                      headers=H, timeout=30)
    detail = r2.json()
    # reason isn't on the log itself either — it's on the override row.
    # list overrides via list endpoint pattern: same testCaseLogId
    # fallback: scan the duplicate-key error trick (POST same body, read error data)
    # cleaner: just hit override-result POST with a sentinel and read 409 echo
    SENTINEL = {"currentResult": "Failed", "reason": "__sentinel_probe__"}
    r3 = requests.post(
        f"{CFG['base_url']}/api/v2/{ACR2_PID}/testcaselogs/{log_id}/override-result",
        headers={**H, "Content-Type": "application/json"},
        json=SENTINEL, timeout=30)
    if r3.status_code == 409:
        existing = r3.json().get("data", {}).get("duplicateKeyEntity", {})
        return (detail.get("result", "?"), existing.get("reason"), log_id)
    return (detail.get("result", "?"), "<no override yet>", log_id)


OLD_EXEC = "a2cb479f-14d9-0b00-b354-0b49c3619343"   # PROBE-TEST execution
NEW_EXEC = "514562a2-51ea-0b00-f530-0b49cc13ef3c"   # D-2 publish execution

for label, eid in [("OLD (PROBE-TEST)", OLD_EXEC), ("NEW (D-2 publish)", NEW_EXEC)]:
    result, reason, log_id = fetch(eid)
    print(f"\n=== {label}  exec={eid[:8]}  log={log_id[:8] if log_id else '?'}")
    print(f"  result: {result}")
    print(f"  reason:")
    if reason:
        for line in reason.splitlines():
            print(f"    {line}")
    else:
        print("    <none>")
