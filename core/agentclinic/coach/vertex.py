"""VertexCoach -- live Gemini via Vertex AI REST + ADC.

Auth is OAuth Bearer using whatever access token is supplied (env var
GCP_ACCESS_TOKEN is the simplest path; refresh with
`gcloud auth print-access-token` for demos).

Stays inside the boundary contract via two layers:
1. `responseSchema` forces the model to emit `{"remediation": str}` only.
2. Validator (apply.py -> validator.py) still rejects judge-reserved
   phrases / overlength text; rejection silently falls back to the
   deterministic remediation.

If auth is unconfigured (no token / no project), `coach()` returns an
error result and the orchestrator falls back -- pipeline never crashes
on Vertex misconfig."""
from __future__ import annotations

import json
import os

import requests

from .base import CoachResult

VERTEX_DEFAULT_MODEL = "gemini-2.5-flash"
VERTEX_DEFAULT_REGION = "us-central1"

PROMPT_TEMPLATE = """You are coaching an AI agent's developer. Below is a
finding from a DETERMINISTIC forensic analyzer about a quality issue in
the agent's execution trace. Your one job is to rewrite the `remediation`
text in a friendlier, more action-oriented tone.

ABSOLUTE CONSTRAINTS (any violation -> your output is discarded):
1. Do NOT change the verdict, severity, or pattern -- a rule engine
   already judged this. Never say "this might be fine", "actually I
   think", "downgrade", "false positive", or similar phrases that imply
   you re-judged.
2. Do NOT introduce NEW remediations or new findings.
3. Output ONLY a JSON object: {{"remediation": "your rewritten text"}}.
4. Length: under 1000 characters total.

Pattern: {pattern}
Severity: {severity}
Original remediation:
{original}
"""


class VertexCoach:
    backend_name = "vertex"

    def __init__(self, *, project: str | None = None,
                 region: str | None = None, model: str | None = None,
                 access_token: str | None = None, timeout: float = 30.0):
        self.project = project or os.environ.get("GCP_PROJECT", "")
        self.region = region or os.environ.get(
            "GCP_REGION", VERTEX_DEFAULT_REGION)
        self.model = model or os.environ.get(
            "VERTEX_MODEL", VERTEX_DEFAULT_MODEL)
        self.access_token = access_token or os.environ.get(
            "GCP_ACCESS_TOKEN", "")
        self.timeout = timeout

    def coach(self, finding: dict, trace: dict) -> CoachResult:
        if not self.project or not self.access_token:
            return CoachResult(
                remediation=None, backend=self.backend_name,
                model=self.model,
                error="GCP_PROJECT or GCP_ACCESS_TOKEN env var missing",
            )
        prompt = PROMPT_TEMPLATE.format(
            pattern=finding["pattern"], severity=finding["severity"],
            original=finding["remediation"],
        )
        url = (f"https://{self.region}-aiplatform.googleapis.com/v1/"
               f"projects/{self.project}/locations/{self.region}/"
               f"publishers/google/models/{self.model}:generateContent")
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "remediation": {"type": "STRING"}
                    },
                    "required": ["remediation"],
                },
                "temperature": 0.2,
                "maxOutputTokens": 800,
            },
        }
        try:
            r = requests.post(
                url, json=body, timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
            )
        except Exception as e:  # noqa: BLE001 -- network / auth errors all
            # collapse to one fallback path
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
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            payload = json.loads(text)
            remediation = payload.get("remediation")
        except Exception as e:  # noqa: BLE001 -- malformed response also
            # falls back; validator never sees garbage
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
