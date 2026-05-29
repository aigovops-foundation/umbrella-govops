"""slsa-provenance-present: release artifacts have a SLSA v1.0 provenance attestation."""
from __future__ import annotations

import json
from pathlib import Path

from ..runner import CheckResult

SLSA_PREDICATE = "https://slsa.dev/provenance/v1"


def check_slsa_provenance_present(repo: Path) -> CheckResult:
    details: list[str] = []
    releases = repo / "evidence" / "releases"
    if not releases.exists():
        return CheckResult(
            "slsa-provenance-present",
            "warn",
            [
                "evidence/releases/ does not exist yet — no signed releases to check"
            ],
        )

    releases_list = [
        d
        for d in releases.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    if not releases_list:
        return CheckResult(
            "slsa-provenance-present", "warn", ["no release directories found"]
        )

    errors = 0
    for r in releases_list:
        prov = r / "provenance.json"
        if not prov.exists():
            errors += 1
            details.append(
                f"{r.relative_to(repo)}: missing provenance.json"
            )
            continue
        try:
            doc = json.loads(prov.read_text())
        except json.JSONDecodeError as exc:
            errors += 1
            details.append(
                f"{r.relative_to(repo)}/provenance.json: invalid JSON — {exc}"
            )
            continue
        if doc.get("predicateType") != SLSA_PREDICATE:
            errors += 1
            details.append(
                f"{r.relative_to(repo)}/provenance.json: predicateType "
                f"{doc.get('predicateType')!r} != {SLSA_PREDICATE!r}"
            )

    if errors > 0:
        return CheckResult("slsa-provenance-present", "fail", details)
    return CheckResult(
        "slsa-provenance-present",
        "pass",
        [f"{len(releases_list)} release(s) have SLSA v1 provenance"],
    )
