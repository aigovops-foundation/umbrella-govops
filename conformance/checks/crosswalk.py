"""crosswalk-resolved: every UCID in controls exists in the crosswalk, and
every implementing_controls ID resolves to a real control file."""
from __future__ import annotations

from pathlib import Path

import yaml

from ..runner import CheckResult


def check_crosswalk_resolved(repo: Path) -> CheckResult:
    details: list[str] = []
    crosswalk_path = repo / "crosswalks" / "unified-control-id.yaml"
    if not crosswalk_path.exists():
        return CheckResult(
            "crosswalk-resolved", "warn", ["crosswalks/unified-control-id.yaml not found"]
        )

    crosswalk = yaml.safe_load(crosswalk_path.read_text()) or {}
    ucids = crosswalk.get("ucids", [])
    ucid_index = {u["id"]: u for u in ucids if isinstance(u, dict) and "id" in u}

    # Collect all control files
    control_files = {}
    for p in (repo / "domains").rglob("*.yaml"):
        try:
            doc = yaml.safe_load(p.read_text())
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict) and doc.get("kind") == "Control":
            cid = (doc.get("metadata") or {}).get("id")
            if cid:
                control_files[cid] = (p, doc)

    errors = 0

    # Every control's UCID must exist in the crosswalk
    for cid, (p, doc) in control_files.items():
        ucid = (doc.get("metadata") or {}).get("ucid")
        if ucid and ucid not in ucid_index:
            errors += 1
            details.append(
                f"{p.relative_to(repo)}: ucid {ucid!r} not found in crosswalk"
            )

    # Every implementing_controls ID must resolve to a real control file
    for u in ucids:
        if not isinstance(u, dict):
            continue
        for impl in u.get("implementing_controls", []) or []:
            if impl not in control_files:
                errors += 1
                details.append(
                    f"crosswalk ucid {u.get('id')}: implementing control {impl!r} has no file"
                )

    if errors > 0:
        return CheckResult("crosswalk-resolved", "fail", details)
    return CheckResult(
        "crosswalk-resolved",
        "pass",
        [
            f"{len(ucid_index)} UCID(s) and {len(control_files)} control(s) cross-resolve"
        ],
    )
