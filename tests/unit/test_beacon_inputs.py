"""`bundle --beacon-bundle` reads what Beacon actually writes.

The fixture tests/fixtures/beacon-bundle-1.0.0 is a verbatim copy of Beacon's
frozen schema 1.0.0 audit bundle (aigovops-beacon/tests/fixtures/
bundle-schema-1.0.0): manifest.json, manifest.sha256, receipts/*.ndjson,
public_keys/. Before this, a .ndjson file was parsed as a single JSON document
and a bundle directory was globbed for *.json — manifest.json became a
"receipt" — and either failure was downgraded to a warning.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from conformance import beacon
from conformance.cli import cli

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
BEACON_BUNDLE = FIXTURES / "beacon-bundle-1.0.0"
RECEIPTS = BEACON_BUNDLE / "receipts" / "2026-05-13.ndjson"


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    shutil.copy(FIXTURES / "level-200-policy.yaml", r / "policy.yaml")
    return r


def _bundle(repo: Path, out: Path, source: Path) -> tuple[int, str]:
    r = CliRunner().invoke(
        cli, ["bundle", str(repo), "--out", str(out), "--beacon-bundle", str(source)]
    )
    return r.exit_code, r.output


def test_beacon_bundle_directory_is_read(repo: Path, tmp_path: Path) -> None:
    code, out = _bundle(repo, tmp_path / "out", BEACON_BUNDLE)
    assert code == 0, out
    assert "(beacon-bundle)" in out
    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text())
    ids = [r["id"] for r in manifest["receipts"]]
    assert ids == ["01HXYZ8K3F2N5Q1R7S9V3W4Y6B", "01HXYZ8K3F2N5Q1R7S9V3W4Y6C"]
    assert all(r["format"] == "runtime" for r in manifest["receipts"])
    src = manifest["metadata"]["beacon_source"]
    assert src["kind"] == "beacon-bundle"
    assert src["public_key_fingerprints"] == ["fe812c12f3ab4ce6"]
    # Beacon receipts are carried verbatim into receipts.ndjson for Lantern
    rows = [json.loads(x) for x in (tmp_path / "out" / "receipts.ndjson").read_text().splitlines()]
    gate = [r for r in rows if r["event_type"] == "gate_decision"]
    assert len(gate) == 1 and gate[0]["signature"]["alg"] == "Ed25519"


def test_beacon_ndjson_file_is_read(repo: Path, tmp_path: Path) -> None:
    code, out = _bundle(repo, tmp_path / "out", RECEIPTS)
    assert code == 0, out
    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text())
    assert len(manifest["receipts"]) == 2
    assert manifest["receipts"][0]["payload"] == json.loads(RECEIPTS.read_text().splitlines()[0])


def test_tampered_beacon_manifest_is_refused(repo: Path, tmp_path: Path) -> None:
    b = tmp_path / "beacon"
    shutil.copytree(BEACON_BUNDLE, b)
    m = b / "manifest.json"
    m.write_text(m.read_text().replace('"generated_by": "frozen-fixture"', '"generated_by": "x"'))
    code, out = _bundle(repo, tmp_path / "out", b)
    assert code == 2
    assert "manifest.sha256 does not match" in out
    assert not (tmp_path / "out" / "bundle.tar.gz").exists()


def test_dropped_receipt_is_refused(tmp_path: Path) -> None:
    b = tmp_path / "beacon"
    shutil.copytree(BEACON_BUNDLE, b)
    f = b / "receipts" / "2026-05-13.ndjson"
    f.write_text(f.read_text().splitlines()[0] + "\n")
    with pytest.raises(beacon.BeaconInputError, match="manifest declares 2"):
        beacon.load(b)


def test_dangling_gate_decision_row_is_refused(tmp_path: Path) -> None:
    b = tmp_path / "beacon"
    shutil.copytree(BEACON_BUNDLE, b)
    (b / "gate_decisions.json").write_text(
        json.dumps([{"id": "g1", "receipt_id": "01HXYZ8K3F2N5Q1R7S9V3W4Y6C"},
                    {"id": "g2", "receipt_id": "NOT-IN-BUNDLE"}])
    )
    with pytest.raises(beacon.BeaconInputError, match="NOT-IN-BUNDLE"):
        beacon.load(b)


def test_gate_decision_rows_counted(tmp_path: Path) -> None:
    b = tmp_path / "beacon"
    shutil.copytree(BEACON_BUNDLE, b)
    (b / "gate_decisions.json").write_text(
        json.dumps([{"id": "g1", "receipt_id": "01HXYZ8K3F2N5Q1R7S9V3W4Y6C"}])
    )
    assert beacon.load(b).info["gate_decisions"] == 1


def test_malformed_ndjson_is_an_error_not_a_warning(repo: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad.ndjson"
    bad.write_text('{"id": "a"}\nnot json\n')
    code, out = _bundle(repo, tmp_path / "out", bad)
    assert code == 2
    assert "line 2" in out


def test_duplicate_receipt_ids_refused(tmp_path: Path) -> None:
    f = tmp_path / "dupe.ndjson"
    line = RECEIPTS.read_text().splitlines()[0]
    f.write_text(line + "\n" + line + "\n")
    with pytest.raises(beacon.BeaconInputError, match="duplicate"):
        beacon.load(f)
