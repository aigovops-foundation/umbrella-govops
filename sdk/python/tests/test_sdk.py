"""Smoke tests for the umbrella_sdk Python package."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from umbrella_sdk import umbrella, journeys

REPO = Path(__file__).resolve().parents[3]


def test_umbrella_surface() -> None:
    u = umbrella(REPO)
    assert u.controls is not None
    assert u.crosswalk is not None
    assert u.evidence is not None
    assert u.journey is not None
    assert u.version == "0.1.0-alpha.1"


def test_controls_load() -> None:
    u = umbrella(REPO)
    all_ = u.controls.load().all()
    assert len(all_) >= 1
    dg = u.controls.by_id("DG-002")
    assert dg is not None
    assert dg.ucid == "UCID-DATA-BIAS-001"


def test_crosswalk_resolve() -> None:
    u = umbrella(REPO)
    u.crosswalk.load()
    ucid = u.crosswalk.resolve("UCID-DATA-BIAS-001")
    assert ucid is not None
    assert "DG-002" in ucid.implementing_controls


def test_crosswalk_equivalents() -> None:
    u = umbrella(REPO)
    u.crosswalk.load()
    matches = u.crosswalk.equivalents("nist_ai_rmf", "MEASURE-2.11")
    assert len(matches) >= 1
    assert matches[0].id == "UCID-DATA-BIAS-001"


def test_journeys_list() -> None:
    all_ = journeys.list()
    assert len(all_) == 3
    keys = sorted(j.key for j in all_)
    assert keys == ["at-yes", "return-to-yes", "to-yes"]


def test_journey_get_to_yes() -> None:
    j = journeys.get("to-yes")
    assert len(j.steps) == 4


def test_evidence_digest_stable() -> None:
    u = umbrella(REPO)
    b = u.evidence.build(repo="umbrella-govops", checks=[{"name": "schema-valid", "status": "pass"}])
    d1 = u.evidence.digest(b)
    d2 = u.evidence.digest(b)
    assert d1 == d2
    assert re.match(r"^[a-f0-9]{64}$", d1)
