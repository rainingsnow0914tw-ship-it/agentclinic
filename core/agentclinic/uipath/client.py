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

    def find_testcase_by_name(self, project_id: str,
                              name: str) -> dict | None:
        """Look up a testcase by exact name within a project. Used for
        per-pattern testcase reuse (don't create a new testcase every
        publish when the same pattern recurs)."""
        r = requests.get(
            f"{self.base}/api/v2/{project_id}/testcases",
            headers=self._auth_header(),
            params={"search": name, "top": 50}, timeout=30,
        )
        self._check(r, "list testcases")
        for tc in r.json().get("data", []):
            if tc.get("name") == name:
                return tc
        return None

    def ensure_testcase(self, project_id: str, name: str,
                        description: str = "", version: str = "1.0",
                        foreign_reference: str | None = None
                        ) -> tuple[dict, bool]:
        """Idempotent on (project, name). Useful for per-pattern testcases."""
        existing = self.find_testcase_by_name(project_id, name)
        if existing:
            return existing, False
        return self.create_testcase(project_id, name, description, version,
                                    foreign_reference), True

    def create_testset(self, project_id: str, name: str,
                       description: str = "", source: str = "ThirdParty",
                       source_details: str = "") -> dict:
        body = {
            "name": name,
            "description": description,
            "projectId": project_id,
            "containerId": project_id,
            "source": source,
            "sourceDetails": source_details,
            "enableCoverage": False,
        }
        r = requests.post(
            f"{self.base}/api/v2/{project_id}/testsets",
            headers={**self._auth_header(),
                     "Content-Type": "application/json"},
            json=body, timeout=30,
        )
        self._check(r, "create testset")
        return r.json()

    def assign_testcases(self, project_id: str, testset_id: str,
                         testcase_ids: list[str]) -> None:
        """Body is a raw UUID array per swagger."""
        r = requests.post(
            f"{self.base}/api/v2/{project_id}/testsets/"
            f"{testset_id}/assigntestcases",
            headers={**self._auth_header(),
                     "Content-Type": "application/json"},
            json=testcase_ids, timeout=30,
        )
        self._check(r, "assign testcases")

    def create_testexecution(self, project_id: str, testset_id: str,
                             testcase_ids: list[str],
                             name: str = "", description: str = "",
                             source: str = "ThirdParty",
                             source_details: str = "") -> dict:
        # UiPath requires BOTH testSetId and testCaseIds even though
        # testset already owns them; under-the-hood the execution row is
        # written per-testcase and the testSetId scopes the run
        body = {
            "projectId": project_id,
            "testSetId": testset_id,
            "testCaseIds": testcase_ids,
            "name": name,
            "description": description,
            "source": source,
            "sourceDetails": source_details,
        }
        r = requests.post(
            f"{self.base}/api/v2/{project_id}/testexecutions",
            headers={**self._auth_header(),
                     "Content-Type": "application/json"},
            json=body, timeout=30,
        )
        self._check(r, "create testexecution")
        # 201 may return an empty body or just the new id; fall back to
        # newest execution under this testset
        try:
            return r.json()
        except Exception:
            return self._fetch_latest_execution(project_id, testset_id)

    def _fetch_latest_execution(self, project_id: str,
                                testset_id: str) -> dict:
        r = requests.get(
            f"{self.base}/api/v2/{project_id}/testexecutions",
            headers=self._auth_header(),
            params={"testsetId": testset_id, "orderby": "created desc",
                    "top": 1}, timeout=30,
        )
        self._check(r, "fetch latest execution")
        data = r.json().get("data", [])
        if not data:
            raise TestManagerError(
                "execution created (201) but no row visible under "
                f"testset {testset_id}")
        return data[0]

    def create_testcaselog(self, project_id: str, testcase_id: str,
                           testexecution_id: str,
                           testcase_version: str = "1.0",
                           external_execution_id: str = "") -> dict:
        body = {
            "testCaseId": testcase_id,
            "testExecutionId": testexecution_id,
            "testCaseVersion": testcase_version,
            "externalTestExecutionId": external_execution_id,
        }
        r = requests.post(
            f"{self.base}/api/v2/{project_id}/testcaselogs",
            headers={**self._auth_header(),
                     "Content-Type": "application/json"},
            json=body, timeout=30,
        )
        self._check(r, "create testcaselog")
        try:
            return r.json()
        except Exception:
            # 201 with empty body -- look up by testexecution + testcase
            return self._fetch_log(project_id, testexecution_id, testcase_id)

    def _fetch_log(self, project_id: str, execution_id: str,
                   testcase_id: str) -> dict:
        # Kept for backward compatibility with create_testcaselog's fallback,
        # but note: server sometimes creates duplicate logs per (testCase,
        # execution); the paged endpoint may list a stale duplicate as the
        # first entry. New callers should prefer list_testcaselogs() and
        # iterate ALL matching rows.
        logs = self.list_testcaselogs(project_id, execution_id, testcase_id)
        if not logs:
            raise TestManagerError(
                f"created log not visible under execution {execution_id}")
        return logs[0]

    def list_testcaselogs(self, project_id: str, execution_id: str,
                          testcase_id: str | None = None) -> list[dict]:
        """List ALL logs under an execution; optional filter by testcase_id.

        Why this exists: the server occasionally writes duplicate testcaselog
        rows for the same (testCase, execution) tuple per POST. UiPath's UI
        and the paged endpoint then surface one row (often the older one),
        while create_testcaselog's POST response id may point at the other.
        Override-result writes only land on the id you give it. To make the
        UI-visible row carry the evidence-bound reason, call this method
        and override every row it returns.
        """
        r = requests.get(
            f"{self.base}/api/v2/{project_id}/testcaselogs/"
            f"testexecution/{execution_id}/paged",
            headers=self._auth_header(),
            params={"top": 200}, timeout=30,
        )
        self._check(r, "list testcaselogs by execution")
        logs = r.json().get("data", [])
        if testcase_id:
            logs = [lg for lg in logs if lg.get("testCaseId") == testcase_id]
        return logs

    def override_testcaselog_result(self, project_id: str, log_id: str,
                                    result: str, reason: str) -> dict:
        """result in {'Passed','Failed','Restricted','None'}. The override
        endpoint takes the *current* result + a reason; UiPath then flips
        the log to the opposite (so we always pass the desired result here
        and let UiPath route from default 'None'/'Passed' to ours)."""
        body = {"currentResult": result, "reason": reason}
        r = requests.post(
            f"{self.base}/api/v2/{project_id}/testcaselogs/"
            f"{log_id}/override-result",
            headers={**self._auth_header(),
                     "Content-Type": "application/json"},
            json=body, timeout=30,
        )
        self._check(r, "override testcaselog result")
        try:
            return r.json()
        except Exception:
            return {}

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
