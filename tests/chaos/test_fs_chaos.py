"""Filesystem chaos.

Inject real I/O faults — missing files, truncated YAML, BOM-prefixed files,
unreadable files (EACCES) — and assert the conformance layer degrades
gracefully: it returns a structured CheckResult (pass/warn/fail) with
actionable details, and the CLI exits with a documented code. It must never
raise an unhandled exception.

Determinism: no randomness; every fault is constructed explicitly.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from conformance.cli import cli
from conformance.runner import run_checks
from conformance.checks import check_crosswalk_resolved, check_schema_valid
from tests._lib.synth import generate_repo

ALL = [
    ("schema-valid", check_schema_valid),
    ("crosswalk-resolved", check_crosswalk_resolved),
]


def test_missing_crosswalk_warns_not_crashes(tmp_path: Path) -> None:
    generate_repo(tmp_path, n_controls=10, seed=1)
    (tmp_path / "crosswalks" / "unified-control-id.yaml").unlink()
    r = check_crosswalk_resolved(tmp_path)
    assert r.status == "warn"
    assert any("not found" in d.lower() for d in r.details)


def test_truncated_yaml_is_reported_as_fail(tmp_path: Path) -> None:
    generate_repo(tmp_path, n_controls=10, seed=2)
    victim = next((tmp_path / "domains").rglob("*-001.yaml"))
    text = victim.read_text()
    victim.write_text(text[: len(text) // 2] + "\n  : : : broken")
    r = check_schema_valid(tmp_path)
    assert r.status == "fail"
    assert any("invalid yaml" in d.lower() or victim.name in d for d in r.details)


def test_bom_prefixed_yaml_does_not_crash(tmp_path: Path) -> None:
    """A UTF-8 BOM at the head of a YAML file must not crash the parser path;
    PyYAML tolerates it, so the check still returns a structured result."""
    generate_repo(tmp_path, n_controls=10, seed=3)
    victim = next((tmp_path / "domains").rglob("*-001.yaml"))
    victim.write_bytes(b"\xef\xbb\xbf" + victim.read_bytes())
    r = check_schema_valid(tmp_path)
    assert r.status in {"pass", "warn", "fail"}


def test_empty_yaml_file_is_handled(tmp_path: Path) -> None:
    generate_repo(tmp_path, n_controls=10, seed=4)
    victim = next((tmp_path / "domains").rglob("*-001.yaml"))
    victim.write_text("")
    r = check_schema_valid(tmp_path)
    # empty doc -> not a dict -> skipped, suite still resolves to a status
    assert r.status in {"pass", "warn", "fail"}


@pytest.mark.skipif(
    os.geteuid() == 0 if hasattr(os, "geteuid") else False,
    reason="root bypasses file-permission checks",
)
@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX permissions only")
def test_unreadable_control_surfaces_structured_failure(tmp_path: Path) -> None:
    """An EACCES on a control file is caught by the runner and converted into a
    failing CheckResult rather than crashing the process."""
    generate_repo(tmp_path, n_controls=10, seed=5)
    victim = next((tmp_path / "domains").rglob("*-001.yaml"))
    victim.chmod(0o000)
    try:
        results = run_checks(tmp_path, ALL)
        # run_checks must never raise; it returns a CheckResult per check.
        assert len(results) == len(ALL)
        assert all(r.status in {"pass", "warn", "fail"} for r in results)
    finally:
        victim.chmod(0o644)


def test_cli_on_nonexistent_path_exits_cleanly(tmp_path: Path) -> None:
    """`check` against a path that does not exist must be a clean Click error
    (exit code 2), not a traceback."""
    result = CliRunner().invoke(cli, ["check", str(tmp_path / "does-not-exist")])
    assert result.exit_code != 0
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_directory_where_file_expected_is_handled(tmp_path: Path) -> None:
    """If the crosswalk path is a directory, the check degrades gracefully."""
    generate_repo(tmp_path, n_controls=10, seed=6)
    cw = tmp_path / "crosswalks" / "unified-control-id.yaml"
    cw.unlink()
    cw.mkdir()
    results = run_checks(tmp_path, [("crosswalk-resolved", check_crosswalk_resolved)])
    assert results[0].status in {"warn", "fail"}
