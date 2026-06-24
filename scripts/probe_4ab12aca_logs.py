"""Probe: 對 Coded Agent 在 Cloud 跑出的那條 execution 4ab12aca
列出所有 testcaselogs，看 server 端真實狀態。

CLI 本地跑沒問題、只有 Coded Agent 在 Cloud 跑才出 dup-log 顯示空白
→ 表示要嘛 paged list 列的 log 跟 UI 顯示的不是同一條，
   要嘛 list 漏了 UI 用的那條。

Probe 步驟：
1. 拉這條 execution 的所有 fields（找 UI 可能用的 hint）
2. paged list 所有 logs（不 filter testcase_id，看完整集合）
3. 對每個 log 單獨 GET 一次（看 single endpoint 跟 paged endpoint 有沒有欄位差）
4. 看 log 是否有 originalResult / currentResult / overrides 之類 hint 哪條是 UI 顯示
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

import requests
from agentclinic.uipath.auth import get_access_token
from agentclinic.uipath import load_config

CFG = load_config()
BASE = CFG["base_url"]
H = {"Authorization": f"Bearer {get_access_token(CFG)}",
     "Accept": "application/json", "Content-Type": "application/json"}

ACR2_PID = "a9034ddc-bbc5-0000-5d9e-0b49c3618104"
EXEC_ID = "4ab12aca-a3f1-0b00-83c4-0b49cd988b42"

print(f"=== probing execution {EXEC_ID[:8]} ===\n")

# 1) execution metadata
r = requests.get(f"{BASE}/api/v2/{ACR2_PID}/testexecutions/{EXEC_ID}",
                 headers=H, timeout=30)
print(f"[1] GET execution  HTTP {r.status_code}")
if r.status_code < 400:
    ex = r.json()
    print(f"    name: {ex.get('name')}")
    print(f"    objKey: {ex.get('objKey')}  status: {ex.get('status')}")
    print(f"    result: {ex.get('result')!r}")
    print(f"    source: {ex.get('source')!r}  sourceDetails: {ex.get('sourceDetails')!r}")
    print(f"    created: {ex.get('created')}  startTime: {ex.get('startTime')}")
    print(f"    all keys: {sorted(ex.keys())}")

# 2) paged list — full set under this execution
r = requests.get(
    f"{BASE}/api/v2/{ACR2_PID}/testcaselogs/testexecution/{EXEC_ID}/paged",
    headers=H, params={"top": 200}, timeout=30,
)
print(f"\n[2] paged list testcaselogs  HTTP {r.status_code}")
logs = r.json().get("data", []) if r.status_code < 400 else []
print(f"    {len(logs)} logs total under this execution\n")

for i, lg in enumerate(logs):
    print(f"  log #{i}:")
    print(f"    id           = {lg.get('id')}")
    print(f"    testCaseId   = {lg.get('testCaseId')}")
    print(f"    result       = {lg.get('result')!r}")
    print(f"    resultReason = {(lg.get('resultReason') or '')[:80]!r}")
    print(f"    created      = {lg.get('created')}")
    print(f"    keys         = {sorted(lg.keys())}")
    print()

# 3) GET each log singly — see if any extra fields surface
print(f"[3] GET each log individually:\n")
for i, lg in enumerate(logs):
    lid = lg["id"]
    r = requests.get(f"{BASE}/api/v2/{ACR2_PID}/testcaselogs/{lid}",
                     headers=H, timeout=30)
    print(f"  log #{i} id={lid[:8]}  HTTP {r.status_code}")
    if r.status_code < 400:
        single = r.json()
        # find any field NOT in paged response
        paged_keys = set(lg.keys())
        single_keys = set(single.keys())
        only_in_single = single_keys - paged_keys
        if only_in_single:
            print(f"    extra fields in single GET: {sorted(only_in_single)}")
            for k in sorted(only_in_single):
                v = single[k]
                v_str = str(v)[:120]
                print(f"      {k} = {v_str}")
        # specifically dump override-related fields
        for k in ("result", "resultReason", "originalResult", "currentResult",
                  "overrideResult", "overrides", "resultOverrides",
                  "overriddenResult", "overrideReason"):
            if k in single:
                v = single[k]
                v_str = str(v)[:120] if v else repr(v)
                print(f"    {k} = {v_str}")
    print()

# 4) try alternate endpoints UI might be hitting
print(f"[4] alt endpoint probes:\n")
ALT_PATHS = [
    f"/api/v2/{ACR2_PID}/testexecutions/{EXEC_ID}/testcaselogs",
    f"/api/v2/{ACR2_PID}/testexecutions/{EXEC_ID}/results",
    f"/api/v2/{ACR2_PID}/testresults?testExecutionId={EXEC_ID}",
]
for path in ALT_PATHS:
    r = requests.get(f"{BASE}{path}", headers=H, timeout=30)
    print(f"  GET {path}  HTTP {r.status_code}")
    if r.status_code < 400:
        try:
            body = r.json()
            if isinstance(body, dict) and "data" in body:
                print(f"    data count: {len(body['data'])}")
                if body["data"]:
                    print(f"    first row keys: {sorted(body['data'][0].keys())}")
            else:
                print(f"    body snip: {str(body)[:200]}")
        except Exception:
            print(f"    text snip: {r.text[:200]}")

print("\n=== done ===")
