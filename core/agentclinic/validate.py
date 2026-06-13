"""Schema boundary: every trace entering and every finding leaving the engine
is validated against the Evidence Contract. A finding that fails its contract
(e.g. no evidence span) is a bug, not a degraded result."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

DEFAULT_CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"


class TraceSchemaError(ValueError):
    """Raised when an input trace violates trace_schema_v1."""


class FindingContractError(ValueError):
    """Raised when the engine produces a finding violating finding_schema_v1."""


def contracts_dir() -> Path:
    override = os.environ.get("AGENTCLINIC_CONTRACTS")
    return Path(override) if override else DEFAULT_CONTRACTS_DIR


@lru_cache(maxsize=None)
def _load_validator(contracts_dir_str: str, schema_filename: str) -> Draft202012Validator:
    # cache key includes the resolved contracts dir so an AGENTCLINIC_CONTRACTS
    # change mid-process is honored, never served stale
    schema_path = Path(contracts_dir_str) / schema_filename
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    # FORMAT_CHECKER enforces "format: date-time" etc. (requires the
    # rfc3339-validator package; without it, format is annotation-only)
    return Draft202012Validator(
        schema, format_checker=Draft202012Validator.FORMAT_CHECKER
    )


def _format_errors(errors) -> str:
    lines = []
    for err in errors:
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        lines.append(f"  at {loc}: {err.message}")
    return "\n".join(lines)


def validate_trace(trace: dict) -> None:
    validator = _load_validator(str(contracts_dir()), "trace_schema_v1.json")
    errors = sorted(validator.iter_errors(trace), key=lambda e: list(e.absolute_path))
    if errors:
        raise TraceSchemaError(
            "trace violates trace_schema_v1:\n" + _format_errors(errors)
        )


def validate_finding(finding: dict) -> None:
    validator = _load_validator(str(contracts_dir()), "finding_schema_v1.json")
    errors = sorted(validator.iter_errors(finding), key=lambda e: list(e.absolute_path))
    if errors:
        raise FindingContractError(
            f"finding {finding.get('finding_id', '<no id>')} violates finding_schema_v1:\n"
            + _format_errors(errors)
        )
