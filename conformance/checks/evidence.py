"""evidence-signed: each evidence bundle has a signature artifact."""
from __future__ import annotations

from pathlib import Path

from ..runner import CheckResult


def check_evidence_signed(repo: Path) -> CheckResult:
    details: list[str] = []
    bundles_dir = repo / "evidence" / "bundles"
    if not bundles_dir.exists():
        return CheckResult(
            "evidence-signed", "warn", ["evidence/bundles/ does not exist"]
        )

    bundles = [
        d
        for d in bundles_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    if not bundles:
        return CheckResult(
            "evidence-signed",
            "warn",
            ["no evidence bundles found yet — run `umbrella-conformance bundle`"],
        )

    errors = 0
    for b in bundles:
        manifest = b / "manifest.json"
        sig = b / "signature.json"
        if not manifest.exists():
            errors += 1
            details.append(f"{b.relative_to(repo)}: missing manifest.json")
        if not sig.exists():
            errors += 1
            details.append(
                f"{b.relative_to(repo)}: missing signature.json "
                "(sign with cosign or `umbrella-conformance verify`)"
            )

    if errors > 0:
        return CheckResult("evidence-signed", "fail", details)
    return CheckResult(
        "evidence-signed",
        "pass",
        [f"{len(bundles)} evidence bundle(s) have signatures"],
    )
