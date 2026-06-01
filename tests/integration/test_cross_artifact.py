"""E2E cross-artifact integrity tests.

Where unit tests check a single artifact in isolation, these exercise the
*relationships* between artifacts the way the conformance pipeline does:

  * Every UCID referenced anywhere (controls + crosswalk) resolves with no
    dangling pointers in either direction.
  * Every implementing_controls id in the registry has a real control file.
  * Round-trip: load the registry -> validate against schema -> re-serialize
    -> re-load -> assert structural equality.
  * The conformance CLI run against the shipped pass/fail fixtures produces
    the documented exit codes and a schema-conformant JSON report.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from jsonschema import Draft202012Validator

from conformance.cli import cli
from tests._lib.ucid import UCID_RE

REPO = Path(__file__).resolve().parents[2]
CROSSWALK = REPO / "crosswalks" / "unified-control-id.yaml"
SCHEMAS = REPO / "conformance" / "schemas"
FIXTURES = REPO / "conformance" / "fixtures"


def _registry() -> dict:
    return yaml.safe_load(CROSSWALK.read_text()) or {}


def _control_index() -> dict[str, Path]:
    index: dict[str, Path] = {}
    for p in (REPO / "domains").rglob("*.yaml"):
        try:
            doc = yaml.safe_load(p.read_text())
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict) and doc.get("kind") == "Control":
            cid = (doc.get("metadata") or {}).get("id")
            if cid:
                index[cid] = p
    return index


# ── Bidirectional reference integrity ────────────────────────────────────────

def test_no_dangling_implementing_controls() -> None:
    """Every implementing control named by the registry has a control file."""
    controls = _control_index()
    dangling: list[str] = []
    for u in _registry().get("ucids", []):
        if not isinstance(u, dict):
            continue
        for impl in u.get("implementing_controls", []) or []:
            if impl not in controls:
                dangling.append(f"{u.get('id')} -> {impl}")
    assert not dangling, f"implementing_controls with no file: {dangling}"


def test_planned_controls_are_marked_not_implemented() -> None:
    """`planned_controls` must NOT also have a control file — that would mean
    the entry is mislabelled (it is implemented, not planned)."""
    controls = _control_index()
    misfiled: list[str] = []
    for u in _registry().get("ucids", []):
        if not isinstance(u, dict):
            continue
        for planned in u.get("planned_controls", []) or []:
            if planned in controls:
                misfiled.append(f"{u.get('id')} lists {planned} as planned but a file exists")
    assert not misfiled, misfiled


def test_every_control_ucid_is_well_formed_and_known() -> None:
    registry_ids = {u["id"] for u in _registry().get("ucids", []) if isinstance(u, dict) and "id" in u}
    problems: list[str] = []
    for cid, p in _control_index().items():
        doc = yaml.safe_load(p.read_text())
        ucid = (doc.get("metadata") or {}).get("ucid")
        if not ucid:
            continue
        if not UCID_RE.match(ucid):
            problems.append(f"{cid}: malformed ucid {ucid!r}")
        elif ucid not in registry_ids:
            problems.append(f"{cid}: ucid {ucid!r} not in registry")
    assert not problems, problems


# ── Round-trip: load -> validate -> serialize -> reload -> equal ─────────────

def test_registry_round_trip_structural_equality() -> None:
    schema = json.loads((SCHEMAS / "crosswalk.schema.json").read_text())
    validator = Draft202012Validator(schema)

    original = _registry()
    errors = list(validator.iter_errors(original))
    assert not errors, [e.message for e in errors]

    # serialize -> reload
    dumped = yaml.safe_dump(original, sort_keys=True)
    reloaded = yaml.safe_load(dumped)

    # re-validate after the round trip
    assert not list(validator.iter_errors(reloaded))
    # structural equality (order-independent because dicts compare by content)
    assert reloaded == original


@pytest.mark.parametrize(
    "control_path", sorted((REPO / "domains").rglob("*.yaml")), ids=lambda p: p.name
)
def test_each_yaml_round_trips(control_path: Path) -> None:
    doc = yaml.safe_load(control_path.read_text())
    if not isinstance(doc, dict):
        pytest.skip("not a mapping document")
    reloaded = yaml.safe_load(yaml.safe_dump(doc, sort_keys=True))
    assert reloaded == doc


# ── CLI against the shipped fixtures (documented exit codes) ─────────────────

def test_cli_passes_on_pass_fixture() -> None:
    result = CliRunner().invoke(cli, ["check", str(FIXTURES / "pass"), "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert {"schema-valid", "crosswalk-resolved", "controls-have-checks"} <= {r["name"] for r in data}


def test_cli_fails_on_fail_fixture() -> None:
    result = CliRunner().invoke(cli, ["check", str(FIXTURES / "fail")])
    assert result.exit_code == 1, result.output


def test_cli_json_report_conforms_to_documented_shape() -> None:
    result = CliRunner().invoke(cli, ["check", str(REPO), "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert isinstance(data, list)
    for entry in data:
        assert set(entry) >= {"name", "status", "details"}
        assert entry["status"] in {"pass", "warn", "fail"}
        assert isinstance(entry["details"], list)
