"""Check runner: applies the registered check functions to a repo."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


@dataclass
class CheckResult:
    name: str
    status: str  # "pass" | "warn" | "fail"
    details: list[str] = field(default_factory=list)


CheckFn = Callable[[Path], CheckResult]


def run_checks(repo: Path, checks: Iterable[tuple[str, CheckFn]]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for name, fn in checks:
        try:
            res = fn(repo)
            # Defensive: ensure name matches
            res.name = name
            results.append(res)
        except Exception as exc:  # pragma: no cover — defensive
            results.append(
                CheckResult(
                    name=name,
                    status="fail",
                    details=[f"check raised: {type(exc).__name__}: {exc}"],
                )
            )
    return results
