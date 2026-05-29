"""controls-have-checks: every control must declare at least one runnable check."""
from __future__ import annotations

from pathlib import Path

import yaml

from ..runner import CheckResult

VALID_RUNNERS = {"pytest", "python", "opa", "rego", "shell", "container"}


def check_controls_have_checks(repo: Path) -> CheckResult:
    details: list[str] = []
    errors = 0
    n_controls = 0

    for p in (repo / "domains").rglob("*.yaml"):
        try:
            doc = yaml.safe_load(p.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict) or doc.get("kind") != "Control":
            continue
        n_controls += 1
        checks = doc.get("checks") or []
        if not checks:
            errors += 1
            details.append(f"{p.relative_to(repo)}: no checks declared")
            continue
        for c in checks:
            if not isinstance(c, dict):
                errors += 1
                details.append(f"{p.relative_to(repo)}: check is not a mapping")
                continue
            if "id" not in c:
                errors += 1
                details.append(f"{p.relative_to(repo)}: check missing id")
            runner = c.get("runner")
            if runner and runner not in VALID_RUNNERS:
                errors += 1
                details.append(
                    f"{p.relative_to(repo)}: check {c.get('id', '?')}: "
                    f"unknown runner {runner!r}"
                )

    if errors > 0:
        return CheckResult("controls-have-checks", "fail", details)
    if n_controls == 0:
        return CheckResult(
            "controls-have-checks", "warn", ["no controls found under domains/"]
        )
    return CheckResult(
        "controls-have-checks",
        "pass",
        [f"{n_controls} control(s) declare runnable checks"],
    )
