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


# DSSE / in-toto Statement v1 envelope constants
DSSE_PAYLOAD_TYPE = "application/vnd.in-toto+json"
GOVOPS_PREDICATE_TYPE = "https://aigovops.org/attestations/govops-evidence/v1"
INTOTO_STATEMENT_TYPE = "https://in-toto.io/Statement/v1"


def _load_beacon_receipts(beacon_bundle: Path) -> list[dict]:
    """Load Beacon receipts from a path. Accepts:

      * a single JSON file containing one receipt (runtime format)
      * a JSONL file (one receipt per line) — foundation audit log
      * a directory containing *.json (each one receipt)

    Returns a list of {"id", "format", "payload", "issued_at"} dicts ready to
    embed in EvidenceBundle.receipts[].
    """
    receipts: list[dict] = []
    if beacon_bundle.is_dir():
        files = sorted(beacon_bundle.glob("*.json"))
    elif beacon_bundle.suffix == ".jsonl":
        files = [beacon_bundle]
    else:
        files = [beacon_bundle]

    for f in files:
        text = f.read_text()
        if f.suffix == ".jsonl":
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                receipts.append(_normalize_receipt(entry))
        else:
            entry = json.loads(text)
            # Some Beacon foundation logs export as {"entries": [...]}
            if isinstance(entry, dict) and "entries" in entry and isinstance(entry["entries"], list):
                for e in entry["entries"]:
                    receipts.append(_normalize_receipt(e))
            elif isinstance(entry, list):
                for e in entry:
                    receipts.append(_normalize_receipt(e))
            else:
                receipts.append(_normalize_receipt(entry))
    return receipts


def _normalize_receipt(entry: dict) -> dict:
    """Detect foundation vs runtime format and produce the EvidenceBundle
    receipts[] shape. Does NOT mutate the payload — it is embedded verbatim."""
    # Foundation receipts have a chained audit-log shape with both entry_sha256
    # and a prev_*_sha256 link (literal "GENESIS" on entry 1).
    if "entry_sha256" in entry and (
        "prev_entry_sha256" in entry or "prev_sha256" in entry
    ):
        return {
            "id": entry["entry_sha256"],
            "format": "foundation",
            "payload": entry,
            "issued_at": (
                entry.get("timestamp_utc")
                or entry.get("ts")
                or entry.get("timestamp")
                or ""
            ),
        }
    # runtime / OVERT: prefer entry["id"], fall back to a hash of the payload
    rid = entry.get("id") or entry.get("receipt_id")
    if rid is None:
        import hashlib as _h
        rid = _h.sha256(
            json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
    issued = (
        entry.get("issued_at")
        or entry.get("ts")
        or entry.get("timestamp")
        or (entry.get("signature") or {}).get("ts")
        or ""
    )
    return {"id": rid, "format": "runtime", "payload": entry, "issued_at": issued}


def _dsse_envelope(payload: dict) -> dict:
    """Wrap an EvidenceBundle in an in-toto Statement v1 + DSSE envelope.
    No signature is attached here — `cosign sign-blob` produces the detached
    signature + certificate. The envelope shape is what gets signed."""
    import base64
    statement = {
        "_type": INTOTO_STATEMENT_TYPE,
        "predicateType": GOVOPS_PREDICATE_TYPE,
        "subject": [
            {
                "name": payload.get("metadata", {}).get("repo", "unknown"),
                "digest": {
                    "sha256": _payload_sha256(payload),
                },
            }
        ],
        "predicate": payload,
    }
    return {
        "payloadType": DSSE_PAYLOAD_TYPE,
        "payload": base64.b64encode(
            json.dumps(statement, separators=(",", ":"), sort_keys=True).encode()
        ).decode(),
    }


def _payload_sha256(payload: dict) -> str:
    import hashlib as _h
    canon = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return _h.sha256(canon).hexdigest()


@cli.command()
@click.option(
    "--out", "out_dir", type=click.Path(file_okay=False), default="./out"
)
@click.option(
    "--beacon-bundle",
    "beacon_bundle",
    type=click.Path(exists=True),
    default=None,
    help="Path to a Beacon receipt, JSONL audit log, or directory of receipts to embed.",
)
@click.option(
    "--commit-sha",
    "commit_sha",
    type=str,
    default=None,
    help="Git commit SHA to record in metadata.commit_sha.",
)
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
def bundle(
    path: str,
    out_dir: str,
    beacon_bundle: str | None,
    commit_sha: str | None,
) -> None:
    """Compile a check matrix and produce a signable evidence bundle.

    With --beacon-bundle, the named Beacon receipts are embedded verbatim into
    EvidenceBundle.receipts[], and any matching checks get evidence_refs[]
    populated. The bundle is wrapped in an in-toto Statement v1 / DSSE envelope
    ready for `cosign sign-blob`.
    """
    import datetime
    import hashlib
    import tarfile

    repo = Path(path).resolve()
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Re-run checks to capture state in the bundle
    results = run_checks(repo, ALL_CHECKS)

    receipts_arr: list[dict] = []
    if beacon_bundle is not None:
        try:
            receipts_arr = _load_beacon_receipts(Path(beacon_bundle).resolve())
            click.secho(
                f"  embedded {len(receipts_arr)} Beacon receipt(s) from {beacon_bundle}",
                fg="cyan",
            )
        except Exception as exc:
            click.secho(f"warn: failed to load Beacon receipts: {exc}", fg="yellow")

    # Map every receipt id into evidence_refs for the 'evidence-signed' check.
    # This is the asymmetric binding: receipts know nothing of UCIDs; the
    # check is what knows which receipts back it.
    receipt_ids = [r["id"] for r in receipts_arr]
    manifest = {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "EvidenceBundle",
        "metadata": {
            "generatedAt": datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "tool": f"umbrella-conformance/{__version__}",
            "repo": str(repo.name),
            **({"commit_sha": commit_sha} if commit_sha else {}),
        },
        "checks": [
            {
                "name": r.name,
                "status": r.status,
                "details": r.details,
                "evidence_refs": (
                    receipt_ids if r.name == "evidence-signed" else []
                ),
            }
            for r in results
        ],
        "receipts": receipts_arr,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=False))

    # DSSE envelope (unsigned) — cosign sign-blob produces the .sig / .pem
    envelope = _dsse_envelope(manifest)
    envelope_path = out / "bundle.intoto.json"
    envelope_path.write_text(json.dumps(envelope, indent=2))

    bundle_path = out / "bundle.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tf:
        tf.add(manifest_path, arcname="manifest.json")
        tf.add(envelope_path, arcname="bundle.intoto.json")

    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    (out / "bundle.sha256").write_text(f"{digest}  bundle.tar.gz\n")
    click.secho(f"✓ wrote {bundle_path}", fg="green")
    click.echo(f"  sha256: {digest}")
    click.echo(f"  manifest: {manifest_path}")
    click.echo(f"  dsse envelope: {envelope_path}")
    if receipts_arr:
        click.echo(f"  embedded receipts: {len(receipts_arr)}")


@cli.command()
@click.argument("bundle_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--beacon-bundle",
    "beacon_bundle",
    type=click.Path(exists=True),
    default=None,
    help="Verify embedded Beacon receipts by shelling out to `beacon-verify`.",
)
@click.option(
    "--beacon-public-key",
    "beacon_public_key",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Public key (PEM) to verify embedded Beacon receipts. Passed through to beacon-verify.",
)
@click.option(
    "--ucid-coverage",
    is_flag=True,
    default=False,
    help="Fail if any enforced control with `beacon: required` has no receipt evidence.",
)
def verify(
    bundle_path: str,
    beacon_bundle: str | None,
    beacon_public_key: str | None,
    ucid_coverage: bool,
) -> None:
    """Verify a signed bundle (cosign keyless if available) and optionally
    re-verify embedded Beacon receipts.

    Exit codes:
      0  all checks passed
      1  bundle digest / cosign signature failed
      2  embedded Beacon receipt verification failed
      3  UCID coverage gap (with --ucid-coverage)
    """
    import shutil
    import subprocess

    bp = Path(bundle_path).resolve()
    sig = bp.with_suffix(bp.suffix + ".sig")
    cert = bp.with_suffix(bp.suffix + ".pem")

    # --- Stage 1: outer DSSE / cosign signature -------------------------------
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
    elif sig.exists() and cert.exists():
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
    else:
        click.secho(
            f"warn: missing {sig.name} or {cert.name} — skipping cosign",
            fg="yellow",
        )

    # --- Stage 2: re-verify embedded Beacon receipts --------------------------
    if beacon_bundle is not None:
        bv = shutil.which("beacon-verify")
        if bv is None:
            click.secho(
                "fail: --beacon-bundle requires `beacon-verify` on PATH",
                fg="red",
            )
            sys.exit(2)
        cmd = [bv, str(Path(beacon_bundle).resolve())]
        if beacon_public_key:
            cmd += ["--public-key", str(Path(beacon_public_key).resolve())]
        try:
            subprocess.run(cmd, check=True)
            click.secho("✓ beacon-verify passed", fg="green")
        except subprocess.CalledProcessError:
            click.secho("fail: beacon-verify rejected the receipts", fg="red")
            sys.exit(2)

    # --- Stage 3: UCID coverage gate ------------------------------------------
    if ucid_coverage:
        # Locate the manifest — either alongside bundle.tar.gz, or inside it.
        manifest_path = bp.parent / "manifest.json"
        manifest = None
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
        else:
            # Extract manifest.json from the tarball without unpacking the whole thing
            import tarfile
            try:
                with tarfile.open(bp, "r:gz") as tf:
                    m = tf.extractfile("manifest.json")
                    if m is not None:
                        manifest = json.loads(m.read().decode())
            except Exception:
                pass
        if manifest is None:
            click.secho("fail: cannot read manifest.json for coverage check", fg="red")
            sys.exit(3)

        receipt_ids = {r["id"] for r in manifest.get("receipts", [])}
        gaps: list[str] = []
        for c in manifest.get("checks", []):
            ucid = c.get("ucid")
            if not ucid:
                continue
            refs = c.get("evidence_refs", [])
            if not refs or not any(r in receipt_ids for r in refs):
                gaps.append(f"{ucid} (check {c['name']}) has no embedded receipt")
        if gaps:
            click.secho("fail: UCID coverage gaps:", fg="red")
            for g in gaps:
                click.echo(f"  - {g}")
            sys.exit(3)
        click.secho("✓ UCID coverage OK", fg="green")


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
