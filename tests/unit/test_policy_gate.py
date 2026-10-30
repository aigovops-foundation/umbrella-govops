"""`check` validates agent gate policies and fails when there is nothing to validate.

Regression for the 22 Oct 2026 estate review finding "check validates
nothing": before this, `umbrella-conformance check .` on a directory holding
only a policy.yaml — or a broken one — warned six times and exited 0.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from conformance.checks.schema import check_schema_valid, policy_errors
from conformance.cli import cli

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
LEVEL_200 = FIXTURES / "level-200-policy.yaml"


def _policy() -> dict:
    return yaml.safe_load(LEVEL_200.read_text())


def _write(tmp_path: Path, doc: object, name: str = "policy.yaml") -> Path:
    (tmp_path / name).write_text(yaml.safe_dump(doc, sort_keys=False))
    return tmp_path


def _check(path: Path) -> tuple[int, str]:
    r = CliRunner().invoke(cli, ["check", str(path)])
    return r.exit_code, r.output


def test_level_200_template_passes(tmp_path: Path) -> None:
    shutil.copy(LEVEL_200, tmp_path / "policy.yaml")
    code, out = _check(tmp_path)
    assert code == 0, out
    assert "1 agent policy file(s)" in out


def test_empty_directory_fails_nothing_to_validate(tmp_path: Path) -> None:
    code, out = _check(tmp_path)
    assert code == 1
    assert "nothing to validate" in out


def test_unparseable_policy_fails(tmp_path: Path) -> None:
    (tmp_path / "policy.yaml").write_text("controls: [\n  - action: x\n  bad")
    code, out = _check(tmp_path)
    assert code == 1
    assert "invalid YAML" in out


def test_misspelled_top_level_key_still_validated(tmp_path: Path) -> None:
    doc = _policy()
    doc["polcy"] = doc.pop("policy")
    code, out = _check(_write(tmp_path, doc))
    assert code == 1
    assert "'policy' is a required property" in out


@pytest.mark.parametrize(
    ("mutate", "expect"),
    [
        (lambda d: d.pop("default"), "'default' is a required property"),
        (lambda d: d.__setitem__("default", "allow"), "'deny' was expected"),
        (lambda d: d["controls"][0].pop("approver_role"), "'approver_role' is a required property"),
        (lambda d: d["controls"][2].pop("reason"), "'reason' is a required property"),
        (lambda d: d["controls"][0].__setitem__("tier", "C9"), "is not one of"),
        (lambda d: d["controls"][0].__setitem__("decision", "maybe"), "is not one of"),
        (lambda d: d["controls"][0].__setitem__("decision", "allow"), "is not one of ['hold', 'deny']"),
        (lambda d: d["controls"][2].__setitem__("decision", "hold"), "'deny' was expected"),
        (lambda d: d["controls"][0].__setitem__("aprover_role", "x"), "Additional properties"),
        (lambda d: d.__setitem__("controls", []), "should be non-empty"),
        (lambda d: d["controls"].append(dict(d["controls"][1])), "declared more than once"),
        (lambda d: d.__setitem__("stop_conditions", ["on_a_whim"]), "is not one of"),
        (lambda d: d["controls"][0]["constraints"].__setitem__("expiry", "tomorrow"), "does not match"),
    ],
)
def test_invalid_policy_exits_non_zero(tmp_path: Path, mutate, expect: str) -> None:
    doc = _policy()
    mutate(doc)
    code, out = _check(_write(tmp_path, doc))
    assert code == 1, out
    assert expect in out


def test_weakening_c3_hold_to_c1_allow_is_valid(tmp_path: Path) -> None:
    """Worksheet step 5 changes `C3 hold` to `C1 allow`; that must still pass check."""
    doc = _policy()
    doc["controls"][0]["tier"] = "C1"
    doc["controls"][0]["decision"] = "allow"
    assert policy_errors(doc) == []


def test_policy_in_catalog_and_policies_dirs(tmp_path: Path) -> None:
    (tmp_path / "catalog" / "my-system").mkdir(parents=True)
    shutil.copy(LEVEL_200, tmp_path / "catalog" / "my-system" / "agent.policy.yaml")
    res = check_schema_valid(tmp_path)
    assert res.status == "pass", res.details
    (tmp_path / "policies").mkdir()
    bad = _policy()
    bad["default"] = "allow"
    _write(tmp_path / "policies", bad, "other.yaml")
    res = check_schema_valid(tmp_path)
    assert res.status == "fail"
    assert any("policies/other.yaml" in d for d in res.details)


def test_bundle_refuses_invalid_policy(tmp_path: Path) -> None:
    doc = _policy()
    doc["default"] = "allow"
    _write(tmp_path, doc)
    r = CliRunner().invoke(cli, ["bundle", str(tmp_path), "--out", str(tmp_path / "out")])
    assert r.exit_code == 1
    assert "refusing to bundle" in r.output
    assert not (tmp_path / "out" / "bundle.tar.gz").exists()
