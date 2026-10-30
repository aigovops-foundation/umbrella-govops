"""Hardening from the PR #20 review: embedded Beacon receipts, cosign identity,
decompression cap, key file mode, undeclared Beacon receipt files, the
evidence-signed check, and policy discovery under policies/ and catalog/."""
from __future__ import annotations

import json
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from conformance import beacon
from conformance import cli as cli_mod
from conformance.checks.evidence import check_evidence_signed
from conformance.checks.schema import check_schema_valid
from conformance.cli import cli

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
BEACON_BUNDLE = FIXTURES / "beacon-bundle-1.0.0"
BEACON_PUB = BEACON_BUNDLE / "public_keys" / "fe812c12f3ab4ce6.pem"


def _run(*args: str) -> tuple[int, str]:
    r = CliRunner().invoke(cli, list(args))
    return r.exit_code, r.output


@pytest.fixture()
def signed(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A repo + signed bundle that embeds Beacon's frozen 1.0.0 receipts."""
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy(FIXTURES / "level-200-policy.yaml", repo / "policy.yaml")
    _run("keygen", "--out", str(tmp_path / "keys"))
    out = tmp_path / "out"
    code, output = _run(
        "bundle", str(repo), "--out", str(out),
        "--sign-key", str(tmp_path / "keys" / "signing.pem"),
        "--beacon-bundle", str(BEACON_BUNDLE),
    )
    assert code == 0, output
    return out / "bundle.tar.gz", tmp_path / "keys" / "signing.pub.pem", repo


def test_embedded_beacon_receipts_require_verification(signed) -> None:
    bp, pub, _ = signed
    code, out = _run("verify", str(bp), "--public-key", str(pub))
    assert code == 2
    assert "embeds 2 Beacon receipt(s)" in out


def test_embedded_beacon_receipts_verify_natively_with_beacon_key(signed) -> None:
    bp, pub, _ = signed
    code, out = _run("verify", str(bp), "--public-key", str(pub),
                     "--beacon-public-key", str(BEACON_PUB))
    assert code == 0, out
    assert "2 embedded Beacon receipt signature(s) valid" in out


def test_embedded_beacon_receipts_wrong_key_fails(signed, tmp_path: Path) -> None:
    bp, pub, _ = signed
    _run("keygen", "--out", str(tmp_path / "other"))
    code, out = _run("verify", str(bp), "--public-key", str(pub),
                     "--beacon-public-key", str(tmp_path / "other" / "signing.pub.pem"))
    assert code == 2
    assert "do not verify" in out


def test_beacon_bundle_source_must_contain_embedded_receipts(
    signed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """beacon-verify passing on *some* source is not enough: the embedded
    receipts must be the ones in it."""
    bp, pub, _ = signed
    other = tmp_path / "other.ndjson"
    first = (BEACON_BUNDLE / "receipts" / "2026-05-13.ndjson").read_text().splitlines()[0]
    other.write_text(first + "\n")
    monkeypatch.setattr("shutil.which", lambda name: "/bin/true")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0))
    code, out = _run("verify", str(bp), "--public-key", str(pub), "--beacon-bundle", str(other))
    assert code == 2
    assert "not in the verified source" in out
    code, out = _run("verify", str(bp), "--public-key", str(pub),
                     "--beacon-bundle", str(BEACON_BUNDLE))
    assert code == 0, out


def test_cosign_identity_is_pinned_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy(FIXTURES / "level-200-policy.yaml", repo / "policy.yaml")
    out = tmp_path / "out"
    _run("bundle", str(repo), "--out", str(out))
    (out / "bundle.tar.gz.sig").write_text("sig")
    (out / "bundle.tar.gz.pem").write_text("cert")
    seen: list[list[str]] = []
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/cosign")

    def fake_run(cmd, check):  # noqa: ANN001
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    code, output = _run("verify", str(out / "bundle.tar.gz"))
    assert code == 0, output
    cmd = seen[0]
    assert ".*" not in cmd
    assert cmd[cmd.index("--certificate-identity-regexp") + 1] == cli_mod.DEFAULT_CERT_IDENTITY_REGEXP
    assert cmd[cmd.index("--certificate-oidc-issuer") + 1] == "https://token.actions.githubusercontent.com"


def test_oversized_bundle_is_refused(signed, monkeypatch: pytest.MonkeyPatch) -> None:
    bp, pub, _ = signed
    monkeypatch.setattr(cli_mod, "MAX_BUNDLE_BYTES", 2048)
    code, out = _run("verify", str(bp), "--public-key", str(pub))
    assert code == 1
    assert "refusing" in out


def test_keygen_private_key_is_0600(tmp_path: Path) -> None:
    code, _ = _run("keygen", "--out", str(tmp_path / "k"))
    assert code == 0
    mode = stat.S_IMODE((tmp_path / "k" / "signing.pem").stat().st_mode)
    assert mode == 0o600
    code, out = _run("keygen", "--out", str(tmp_path / "k"))
    assert code == 1 and "refusing to overwrite" in out


def test_undeclared_beacon_receipt_file_is_refused(tmp_path: Path) -> None:
    b = tmp_path / "beacon"
    shutil.copytree(BEACON_BUNDLE, b)
    shutil.copy(b / "receipts" / "2026-05-13.ndjson", b / "receipts" / "2026-05-14.ndjson")
    with pytest.raises(beacon.BeaconInputError, match="not listed in manifest"):
        beacon.load(b)


def test_evidence_signed_recognises_emitted_signatures(signed, tmp_path: Path) -> None:
    bp, _, repo = signed
    dest = repo / "evidence" / "bundles" / "1"
    shutil.copytree(bp.parent, dest)
    assert check_evidence_signed(repo).status == "pass"
    (dest / "bundle.tar.gz.sig.json").unlink()
    assert check_evidence_signed(repo).status == "fail"
    (dest / "bundle.tar.gz.sig").write_text("s")
    (dest / "bundle.tar.gz.pem").write_text("c")
    assert check_evidence_signed(repo).status == "pass"


def test_misspelled_policy_in_policies_dir_is_validated_not_skipped(tmp_path: Path) -> None:
    shutil.copy(FIXTURES / "level-200-policy.yaml", tmp_path / "policy.yaml")
    doc = yaml.safe_load((FIXTURES / "level-200-policy.yaml").read_text())
    doc["polcy"] = doc.pop("policy")
    doc["contorls"] = doc.pop("controls")
    (tmp_path / "policies").mkdir()
    (tmp_path / "policies" / "agent.yaml").write_text(yaml.safe_dump(doc))
    res = check_schema_valid(tmp_path)
    assert res.status == "fail"
    assert any("policies/agent.yaml" in d for d in res.details)


def test_kinded_documents_in_policies_dir_are_not_policies(tmp_path: Path) -> None:
    shutil.copy(FIXTURES / "level-200-policy.yaml", tmp_path / "policy.yaml")
    (tmp_path / "policies").mkdir()
    (tmp_path / "policies" / "orchestration.yaml").write_text(
        json.dumps({"apiVersion": "govops.aigovops.org/v1", "kind": "PolicyOrchestration"})
    )
    assert check_schema_valid(tmp_path).status == "pass"
