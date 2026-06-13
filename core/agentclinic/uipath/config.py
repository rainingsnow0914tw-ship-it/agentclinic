"""Resolve UiPath integration config.

Precedence (later wins): file -> environment variable. The file is the
working default, env lets CI override without touching disk."""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_FIELDS = (
    "app_id", "app_secret", "token_endpoint", "scope", "base_url",
    "org", "tenant",
)
REQUIRED_FIELDS = ("app_id", "app_secret", "token_endpoint", "scope",
                   "base_url")


class ConfigError(ValueError):
    pass


def load_config(path: str | Path | None = None) -> dict:
    """Load `.uipath/app.json` (or explicit path), then overlay env vars
    of the form `UIPATH_<FIELD>` (uppercased). Validates required fields."""
    file_cfg = _read_file(path) if path else _read_default_file()
    cfg = dict(file_cfg)
    for field in CONFIG_FIELDS:
        env_key = f"UIPATH_{field.upper()}"
        if env_key in os.environ:
            cfg[field] = os.environ[env_key]
    missing = [f for f in REQUIRED_FIELDS if not cfg.get(f)]
    if missing:
        raise ConfigError(
            f"UiPath config missing required fields: {missing}. "
            f"Set them in .uipath/app.json or env UIPATH_<FIELD>.")
    cfg["base_url"] = cfg["base_url"].rstrip("/")
    return cfg


def _read_file(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"UiPath config file not found: {p}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _read_default_file() -> dict:
    """Walk up from cwd looking for .uipath/app.json. Falls back to empty
    so env-only configurations work (e.g. CI with secrets injected)."""
    cur = Path.cwd().resolve()
    for parent in (cur, *cur.parents):
        candidate = parent / ".uipath" / "app.json"
        if candidate.exists():
            return _read_file(candidate)
    return {}
