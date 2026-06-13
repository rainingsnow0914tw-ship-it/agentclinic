"""UiPathCoach -- LLM via UiPath's platform-native AgentHub LLM Gateway.

Why this backend matters for Track 3 framing: every coach call rides
UiPath's AI Trust Layer (audit log + PII redaction + usage governance),
so the LLM stays *inside* the platform. No external API key, no third-
party billing, no Platform Usage demerit for "external LLM" framing.

Auth path discovered 2026-06-13:
- External Application + client_credentials grant.
- Scope: any OR.* set (we use the union the External App was granted).
  OR.* and TM.* CANNOT share a token (different audience) -- this coach
  manages its own token, separate from uipath/auth.py's cache.
- Endpoint: {base}/agenthub_/llm/api/chat/completions (NOT
  llmgateway_/ -- that path is for a different service plane).
- Required header: X-UiPath-LlmGateway-NormalizedApi-ModelName.
- Required model names: SDK constants in
  uipath.platform.chat._llm_gateway_service (verified live: gpt-4o-mini-
  2024-07-18, gpt-4o-2024-08-06, gemini-2.5-flash work as-is; Claude is
  prefixed `anthropic.claude-3-...-v1:0`)."""
from __future__ import annotations

import json
import os
import threading
import time

import requests

from .base import CoachResult

DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"
DEFAULT_TIMEOUT = 30.0
_EARLY_REFRESH_SECONDS = 60

PROMPT_TEMPLATE = """You are coaching an AI agent's developer. Below is a
finding from a DETERMINISTIC forensic analyzer about a quality issue in
the agent's execution trace. Rewrite the `remediation` text in a friendly,
action-oriented tone.

ABSOLUTE CONSTRAINTS (any violation -> your output is discarded):
1. Do NOT change the verdict, severity, or pattern. A rule engine
   already judged this. Never say "this might be fine", "actually I
   think...", "downgrade", "false positive", or any phrase that implies
   you re-judged.
2. Do NOT introduce NEW remediations or new findings.
3. Output ONLY valid JSON: {{"remediation": "your rewritten text"}}.
   No markdown, no commentary outside the JSON.
4. Length: under 1000 characters total.

Pattern: {pattern}
Severity: {severity}
Original remediation:
{original}
"""


class UiPathCoach:
    backend_name = "uipath"

    def __init__(self, *, base_url: str | None = None,
                 token_endpoint: str | None = None,
                 app_id: str | None = None,
                 app_secret: str | None = None,
                 scope: str | None = None,
                 model: str | None = None,
                 timeout: float = DEFAULT_TIMEOUT):
        # Lazy import so the coach module doesn't hard-depend on
        # uipath/config.py when this backend isn't used.
        from ..uipath.config import load_config
        cfg = load_config()
        derived_base = self._derive_llm_base(cfg["base_url"])
        self.base_url = (base_url
                         or os.environ.get("UIPATH_LLM_BASE_URL")
                         or derived_base)
        self.token_endpoint = (token_endpoint
                               or os.environ.get("UIPATH_TOKEN_ENDPOINT")
                               or cfg["token_endpoint"])
        self.app_id = (app_id or os.environ.get("UIPATH_APP_ID")
                       or cfg["app_id"])
        self.app_secret = (app_secret
                           or os.environ.get("UIPATH_APP_SECRET")
                           or cfg["app_secret"])
        self.scope = (scope or os.environ.get("UIPATH_LLM_SCOPE")
                      or self._derive_or_scope(cfg["scope"]))
        self.model = (model or os.environ.get("UIPATH_LLM_MODEL")
                      or DEFAULT_MODEL)
        self.timeout = timeout
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._lock = threading.Lock()

    @staticmethod
    def _derive_llm_base(testmanager_base: str) -> str:
        """`base_url` in app.json is the testmanager_ prefix; derive the
        agenthub_/llm/api sibling under the same org/tenant."""
        trimmed = testmanager_base.rstrip("/")
        # strip the trailing service segment (testmanager_) -> host+tenant
        host_tenant = trimmed.rsplit("/", 1)[0]
        return f"{host_tenant}/agenthub_/llm/api"

    @staticmethod
    def _derive_or_scope(scope_string: str) -> str:
        """LLM Gateway requires the OR.* audience; filter the app.json
        scope union down to those tokens so we don't accidentally trip
        invalid_scope by mixing audiences."""
        return " ".join(s for s in scope_string.split() if s.startswith("OR."))

    def _get_token(self) -> str:
        now = time.time()
        with self._lock:
            if self._token and now < self._token_expires_at:
                return self._token
        try:
            r = requests.post(
                self.token_endpoint,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "scope": self.scope,
                },
                timeout=self.timeout,
            )
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                f"token exchange network error: {type(e).__name__}: {e}"
            ) from e
        if r.status_code != 200:
            raise RuntimeError(
                f"token exchange failed: HTTP {r.status_code} -- "
                f"{r.text[:200]}")
        body = r.json()
        with self._lock:
            self._token = body["access_token"]
            self._token_expires_at = now + max(
                0, int(body.get("expires_in", 3600)) - _EARLY_REFRESH_SECONDS)
            return self._token

    def coach(self, finding: dict, trace: dict) -> CoachResult:
        prompt = PROMPT_TEMPLATE.format(
            pattern=finding["pattern"], severity=finding["severity"],
            original=finding["remediation"],
        )
        try:
            token = self._get_token()
        except Exception as e:  # noqa: BLE001 -- one token failure must
            # not abort the publish; fall back per finding
            return CoachResult(
                remediation=None, backend=self.backend_name,
                model=self.model, error=f"auth: {type(e).__name__}: {e}",
            )
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-UIPATH-STREAMING-ENABLED": "false",
            "X-UiPath-LlmGateway-RequestingProduct": "agentclinic-coach",
            "X-UiPath-LlmGateway-RequestingFeature": "remediation-rewrite",
            "X-UiPath-LlmGateway-NormalizedApi-ModelName": self.model,
        }
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
            "temperature": 0.2,
        }
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        try:
            r = requests.post(url, json=body, headers=headers,
                              timeout=self.timeout)
        except Exception as e:  # noqa: BLE001
            return CoachResult(
                remediation=None, backend=self.backend_name,
                model=self.model,
                error=f"network: {type(e).__name__}: {e}",
            )
        if r.status_code != 200:
            return CoachResult(
                remediation=None, backend=self.backend_name,
                model=self.model,
                error=f"HTTP {r.status_code}: {r.text[:200]}",
            )
        try:
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            payload = json.loads(_extract_json(text))
            remediation = payload.get("remediation")
        except Exception as e:  # noqa: BLE001 -- malformed -> fallback,
            # validator never sees garbage
            return CoachResult(
                remediation=None, backend=self.backend_name,
                model=self.model,
                error=f"parse: {type(e).__name__}: {e}",
                raw_response=r.text[:500],
            )
        return CoachResult(
            remediation=remediation,
            backend=self.backend_name,
            model=self.model,
            raw_response=text,
        )


def _extract_json(text: str) -> str:
    """Models sometimes wrap JSON in ```json fences. Strip them so
    json.loads doesn't choke."""
    t = text.strip()
    if t.startswith("```"):
        # drop the first fence line and the trailing ```
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t
