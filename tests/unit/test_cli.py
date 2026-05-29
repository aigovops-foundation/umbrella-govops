"""CLI unit tests via click.testing.CliRunner."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from conformance.cli import cli


def test_version() -> None:
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "umbrella-conformance" in result.output


def test_check_real_repo_passes(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    result = CliRunner().invoke(cli, ["check", str(repo)])
    assert result.exit_code == 0, result.output


def test_check_json_format(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    result = CliRunner().invoke(cli, ["check", str(repo), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    names = {r["name"] for r in data}
    assert "schema-valid" in names
    assert "crosswalk-resolved" in names


def test_init_scaffolds_repo(tmp_path: Path) -> None:
    target = tmp_path / "newrepo"
    result = CliRunner().invoke(cli, ["init", str(target)])
    assert result.exit_code == 0
    assert (target / "domains").is_dir()
    assert (target / "crosswalks").is_dir()
    assert (target / "evidence" / "bundles").is_dir()
    assert (target / "README.md").exists()


def test_bundle_creates_tarball(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    out = tmp_path / "out"
    result = CliRunner().invoke(cli, ["bundle", str(repo), "--out", str(out)])
    assert result.exit_code == 0
    assert (out / "bundle.tar.gz").exists()
    assert (out / "manifest.json").exists()
    assert (out / "bundle.sha256").exists()
    digest = (out / "bundle.sha256").read_text().split()[0]
    assert len(digest) == 64


def test_bundle_embeds_dsse_envelope(tmp_path: Path) -> None:
    """Bundle must emit an in-toto Statement v1 / DSSE envelope and conform to
    the EvidenceBundle schema."""
    import base64
    import jsonschema

    repo = Path(__file__).resolve().parents[2]
    out = tmp_path / "out"
    result = CliRunner().invoke(cli, ["bundle", str(repo), "--out", str(out)])
    assert result.exit_code == 0, result.output

    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["apiVersion"] == "govops.aigovops.org/v1"
    assert manifest["kind"] == "EvidenceBundle"
    assert isinstance(manifest["checks"], list)
    assert "receipts" in manifest  # NEW — added in repositioning work
    assert isinstance(manifest["receipts"], list)

    # Outer envelope sanity
    envelope = json.loads((out / "bundle.intoto.json").read_text())
    assert envelope["payloadType"] == "application/vnd.in-toto+json"
    payload = json.loads(base64.b64decode(envelope["payload"]).decode())
    assert payload["_type"] == "https://in-toto.io/Statement/v1"
    assert (
        payload["predicateType"]
        == "https://aigovops.org/attestations/govops-evidence/v1"
    )
    assert payload["predicate"] == manifest
    assert payload["subject"][0]["digest"]["sha256"]

    # Schema conformance
    schema = json.loads(
        (repo / "conformance" / "schemas" / "evidence-bundle.schema.json").read_text()
    )
    jsonschema.validate(instance=manifest, schema=schema)


def test_bundle_embeds_beacon_receipts(tmp_path: Path) -> None:
    """With --beacon-bundle, receipts[] is populated and evidence-signed gets
    its evidence_refs[] filled in."""
    repo = Path(__file__).resolve().parents[2]
    # Fabricate a foundation-shaped receipt the loader will accept verbatim.
    receipts_path = tmp_path / "receipts.jsonl"
    receipts_path.write_text(
        json.dumps(
            {
                "seq": 1,
                "timestamp_utc": "2026-05-29T00:00:00Z",
                "action": "test",
                "prev_entry_sha256": "GENESIS",
                "entry_sha256": "a" * 64,
                "signature_ed25519": "sig",
                "key_fingerprint": "fp",
            }
        )
        + "\n"
    )
    out = tmp_path / "out"
    result = CliRunner().invoke(
        cli,
        [
            "bundle",
            str(repo),
            "--out",
            str(out),
            "--beacon-bundle",
            str(receipts_path),
            "--commit-sha",
            "deadbeef1234567",
        ],
    )
    assert result.exit_code == 0, result.output
    manifest = json.loads((out / "manifest.json").read_text())
    assert len(manifest["receipts"]) == 1
    assert manifest["receipts"][0]["format"] == "foundation"
    assert manifest["receipts"][0]["id"] == "a" * 64
    assert manifest["metadata"]["commit_sha"] == "deadbeef1234567"
    refs = next(
        c["evidence_refs"] for c in manifest["checks"] if c["name"] == "evidence-signed"
    )
    assert refs == ["a" * 64]


def test_check_filtered_by_name() -> None:
    repo = Path(__file__).resolve().parents[2]
    result = CliRunner().invoke(
        cli,
        ["check", str(repo), "--check", "schema-valid", "--format", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["name"] == "schema-valid"
