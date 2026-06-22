"""D-step: assign CK as Project Owner on AgentClinic projects.
Try ACS first (small blast radius); on success, do ACR + ACR2."""
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

# CK identity (from JWT decode of .env UIPATH_ACCESS_TOKEN; sub claim)
CK = {
    "identifier": "4122310e-54e5-4390-acf4-48842de89152",
    "identityName": "rainingsnow0914.tw@gmail.com",
    "email": "rainingsnow0914.tw@gmail.com",
    "displayName": "Chloe Kao",
    "firstName": "Chloe",
    "lastName": "Kao",
    "objectType": "directoryUser",
    "source": "auth0|google",
}

PROJECTS = {
    "ACS":  ("AgentClinic Spike",     "5fd315df-b9c5-0000-e233-0b49c35ae186"),
    "ACR":  ("AgentClinic Reports",   "0775050a-bac5-0000-7410-0b49c360683b"),
    "ACR2": ("AgentClinic Reports v2","a9034ddc-bbc5-0000-5d9e-0b49c3618104"),
}

ORDER = sys.argv[1] if len(sys.argv) > 1 else "ACS"
target = list(PROJECTS.values()) if ORDER == "ALL" else [PROJECTS[ORDER]] if ORDER in PROJECTS else []
if not target:
    sys.exit(f"unknown order: {ORDER}")

for name, pid in target:
    print(f"\n=== assign Project Owner to CK on '{name}' ({pid})")
    body = {
        "projectId": pid,
        "directoryUsers": [CK],
        "roleNames": ["Project Owner"],
    }
    r = requests.post(
        f"{BASE}/api/v2/{pid}/permissions/project/assignroles",
        headers=H, json=body, timeout=30,
    )
    print(f"  HTTP {r.status_code}")
    try:
        print("  body:", json.dumps(r.json(), indent=2, ensure_ascii=False)[:800])
    except Exception:
        print("  body:", r.text[:500])

    # verify
    v = requests.get(
        f"{BASE}/api/v2/{pid}/permissions/project",
        headers=H, params={"top": 50}, timeout=30,
    )
    members = (v.json() or {}).get("data", [])
    print(f"  members now ({len(members)}):")
    for m in members:
        roles = m.get('roles', [])
        role_names = [r['name'] if isinstance(r, dict) else r for r in roles]
        print(f"    - {m.get('identityName','?')} / objectType={m.get('objectType')} / roles={role_names}")
