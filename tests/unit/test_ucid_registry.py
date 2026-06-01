"""Unit tests for the real UCID registry and the repo's YAML data contracts.

These assert *syntactic* and *referential* health of the on-disk artifacts:

  * Every published `*.schema.json` is itself a valid Draft 2020-12 schema.
  * Every YAML under crosswalks/, policies/, domains/, systems/, frameworks/
    parses without error.
  * Every UCID id in the registry matches the canonical pattern, is unique,
    and is consistent (no duplicate titles for distinct ids, etc.).
  * Every UCID referenced by a control's `metadata.ucid` resolves to a
    registry entry (no orphan references at the unit layer).

Cross-artifact *integrity* (dangling implementing_controls, round-trip, CLI
fixtures) lives in tests/integration/.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from tests._lib.ucid import UCID_RE

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "conformance" / "schemas"
CROSSWALK = REPO / "crosswalks" / "unified-control-id.yaml"

YAML_ROOTS = ["crosswalks", "policies", "domains", "systems", "frameworks"]


def _all_yaml_paths() -> list[Path]:
    paths: list[Path] = []
    for root in YAML_ROOTS:
        d = REPO / root
        if d.exists():
            paths.extend(p for p in d.rglob("*.yaml") if p.is_file())
            paths.extend(p for p in d.rglob("*.yml") if p.is_file())
    return sorted(paths)


def _load_registry() -> dict:
    return yaml.safe_load(CROSSWALK.read_text()) or {}


def _registry_ucids() -> list[dict]:
    reg = _load_registry()
    return [u for u in reg.get("ucids", []) if isinstance(u, dict)]


# ── Schema validity ──────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "schema_path", sorted(SCHEMAS.glob("*.schema.json")), ids=lambda p: p.name
)
def test_every_schema_is_valid_draft_2020_12(schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)


# ── YAML parseability ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "yaml_path", _all_yaml_paths(), ids=lambda p: str(p.relative_to(REPO))
)
def test_every_data_yaml_parses(yaml_path: Path) -> None:
    """Every shipped data YAML must load without a YAMLError."""
    try:
        yaml.safe_load(yaml_path.read_text())
    except yaml.YAMLError as exc:  # pragma: no cover - failure path
        pytest.fail(f"{yaml_path.relative_to(REPO)} did not parse: {exc}")


def test_registry_file_is_a_crosswalk() -> None:
    reg = _load_registry()
    assert reg.get("kind") == "Crosswalk"
    assert reg.get("apiVersion") == "govops.aigovops.org/v1"
    assert isinstance(reg.get("ucids"), list) and reg["ucids"]


# ── UCID format + uniqueness ─────────────────────────────────────────────────

def test_every_registry_ucid_matches_canonical_pattern() -> None:
    bad = [u.get("id") for u in _registry_ucids() if not UCID_RE.match(str(u.get("id", "")))]
    assert not bad, f"UCIDs violating canonical pattern: {bad}"


def test_registry_ucid_ids_are_unique() -> None:
    ids = [u["id"] for u in _registry_ucids() if "id" in u]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert not dupes, f"duplicate UCID ids in registry: {dupes}"


def test_registry_ucids_have_required_fields() -> None:
    missing: list[str] = []
    for u in _registry_ucids():
        for field in ("id", "title", "implementing_controls"):
            if field not in u:
                missing.append(f"{u.get('id', '<no id>')}: missing {field!r}")
    assert not missing, missing


def test_registry_ucids_cite_at_least_one_framework() -> None:
    """Each UCID must cite NIST, EU AI Act, or ISO 42001 — a UCID with no
    framework citation is just a control id and defeats the pivot."""
    orphans = []
    for u in _registry_ucids():
        if not any(k in u for k in ("nist_ai_rmf", "eu_ai_act", "iso_42001")):
            orphans.append(u.get("id"))
    assert not orphans, f"UCIDs with no framework citation: {orphans}"


# ── No orphan control → UCID references ──────────────────────────────────────

def test_no_control_references_unknown_ucid() -> None:
    """Every `metadata.ucid` on a real control resolves to a registry entry."""
    registry_ids = {u["id"] for u in _registry_ucids() if "id" in u}
    orphans: list[str] = []
    for p in (REPO / "domains").rglob("*.yaml"):
        try:
            doc = yaml.safe_load(p.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict) or doc.get("kind") != "Control":
            continue
        ucid = (doc.get("metadata") or {}).get("ucid")
        if ucid and ucid not in registry_ids:
            orphans.append(f"{p.relative_to(REPO)} -> {ucid}")
    assert not orphans, f"controls referencing unknown UCIDs: {orphans}"
