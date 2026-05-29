"""schema-valid: validate every YAML against its JSON Schema."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, ValidationError

from ..runner import CheckResult

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

# kind → schema file
KIND_TO_SCHEMA = {
    "Control": "control.schema.json",
    "Crosswalk": "crosswalk.schema.json",
    "EvidenceBundle": "evidence-bundle.schema.json",
    "GovernanceDomain": "domain.schema.json",
}


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


def check_schema_valid(repo: Path) -> CheckResult:
    details: list[str] = []
    errors = 0
    checked = 0
    yaml_paths: list[Path] = []
    for sub in ("domains", "crosswalks", "frameworks"):
        d = repo / sub
        if d.exists():
            yaml_paths.extend(p for p in d.rglob("*.yaml") if p.is_file())

    for p in yaml_paths:
        try:
            doc = yaml.safe_load(p.read_text())
        except yaml.YAMLError as exc:
            errors += 1
            details.append(f"{p.relative_to(repo)}: invalid YAML — {exc}")
            continue
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind")
        if kind not in KIND_TO_SCHEMA:
            continue
        try:
            schema = _load_schema(KIND_TO_SCHEMA[kind])
        except FileNotFoundError:
            details.append(
                f"{p.relative_to(repo)}: no schema for kind={kind} (skipped)"
            )
            continue
        validator = Draft202012Validator(schema)
        checked += 1
        for err in validator.iter_errors(doc):
            errors += 1
            details.append(
                f"{p.relative_to(repo)}: {_err_path(err)}: {err.message}"
            )

    if errors > 0:
        return CheckResult("schema-valid", "fail", details)
    if checked == 0:
        return CheckResult(
            "schema-valid", "warn", ["no YAML files matched a known kind"]
        )
    return CheckResult(
        "schema-valid",
        "pass",
        [f"{checked} document(s) validated against JSON Schema"],
    )


def _err_path(err: ValidationError) -> str:
    return "$" + "".join(f".{p}" if isinstance(p, str) else f"[{p}]" for p in err.absolute_path)
