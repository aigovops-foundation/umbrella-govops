"""Click-based CLI entrypoint for umbrella-conformance."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import __version__
from .checks import (
    check_controls_have_checks,
    check_crosswalk_resolved,
    check_evidence_signed,
    check_overt_predicate_valid,
    check_schema_valid,
    check_slsa_provenance_present,
)
from .runner import CheckResult, run_checks

ALL_CHECKS = [
    ("schema-valid", check_schema_valid),
    ("crosswalk-resolved", check_crosswalk_resolved),
    ("controls-have-checks", check_controls_have_checks),
    ("evidence-signed", check_evidence_signed),
    ("slsa-provenance-present", check_slsa_provenance_present),
    ("overt-predicate-valid", check_overt_predicate_valid),
]


@click.group()
@click.version_option(__version__, prog_name="umbrella-conformance")
def cli() -> None:
    """Conformance CLI for Umbrella-GovOps repositories."""


@cli.command()
@click.argument("path", type=click.Path(file_okay=False), default=".")
def init(path: str) -> None:
    """Scaffold a new Umbrella-GovOps repository at PATH."""
    target = Path(path).resolve()
    target.mkdir(parents=True, exist_ok=True)
    (target / "domains").mkdir(exist_ok=True)
    (target / "crosswalks").mkdir(exist_ok=True)
    (target / "evidence" / "bundles").mkdir(parents=True, exist_ok=True)
    (target / "policies").mkdir(exist_ok=True)
    (target / "frameworks").mkdir(exist_ok=True)
    readme = target / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Umbrella-GovOps repo\n\n"
            "Scaffolded by `umbrella-conformance init`.\n\n"
            "Next: add your first control under `domains/<domain>/controls/`.\n"
        )
    click.secho(f"✓ initialized umbrella repo at {target}", fg="green")


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
@click.option(
    "--check",
    "checks_filter",
    multiple=True,
    help="Run only the named check(s). Repeat for multiple.",
)
@click.option(
    "--format",
    "out_format",
    type=click.Choice(["text", "json"]),
    default="text",
)
@click.option("--strict", is_flag=True, help="Treat warnings as failures.")
def check(
    path: str,
    checks_filter: tuple[str, ...],
    out_format: str,
    strict: bool,
) -> None:
    """Run conformance checks against a repository at PATH."""
    repo = Path(path).resolve()
    selected = (
        [(n, fn) for (n, fn) in ALL_CHECKS if n in checks_filter]
        if checks_filter
        else ALL_CHECKS
    )
    results = run_checks(repo, selected)
    _emit(results, out_format)
    failed = any(r.status == "fail" for r in results)
    warned = any(r.status == "warn" for r in results)
    if failed or (strict and warned):
        sys.exit(1)


@cli.command()
@click.option(
    "--out", "out_dir", type=click.Path(file_okay=False), default="./out"
)
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
def bundle(path: str, out_dir: str) -> None:
    """Compile a check matrix and produce a signable evidence bundle."""
    import datetime
    import hashlib
    import tarfile

    repo = Path(path).resolve()
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Re-run checks to capture state in the bundle
    results = run_checks(repo, ALL_CHECKS)
    manifest = {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "EvidenceBundle",
        "metadata": {
            "generatedAt": datetime.datetime.utcnow().isoformat() + "Z",
            "tool": f"umbrella-conformance/{__version__}",
            "repo": str(repo.name),
        },
        "checks": [
            {"name": r.name, "status": r.status, "details": r.details}
            for r in results
        ],
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    bundle_path = out / "bundle.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tf:
        tf.add(manifest_path, arcname="manifest.json")

    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    (out / "bundle.sha256").write_text(f"{digest}  bundle.tar.gz\n")
    click.secho(f"✓ wrote {bundle_path}", fg="green")
    click.echo(f"  sha256: {digest}")


@cli.command()
@click.argument("bundle_path", type=click.Path(exists=True, dir_okay=False))
def verify(bundle_path: str) -> None:
    """Verify a signed bundle (cosign keyless if available)."""
    import shutil
    import subprocess

    bp = Path(bundle_path).resolve()
    sig = bp.with_suffix(bp.suffix + ".sig")
    cert = bp.with_suffix(bp.suffix + ".pem")

    cosign = shutil.which("cosign")
    if cosign is None:
        click.secho(
            "warn: cosign not installed — verifying digest only", fg="yellow"
        )
        digest_file = bp.parent / "bundle.sha256"
        if not digest_file.exists():
            click.secho("fail: no bundle.sha256 to verify against", fg="red")
            sys.exit(1)
        click.secho("✓ digest file present", fg="green")
        return

    if not sig.exists() or not cert.exists():
        click.secho(
            f"fail: missing {sig.name} or {cert.name} alongside bundle",
            fg="red",
        )
        sys.exit(1)

    try:
        subprocess.run(
            [
                cosign,
                "verify-blob",
                "--certificate",
                str(cert),
                "--signature",
                str(sig),
                "--certificate-identity-regexp",
                ".*",
                "--certificate-oidc-issuer-regexp",
                ".*",
                str(bp),
            ],
            check=True,
        )
        click.secho("✓ cosign verification passed", fg="green")
    except subprocess.CalledProcessError:
        click.secho("fail: cosign verification failed", fg="red")
        sys.exit(1)


def _emit(results: list[CheckResult], out_format: str) -> None:
    if out_format == "json":
        click.echo(
            json.dumps(
                [
                    {"name": r.name, "status": r.status, "details": r.details}
                    for r in results
                ],
                indent=2,
            )
        )
        return
    status_color = {"pass": "green", "warn": "yellow", "fail": "red"}
    glyph = {"pass": "✓", "warn": "!", "fail": "✗"}
    for r in results:
        click.secho(
            f"{glyph[r.status]} {r.name:30s} {r.status.upper()}",
            fg=status_color[r.status],
        )
        for d in r.details:
            click.echo(f"    {d}")
    n_pass = sum(1 for r in results if r.status == "pass")
    n_warn = sum(1 for r in results if r.status == "warn")
    n_fail = sum(1 for r in results if r.status == "fail")
    click.echo()
    click.echo(f"  {n_pass} passed · {n_warn} warned · {n_fail} failed")


if __name__ == "__main__":
    cli()
