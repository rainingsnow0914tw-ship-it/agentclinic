"""D-step probe: list projects + roles + current members + find CK user.
Read-only. Will print everything we need to confirm before any POST."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

import requests
from agentclinic.uipath.auth import get_access_token

CFG = json.load(open(ROOT / ".uipath" / "app.json", encoding="utf-8"))
BASE = CFG["base_url"]
TOKEN = get_access_token(CFG)
H = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

def show(label, r):
    print(f"\n=== {label}  HTTP {r.status_code}")
    try:
        body = r.json()
    except Exception:
        body = r.text[:500]
    print(json.dumps(body, indent=2, ensure_ascii=False)[:2000])
    return body if r.status_code < 400 else None

# 1) projects we care about
projects = show("GET projects (top=50)",
                requests.get(f"{BASE}/api/v2/projects",
                             headers=H, params={"top": 50}, timeout=30))
acr_ids = {}
for p in (projects or {}).get("data", []):
    if p.get("name", "").startswith(("ACR", "AgentClinic")):
        acr_ids[p["name"]] = p["id"]
print("\nACR-family projects:", acr_ids)

if not acr_ids:
    sys.exit("no ACR projects found -- abort")

target_name, target_id = sorted(acr_ids.items())[-1]  # newest naming
print(f"\nUsing target project: {target_name} = {target_id}")

# 2) find CK in users
show("GET users search=raining",
     requests.get(f"{BASE}/api/users",
                  headers=H,
                  params={"search": "raining", "top": 10}, timeout=30))

# 3) available project roles
show(f"GET project roles (project={target_name})",
     requests.get(f"{BASE}/api/v2/{target_id}/permissions/project/roles",
                  headers=H, timeout=30))

# 4) current project members
show(f"GET current project permissions (project={target_name})",
     requests.get(f"{BASE}/api/v2/{target_id}/permissions/project",
                  headers=H, params={"top": 50}, timeout=30))

print("\n--- probe done, no writes performed ---")
