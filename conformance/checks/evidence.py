"""evidence-signed: each evidence bundle has a signature artifact.

A bundle directory counts as signed when it carries one of the signature
forms `umbrella-conformance bundle` / CI produce — ``bundle.tar.gz.sig.json``
(Ed25519, ``bundle --sign-key``) or ``bundle.tar.gz.sig`` +
``bundle.tar.gz.pem`` (cosign keyless) — or the legacy ``signature.json``.
Presence only: ``umbrella-conformance verify`` is what checks the signature.
"""
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
        signed = (
            (b / "bundle.tar.gz.sig.json").exists()
            or ((b / "bundle.tar.gz.sig").exists() and (b / "bundle.tar.gz.pem").exists())
            or (b / "signature.json").exists()
        )
        if not manifest.exists():
            errors += 1
            details.append(f"{b.relative_to(repo)}: missing manifest.json")
        if not signed:
            errors += 1
            details.append(
                f"{b.relative_to(repo)}: unsigned — no bundle.tar.gz.sig.json, "
                "bundle.tar.gz.sig + .pem, or signature.json "
                "(sign with `bundle --sign-key` or `cosign sign-blob`)"
            )

    if errors > 0:
        return CheckResult("evidence-signed", "fail", details)
    return CheckResult(
        "evidence-signed",
        "pass",
        [f"{len(bundles)} evidence bundle(s) have signatures"],
    )
