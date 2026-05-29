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
