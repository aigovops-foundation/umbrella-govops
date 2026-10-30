"""`verify` recomputes every digest and never passes an unsigned bundle.

Regression for the 22 Oct 2026 estate review finding: `verify` checked only
that bundle.sha256 *existed*, so a corrupted bundle — and an unsigned one —
passed.
"""
from __future__ import annotations

import io
import json
import shutil
import tarfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from conformance.cli import cli

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _run(*args: str) -> tuple[int, str]:
    r = CliRunner().invoke(cli, list(args))
    return r.exit_code, r.output


@pytest.fixture()
def keys(tmp_path: Path) -> tuple[Path, Path]:
    code, out = _run("keygen", "--out", str(tmp_path / "keys"))
    assert code == 0, out
    return tmp_path / "keys" / "signing.pem", tmp_path / "keys" / "signing.pub.pem"


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    shutil.copy(FIXTURES / "level-200-policy.yaml", r / "policy.yaml")
    return r


def _bundle(repo: Path, out: Path, key: Path | None = None) -> Path:
    args = ["bundle", str(repo), "--out", str(out)]
    if key is not None:
        args += ["--sign-key", str(key)]
    code, output = _run(*args)
    assert code == 0, output
    return out / "bundle.tar.gz"


def _rewrite_member(bp: Path, name: str, data: bytes) -> None:
    members: list[tuple[tarfile.TarInfo, bytes]] = []
    with tarfile.open(bp, "r:gz") as tf:
        for m in tf.getmembers():
            f = tf.extractfile(m)
            members.append((m, f.read() if f else b""))
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for m, content in members:
            if m.name == name:
                content = data
            m.size = len(content)
            tf.addfile(m, io.BytesIO(content))
    bp.write_bytes(buf.getvalue())


def test_signed_bundle_verifies(repo: Path, tmp_path: Path, keys) -> None:
    priv, pub = keys
    bp = _bundle(repo, tmp_path / "out", priv)
    code, out = _run("verify", str(bp), "--public-key", str(pub))
    assert code == 0, out
    assert "Ed25519 signature valid" in out
    assert "receipt signatures valid" in out


def test_unsigned_bundle_never_passes(repo: Path, tmp_path: Path) -> None:
    bp = _bundle(repo, tmp_path / "out")
    code, out = _run("verify", str(bp))
    assert code == 1
    assert "unsigned" in out


def test_unsigned_bundle_fails_even_with_public_key(repo: Path, tmp_path: Path, keys) -> None:
    _, pub = keys
    bp = _bundle(repo, tmp_path / "out")
    code, out = _run("verify", str(bp), "--public-key", str(pub))
    assert code == 1
    assert "unsigned" in out


def test_ed25519_bundle_without_public_key_fails(repo: Path, tmp_path: Path, keys) -> None:
    priv, _ = keys
    bp = _bundle(repo, tmp_path / "out", priv)
    code, out = _run("verify", str(bp))
    assert code == 1
    assert "--public-key" in out


def test_wrong_public_key_fails(repo: Path, tmp_path: Path, keys) -> None:
    priv, _ = keys
    _run("keygen", "--out", str(tmp_path / "other"))
    bp = _bundle(repo, tmp_path / "out", priv)
    code, out = _run("verify", str(bp), "--public-key", str(tmp_path / "other" / "signing.pub.pem"))
    assert code == 1
    assert "not by the key you supplied" in out


def test_corrupted_tarball_bytes_fail(repo: Path, tmp_path: Path, keys) -> None:
    priv, pub = keys
    bp = _bundle(repo, tmp_path / "out", priv)
    data = bytearray(bp.read_bytes())
    data[len(data) // 2] ^= 0xFF
    bp.write_bytes(bytes(data))
    code, out = _run("verify", str(bp), "--public-key", str(pub))
    assert code == 1
    assert "integrity" in out


def test_tampered_member_with_recomputed_outer_digest_fails(
    repo: Path, tmp_path: Path, keys
) -> None:
    """An attacker who edits receipts.ndjson and rewrites bundle.sha256 is
    still caught by SHA256SUMS (and the signature)."""
    import hashlib

    priv, pub = keys
    out = tmp_path / "out"
    bp = _bundle(repo, out, priv)
    _rewrite_member(bp, "receipts.ndjson", b'{"id":"forged"}\n')
    (out / "bundle.sha256").write_text(
        hashlib.sha256(bp.read_bytes()).hexdigest() + "  bundle.tar.gz\n"
    )
    code, output = _run("verify", str(bp), "--public-key", str(pub))
    assert code == 1
    assert "receipts.ndjson: sha256 mismatch" in output


def test_tampered_loose_receipts_copy_fails(repo: Path, tmp_path: Path, keys) -> None:
    """`lantern read out/receipts.ndjson` reads the loose copy, so it is covered too."""
    priv, pub = keys
    out = tmp_path / "out"
    bp = _bundle(repo, out, priv)
    p = out / "receipts.ndjson"
    p.write_text(p.read_text().replace('"decision":"hold"', '"decision":"allow"'))
    code, output = _run("verify", str(bp), "--public-key", str(pub))
    assert code == 1
    assert "does not match SHA256SUMS" in output


def test_missing_digest_file_fails(repo: Path, tmp_path: Path, keys) -> None:
    priv, pub = keys
    out = tmp_path / "out"
    bp = _bundle(repo, out, priv)
    (out / "bundle.sha256").unlink()
    code, output = _run("verify", str(bp), "--public-key", str(pub))
    assert code == 1
    assert "no bundle.sha256" in output


def test_bad_signature_fails(repo: Path, tmp_path: Path, keys) -> None:
    priv, pub = keys
    out = tmp_path / "out"
    bp = _bundle(repo, out, priv)
    sig_path = out / "bundle.tar.gz.sig.json"
    block = json.loads(sig_path.read_text())
    other = _bundle(repo, tmp_path / "out2", priv)  # same key, different bytes (new timestamp)
    other_block = json.loads((tmp_path / "out2" / "bundle.tar.gz.sig.json").read_text())
    if other.read_bytes() != bp.read_bytes():
        block["sig_b64"] = other_block["sig_b64"]
    else:  # pragma: no cover - same-second rebuild
        block["sig_b64"] = block["sig_b64"][::-1]
    sig_path.write_text(json.dumps(block))
    code, output = _run("verify", str(bp), "--public-key", str(pub))
    assert code == 1
    assert "does not verify" in output


def test_rebuild_removes_stale_signature(repo: Path, tmp_path: Path, keys) -> None:
    priv, _ = keys
    out = tmp_path / "out"
    _bundle(repo, out, priv)
    (out / "bundle.tar.gz.sig").write_text("old cosign sig")
    (out / "bundle.tar.gz.pem").write_text("old cert")
    _bundle(repo, out)
    assert not (out / "bundle.tar.gz.sig.json").exists()
    assert not (out / "bundle.tar.gz.sig").exists()
    assert not (out / "bundle.tar.gz.pem").exists()


def test_cosign_signature_without_cosign_fails(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "out"
    bp = _bundle(repo, out)
    (out / "bundle.tar.gz.sig").write_text("sig")
    (out / "bundle.tar.gz.pem").write_text("cert")
    monkeypatch.setattr("shutil.which", lambda _name: None)
    code, output = _run("verify", str(bp))
    assert code == 1
    assert "cosign is not installed" in output


def test_receipts_are_lantern_shaped_and_content_addressed(repo: Path, tmp_path: Path) -> None:
    out1, out2 = tmp_path / "a", tmp_path / "b"
    _bundle(repo, out1)
    rows1 = [json.loads(x) for x in (out1 / "receipts.ndjson").read_text().splitlines()]
    required = {"id", "ts_utc", "user", "vendor", "model", "version",
                "prompt_hash", "result_hash", "event_type", "environment"}
    assert all(required <= r.keys() for r in rows1)
    controls = [r for r in rows1 if r["event_type"] == "policy.control"]
    assert len(controls) == 3
    hold = next(r for r in controls if r["attributes"]["action"] == "commitment.make")
    assert hold["attributes"]["tier"] == "C3" and hold["attributes"]["decision"] == "hold"

    # weaken one rule (worksheet step 5) — exactly that control's id changes
    p = repo / "policy.yaml"
    p.write_text(
        p.read_text()
        .replace("tier: C3", "tier: C1", 1)
        .replace("decision: hold", "decision: allow", 1)
    )
    _bundle(repo, out2)
    rows2 = [json.loads(x) for x in (out2 / "receipts.ndjson").read_text().splitlines()]
    ids1 = {r["id"] for r in rows1 if r["event_type"] == "policy.control"}
    ids2 = {r["id"] for r in rows2 if r["event_type"] == "policy.control"}
    assert len(ids1 - ids2) == 1 and len(ids2 - ids1) == 1
