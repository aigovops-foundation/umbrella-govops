"""Round-trip tests proving the JSON Schemas reject obvious bad inputs."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMAS = Path(__file__).resolve().parents[2] / "conformance" / "schemas"


def load(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text())


def test_control_schema_rejects_missing_metadata() -> None:
    v = Draft202012Validator(load("control.schema.json"))
    errors = list(v.iter_errors({"apiVersion": "govops.aigovops.org/v1", "kind": "Control"}))
    assert any("metadata" in str(e.message) for e in errors)


def test_control_schema_rejects_bad_id() -> None:
    v = Draft202012Validator(load("control.schema.json"))
    doc = {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "Control",
        "metadata": {
            "id": "lowercase-001",
            "ucid": "UCID-X-001",
            "name": "x",
            "owner": "@x",
            "severity": "low",
            "status": "draft",
        },
        "checks": [{"id": "x.C1", "name": "x", "runner": "pytest"}],
    }
    errors = list(v.iter_errors(doc))
    # The schema must reject the lowercase id via pattern OR enum
    assert any(
        ("pattern" in str(e.message).lower())
        or ("does not match" in str(e.message).lower())
        or (e.validator == "pattern")
        for e in errors
    ), f"Expected pattern rejection, got: {[str(e.message) for e in errors]}"


def test_control_schema_rejects_empty_checks() -> None:
    v = Draft202012Validator(load("control.schema.json"))
    doc = {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "Control",
        "metadata": {
            "id": "XX-001",
            "ucid": "UCID-X-001",
            "name": "x",
            "owner": "@x",
            "severity": "low",
            "status": "draft",
        },
        "checks": [],
    }
    errors = list(v.iter_errors(doc))
    assert errors  # minItems: 1


def test_control_schema_rejects_bad_runner() -> None:
    v = Draft202012Validator(load("control.schema.json"))
    doc = {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "Control",
        "metadata": {
            "id": "XX-001",
            "ucid": "UCID-X-001",
            "name": "x",
            "owner": "@x",
            "severity": "low",
            "status": "draft",
        },
        "checks": [{"id": "x.C1", "name": "x", "runner": "javascript"}],
    }
    errors = list(v.iter_errors(doc))
    assert errors


def test_crosswalk_schema_rejects_bad_ucid_pattern() -> None:
    v = Draft202012Validator(load("crosswalk.schema.json"))
    doc = {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "Crosswalk",
        "metadata": {"name": "x"},
        "ucids": [
            {"id": "not-a-ucid", "title": "x", "implementing_controls": ["XX-001"]}
        ],
    }
    errors = list(v.iter_errors(doc))
    assert errors


@pytest.mark.parametrize(
    "schema_file", ["control.schema.json", "crosswalk.schema.json", "domain.schema.json", "evidence-bundle.schema.json"]
)
def test_all_schemas_are_valid_drafts(schema_file: str) -> None:
    schema = load(schema_file)
    # Will raise if schema itself is malformed
    Draft202012Validator.check_schema(schema)
