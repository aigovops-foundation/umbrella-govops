"""overt-predicate-valid: the umbrella-govops.v1 OVERT predicate is present and valid."""
from __future__ import annotations

import json
from pathlib import Path

from ..runner import CheckResult

OVERT_PREDICATE_TYPE = "https://overt.dev/umbrella-govops/v1"


def check_overt_predicate_valid(repo: Path) -> CheckResult:
    details: list[str] = []
    predicate = repo / "overt" / "umbrella-govops.v1.json"
    if not predicate.exists():
        return CheckResult(
            "overt-predicate-valid",
            "warn",
            [
                "overt/umbrella-govops.v1.json not present — predicate not yet registered"
            ],
        )

    try:
        doc = json.loads(predicate.read_text())
    except json.JSONDecodeError as exc:
        return CheckResult(
            "overt-predicate-valid",
            "fail",
            [f"overt/umbrella-govops.v1.json: invalid JSON — {exc}"],
        )

    errors = 0
    if doc.get("predicateType") != OVERT_PREDICATE_TYPE:
        errors += 1
        details.append(
            f"predicateType {doc.get('predicateType')!r} != {OVERT_PREDICATE_TYPE!r}"
        )
    required = ["version", "frameworks", "domains", "controls", "evidenceTypes"]
    for k in required:
        if k not in doc:
            errors += 1
            details.append(f"missing required key {k!r}")

    if errors > 0:
        return CheckResult("overt-predicate-valid", "fail", details)
    return CheckResult(
        "overt-predicate-valid",
        "pass",
        ["overt/umbrella-govops.v1.json conforms"],
    )
