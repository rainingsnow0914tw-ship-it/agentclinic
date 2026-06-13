"""Test Manager REST client -- thin wrapper, no business logic.

Mirrors the four endpoints the 2026-06-13 spike walked through, plus
`find_project_by_name` so `ensure_project` can be idempotent (don't create
a new project per analyze run)."""
from __future__ import annotations

from pathlib import Path

import requests

from .auth import get_access_token


class TestManagerError(RuntimeError):
    pass


class TestManagerClient:
    def __init__(self, config: dict):
        self.cfg = config
        self.base = config["base_url"]

    def _auth_header(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {get_access_token(self.cfg)}",
            "Accept": "application/json",
        }

    def _check(self, r: requests.Response, what: str) -> None:
        if r.status_code >= 400:
            raise TestManagerError(
                f"{what} failed: HTTP {r.status_code} -- {r.text}")

    def list_projects(self, search: str | None = None,
                      top: int = 50) -> list[dict]:
        params: dict = {"top": top}
        if search:
            params["search"] = search
        r = requests.get(f"{self.base}/api/v2/projects",
                         headers=self._auth_header(),
                         params=params, timeout=30)
        self._check(r, "list projects")
        return r.json().get("data", [])

    def find_project_by_name(self, name: str) -> dict | None:
        for p in self.list_projects(search=name):
            if p.get("name") == name:
                return p
        return None

    def create_project(self, name: str, project_prefix: str,
                       description: str = "", is_active: bool = True) -> dict:
        r = requests.post(
            f"{self.base}/api/v2/projects",
            headers={**self._auth_header(),
                     "Content-Type": "application/json"},
            json={"name": name, "projectPrefix": project_prefix,
                  "description": description, "isActive": is_active},
            timeout=30,
        )
        self._check(r, "create project")
        return r.json()

    def ensure_project(self, name: str, project_prefix: str,
                       description: str = "") -> tuple[dict, bool]:
        """Return (project, created_now). Idempotent on (name)."""
        existing = self.find_project_by_name(name)
        if existing:
            return existing, False
        return self.create_project(name, project_prefix, description), True

    def create_testcase(self, project_id: str, name: str,
                        description: str = "", version: str = "1.0",
                        foreign_reference: str | None = None) -> dict:
        # containerId = projectId uses the project's root container (spike
        # verified). No need to pre-build folders for the v1 push path.
        body: dict = {
            "name": name,
            "description": description,
            "projectId": project_id,
            "containerId": project_id,
            "version": version,
        }
        if foreign_reference:
            body["foreignReference"] = foreign_reference
        r = requests.post(
            f"{self.base}/api/v2/{project_id}/testcases",
            headers={**self._auth_header(),
                     "Content-Type": "application/json"},
            json=body, timeout=30,
        )
        self._check(r, "create testcase")
        return r.json()

    def upload_attachment(self, project_id: str, object_type: str,
                          object_id: str, file_path: str | Path) -> dict:
        """multipart upload. object_type is one of the TM ObjectType enum
        values (testCase, testSet, testExecution, testCaseLog, defect, ...)."""
        path = Path(file_path)
        with open(path, "rb") as f:
            r = requests.post(
                f"{self.base}/api/v2/{project_id}/attachments/"
                f"{object_type}/{object_id}/upload",
                headers=self._auth_header(),
                data={"objectType": object_type},
                files={"file": (path.name, f)},
                timeout=60,
            )
        self._check(r, "upload attachment")
        return r.json()
