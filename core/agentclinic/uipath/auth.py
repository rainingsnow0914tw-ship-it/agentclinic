"""OAuth client_credentials exchange + in-process token cache.

UiPath staging hackathon Personal Access Tokens do not authenticate against
testmanager_ (verified 2026-06-13 spike: 5 lines of forensic evidence in
docs/P2_SPIKE_RESULT.md). External Application + client_credentials grant
is the supported path. This module hides that choice behind a single
`get_access_token(cfg)` call."""
from __future__ import annotations

import threading
import time

import requests


class TokenError(RuntimeError):
    pass


# in-process cache keyed by (token_endpoint, app_id) -- supports multi-tenant
# operation in one process without leaking tokens across configs
_CACHE: dict[tuple[str, str], dict] = {}
_LOCK = threading.Lock()

# refresh `_EARLY_REFRESH_SECONDS` before actual expiry to absorb clock drift
_EARLY_REFRESH_SECONDS = 60


def get_access_token(cfg: dict, *, force_refresh: bool = False) -> str:
    key = (cfg["token_endpoint"], cfg["app_id"])
    now = time.time()
    with _LOCK:
        cached = _CACHE.get(key)
        if not force_refresh and cached and now < cached["expires_at"]:
            return cached["token"]
    token, expires_in = _exchange(cfg)
    with _LOCK:
        _CACHE[key] = {
            "token": token,
            "expires_at": now + max(0, expires_in - _EARLY_REFRESH_SECONDS),
        }
    return token


def _exchange(cfg: dict) -> tuple[str, int]:
    # UiPath identity rejects mixed-audience scope in one exchange
    # (TM.* + OR.* together -> {"error":"invalid_scope"}). Test Cloud publish
    # only needs TM.*; filter the External App's full scope list to that
    # subset at exchange time. The Coach LLM Gateway path keeps its own
    # OR.*-scoped token (see coach/uipath_llm.py) and never shares this cache.
    tm_scope = " ".join(
        s for s in cfg["scope"].split() if s.startswith("TM.")
    )
    r = requests.post(
        cfg["token_endpoint"],
        data={
            "grant_type": "client_credentials",
            "client_id": cfg["app_id"],
            "client_secret": cfg["app_secret"],
            "scope": tm_scope,
        },
        timeout=30,
    )
    if r.status_code != 200:
        raise TokenError(
            f"client_credentials exchange failed: {r.status_code} {r.text}")
    body = r.json()
    if "access_token" not in body:
        raise TokenError(f"token endpoint returned no access_token: {body}")
    return body["access_token"], int(body.get("expires_in", 3600))


def clear_cache() -> None:
    """Drop the cache. Mostly for tests + debugging."""
    with _LOCK:
        _CACHE.clear()
