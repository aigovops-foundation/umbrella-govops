"""Tests for the conformance check suite."""
from __future__ import annotations

from pathlib import Path

import pytest

from conformance.checks import (
    check_controls_have_checks,
    check_crosswalk_resolved,
    check_schema_valid,
)

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "conformance" / "fixtures"


def test_pass_fixture_validates_schema() -> None:
    r = check_schema_valid(FIXTURES / "pass")
    assert r.status == "pass", r.details


def test_pass_fixture_resolves_crosswalk() -> None:
    r = check_crosswalk_resolved(FIXTURES / "pass")
    assert r.status == "pass", r.details


def test_pass_fixture_controls_have_checks() -> None:
    r = check_controls_have_checks(FIXTURES / "pass")
    assert r.status == "pass", r.details


def test_fail_fixture_crosswalk_unresolved() -> None:
    r = check_crosswalk_resolved(FIXTURES / "fail")
    assert r.status == "fail"
    assert any("FX-999" in d for d in r.details)


def test_fail_fixture_no_checks() -> None:
    r = check_controls_have_checks(FIXTURES / "fail")
    assert r.status == "fail"
    assert any("FX-002" in d or "no checks" in d.lower() for d in r.details)


def test_real_repo_schema_valid() -> None:
    """The actual repo's controls + crosswalk should pass schema validation."""
    r = check_schema_valid(REPO)
    # Allow warn on a fresh repo, but never fail
    assert r.status in ("pass", "warn"), r.details


def test_real_repo_crosswalk_resolves() -> None:
    r = check_crosswalk_resolved(REPO)
    assert r.status in ("pass", "warn"), r.details
