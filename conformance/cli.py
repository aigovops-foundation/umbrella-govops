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


UMBRELLA_RECEIPT_SCHEMA = "umbrella-receipt/1"
SUMS_NAME = "SHA256SUMS"
RECEIPTS_NAME = "receipts.ndjson"
ED25519_SIG_SUFFIX = ".sig.json"


def _sha256_hex(data: bytes) -> str:
    import hashlib as _h
    return _h.sha256(data).hexdigest()


def _umbrella_receipt(
    *,
    event_type: str,
    subject: str,
    attributes: dict,
    ts: str,
    environment: str,
) -> dict:
    """A receipt in the Beacon envelope shape (so Lantern and beacon-verify
    read it), describing one fact about the governed repo. The id is a
    content hash, so an unchanged fact keeps its id across rebuilds and
    `lantern diff` shows only what actually changed."""
    from .signing import canonicalize

    body = canonicalize({"event_type": event_type, "subject": subject, "attributes": attributes})
    return {
        "id": _sha256_hex(body),
        "ts_utc": ts,
        "schema_version": UMBRELLA_RECEIPT_SCHEMA,
        "user": {"sub": "umbrella-conformance"},
        "vendor": "in-house",
        "model": "n/a",
        "version": __version__,
        "prompt_hash": _sha256_hex(body),
        "result_hash": _sha256_hex(
            str(attributes.get("decision") or attributes.get("status") or "").encode()
        ),
        "event_type": event_type,
        "environment": environment,
        "subject": subject,
        "attributes": attributes,
    }


def _policy_receipts(repo: Path, ts: str, environment: str) -> tuple[list[dict], list[tuple[str, bytes]]]:
    from .checks.schema import find_policies

    receipts: list[dict] = []
    files: list[tuple[str, bytes]] = []
    for p, doc in find_policies(repo):
        rel = p.relative_to(repo).as_posix()
        data = p.read_bytes()
        files.append((f"policies/{rel}", data))
        name = doc["policy"]
        receipts.append(
            _umbrella_receipt(
                event_type="policy.declared",
                subject=f"policy://{name}",
                attributes={
                    "policy": name,
                    "file": rel,
                    "file_sha256": _sha256_hex(data),
                    "default": doc.get("default"),
                    "controls": len(doc.get("controls") or []),
                    "applies_to": doc.get("applies_to") or {},
                },
                ts=ts,
                environment=environment,
            )
        )
        for c in doc.get("controls") or []:
            attrs = {"policy": name, "file": rel}
            for k in ("action", "tier", "decision", "approver_role", "reason", "ucid", "constraints"):
                if k in c:
                    attrs[k] = c[k]
            receipts.append(
                _umbrella_receipt(
                    event_type="policy.control",
                    subject=f"policy://{name}/{c['action']}",
                    attributes=attrs,
                    ts=ts,
                    environment=environment,
                )
            )
    return receipts, files


@cli.command()
@click.option("--out", "out_dir", type=click.Path(file_okay=False), default="./keys",
              help="Directory for signing.pem (private, mode 600) and signing.pub.pem.")
def keygen(out_dir: str) -> None:
    """Create an Ed25519 key pair for `bundle --sign-key`."""
    from .signing import SigningError, generate_keypair, key_fpr, load_public_key

    try:
        priv, pub = generate_keypair(Path(out_dir))
    except SigningError as exc:
        click.secho(f"fail: {exc}", fg="red")
        sys.exit(1)
    click.secho(f"✓ private key: {priv}  (keep it secret; never commit it)", fg="green")
    click.echo(f"  public key:  {pub}  (give this to whoever verifies)")
    click.echo(f"  key_fpr:     {key_fpr(load_public_key(pub))}")


@cli.command()
@click.option(
    "--out", "out_dir", type=click.Path(file_okay=False), default="./out"
)
@click.option(
    "--beacon-bundle",
    "beacon_bundle",
    type=click.Path(exists=True),
    default=None,
    help=(
        "Beacon output to embed: an audit bundle directory (manifest.json + receipts/), "
        "a .ndjson/.jsonl receipt file, a .json receipt file, or a directory of them."
    ),
)
@click.option(
    "--commit-sha",
    "commit_sha",
    type=str,
    default=None,
    help="Git commit SHA to record in metadata.commit_sha.",
)
@click.option(
    "--sign-key",
    "sign_key",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Ed25519 private key (PEM, from `keygen`). Signs the bundle and every receipt it writes.",
)
@click.option(
    "--environment",
    default="local",
    show_default=True,
    help="Environment recorded on the receipts this bundle writes.",
)
@click.argument("path", type=click.Path(exists=True, file_okay=False), default=".")
def bundle(
    path: str,
    out_dir: str,
    beacon_bundle: str | None,
    commit_sha: str | None,
    sign_key: str | None,
    environment: str,
) -> None:
    """Compile a check matrix and produce a signable evidence bundle.

    Writes to --out: bundle.tar.gz, bundle.sha256, SHA256SUMS, manifest.json,
    bundle.intoto.json (DSSE envelope), receipts.ndjson (one receipt per policy
    control and per check, readable by `lantern read`), and policies/ (the
    policy files that were validated). Refuses to bundle a repo whose
    schema-valid check fails: the rule is valid or it does not run.

    With --beacon-bundle, Beacon receipts are embedded verbatim into
    EvidenceBundle.receipts[] (and runtime receipts are also copied into
    receipts.ndjson). With --sign-key, bundle.tar.gz.sig.json holds an Ed25519
    signature over bundle.tar.gz; otherwise sign with
    `cosign sign-blob --output-signature out/bundle.tar.gz.sig --output-certificate out/bundle.tar.gz.pem`.
    """
    import datetime
    import io
    import tarfile

    from . import beacon as beacon_mod
    from .signing import SigningError, load_private_key, sign_receipt, signature_block

    repo = Path(path).resolve()
    out = Path(out_dir).resolve()

    key = None
    if sign_key is not None:
        try:
            key = load_private_key(Path(sign_key))
        except SigningError as exc:
            click.secho(f"fail: {exc}", fg="red")
            sys.exit(2)

    results = run_checks(repo, ALL_CHECKS)
    schema = next(r for r in results if r.name == "schema-valid")
    if schema.status == "fail":
        click.secho("fail: schema-valid failed — refusing to bundle an invalid policy", fg="red")
        for d in schema.details:
            click.echo(f"    {d}")
        sys.exit(1)

    beacon_in = None
    if beacon_bundle is not None:
        try:
            beacon_in = beacon_mod.load(Path(beacon_bundle).resolve())
        except (beacon_mod.BeaconInputError, OSError, ValueError) as exc:
            click.secho(f"fail: cannot read Beacon output {beacon_bundle}: {exc}", fg="red")
            sys.exit(2)
        click.secho(
            f"  embedded {len(beacon_in.receipts)} Beacon receipt(s) from {beacon_bundle} "
            f"({beacon_in.source_kind})",
            fg="cyan",
        )

    out.mkdir(parents=True, exist_ok=True)
    # A signature left over from a previous build must never sit beside a new tarball.
    for stale in ("bundle.tar.gz.sig", "bundle.tar.gz.pem", "bundle.tar.gz" + ED25519_SIG_SUFFIX):
        (out / stale).unlink(missing_ok=True)

    generated_at = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    receipts_arr = beacon_in.receipts if beacon_in else []
    receipt_ids = [r["id"] for r in receipts_arr]
    policy_receipts, policy_files = _policy_receipts(repo, generated_at, environment)

    manifest = {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "EvidenceBundle",
        "metadata": {
            "generatedAt": generated_at,
            "tool": f"umbrella-conformance/{__version__}",
            "repo": str(repo.name),
            **({"commit_sha": commit_sha} if commit_sha else {}),
        },
        "checks": [
            {
                "name": r.name,
                "status": r.status,
                "details": r.details,
                "evidence_refs": (receipt_ids if r.name == "evidence-signed" else []),
            }
            for r in results
        ],
        "receipts": receipts_arr,
        "policies": [
            {"path": name, "sha256": _sha256_hex(data)} for name, data in policy_files
        ],
    }
    if beacon_in is not None:
        manifest["metadata"]["beacon_source"] = {
            "kind": beacon_in.source_kind,
            **{k: v for k, v in beacon_in.info.items() if v is not None},
        }

    check_receipts = [
        _umbrella_receipt(
            event_type="conformance.check",
            subject=f"check://{r.name}",
            attributes={"name": r.name, "status": r.status},
            ts=generated_at,
            environment=environment,
        )
        for r in results
    ]
    own = policy_receipts + check_receipts
    if key is not None:
        own = [sign_receipt(key, r) for r in own]
    beacon_runtime = [
        r["payload"] for r in receipts_arr
        if r["format"] == "runtime" and "event_type" in r["payload"]
    ]
    receipts_ndjson = "".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
        for r in own + beacon_runtime
    ).encode("utf-8")

    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=False).encode()
    envelope_bytes = json.dumps(_dsse_envelope(manifest), indent=2).encode()
    artifacts: list[tuple[str, bytes]] = [
        ("manifest.json", manifest_bytes),
        ("bundle.intoto.json", envelope_bytes),
        (RECEIPTS_NAME, receipts_ndjson),
        *policy_files,
    ]
    sums = "".join(f"{_sha256_hex(data)}  {name}\n" for name, data in artifacts).encode()

    # Loose copies (what `lantern read` and humans open) ...
    for name, data in [*artifacts, (SUMS_NAME, sums)]:
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    # ... and the tarball, written deterministically from the same bytes.
    bundle_path = out / "bundle.tar.gz"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in [*artifacts, (SUMS_NAME, sums)]:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))
    bundle_bytes = buf.getvalue()
    bundle_path.write_bytes(bundle_bytes)

    digest = _sha256_hex(bundle_bytes)
    (out / "bundle.sha256").write_text(f"{digest}  bundle.tar.gz\n")

    if key is not None:
        block = signature_block(key, bundle_bytes)
        block.update({"canonical_form": "raw-bytes", "signed": "bundle.tar.gz", "sha256": digest})
        (out / ("bundle.tar.gz" + ED25519_SIG_SUFFIX)).write_text(json.dumps(block, indent=2) + "\n")

    click.secho(f"✓ wrote {bundle_path}", fg="green")
    click.echo(f"  sha256: {digest}")
    click.echo(f"  manifest: {out / 'manifest.json'}")
    click.echo(f"  dsse envelope: {out / 'bundle.intoto.json'}")
    click.echo(f"  receipts: {out / RECEIPTS_NAME} ({len(own) + len(beacon_runtime)})")
    if policy_files:
        click.echo(f"  policies: {len(policy_files)} file(s)")
    if receipts_arr:
        click.echo(f"  embedded receipts: {len(receipts_arr)}")
    if key is not None:
        click.echo(f"  signature: {out / ('bundle.tar.gz' + ED25519_SIG_SUFFIX)}")
    else:
        click.secho(
            "  unsigned — `verify` will refuse it until it is signed "
            "(--sign-key, or cosign sign-blob)",
            fg="yellow",
        )


def _parse_sums(text: str) -> dict[str, str]:
    sums: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError(f"malformed line: {line!r}")
        sums[parts[1].strip().lstrip("*")] = parts[0].lower()
    return sums


def _verify_integrity(bp: Path) -> tuple[list[str], dict | None, bytes | None]:
    """Recompute every digest the bundle claims. Returns (errors, manifest, receipts bytes)."""
    import base64
    import tarfile

    errors: list[str] = []
    bundle_bytes = bp.read_bytes()

    digest_file = bp.parent / "bundle.sha256"
    if not digest_file.exists():
        errors.append(f"no bundle.sha256 beside {bp.name}")
    else:
        parts = digest_file.read_text().split()
        if not parts:
            errors.append("bundle.sha256 is empty")
        elif parts[0].lower() != _sha256_hex(bundle_bytes):
            errors.append(
                f"{bp.name}: sha256 mismatch (recorded {parts[0][:12]}…, "
                f"actual {_sha256_hex(bundle_bytes)[:12]}…)"
            )

    members: dict[str, bytes] = {}
    try:
        with tarfile.open(bp, "r:gz") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                f = tf.extractfile(m)
                if f is not None:
                    members[m.name] = f.read()
    except (tarfile.TarError, OSError, EOFError) as exc:
        errors.append(f"{bp.name}: cannot read tarball — {exc}")
        return errors, None, None

    if SUMS_NAME not in members:
        errors.append(f"{bp.name}: no {SUMS_NAME} inside — rebuild with this version of `bundle`")
        return errors, None, None
    try:
        sums = _parse_sums(members[SUMS_NAME].decode())
    except (ValueError, UnicodeDecodeError) as exc:
        errors.append(f"{SUMS_NAME}: {exc}")
        return errors, None, None

    for name, want in sums.items():
        if name not in members:
            errors.append(f"{name}: listed in {SUMS_NAME} but missing from {bp.name}")
        elif _sha256_hex(members[name]) != want:
            errors.append(f"{name}: sha256 mismatch inside {bp.name}")
        loose = bp.parent / name
        if loose.is_file() and _sha256_hex(loose.read_bytes()) != want:
            errors.append(f"{name}: the copy beside {bp.name} does not match {SUMS_NAME}")
    for name in members:
        if name != SUMS_NAME and name not in sums:
            errors.append(f"{name}: present in {bp.name} but not covered by {SUMS_NAME}")
    for name in ("manifest.json", "bundle.intoto.json"):
        if name not in sums:
            errors.append(f"{SUMS_NAME} does not cover {name}")

    manifest = None
    try:
        manifest = json.loads(members["manifest.json"])
        envelope = json.loads(members["bundle.intoto.json"])
        statement = json.loads(base64.b64decode(envelope["payload"]))
        subject = statement["subject"][0]["digest"]["sha256"]
        if subject != _payload_sha256(manifest):
            errors.append("DSSE subject digest does not match manifest.json")
        if statement.get("predicate") != manifest:
            errors.append("DSSE predicate is not the manifest")
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        errors.append(f"manifest / DSSE envelope unreadable: {exc}")

    return errors, manifest, members.get(RECEIPTS_NAME)


@cli.command()
@click.argument("bundle_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--public-key",
    "public_key",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Ed25519 public key (PEM) the bundle must be signed by (bundle --sign-key).",
)
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
    public_key: str | None,
    beacon_bundle: str | None,
    beacon_public_key: str | None,
    ucid_coverage: bool,
) -> None:
    """Verify a bundle: recompute every digest, then check its signature.

    There is no unsigned pass. A bundle verifies only when every sha256 it
    claims recomputes (the tarball, every artifact inside it, the loose copies
    beside it, the DSSE subject) AND it carries a valid signature: Ed25519
    (bundle.tar.gz.sig.json, checked against --public-key) or cosign keyless
    (bundle.tar.gz.sig + bundle.tar.gz.pem, checked with `cosign verify-blob`).

    Exit codes:
      0  all checks passed
      1  integrity failure, or signature missing / invalid
      2  embedded Beacon receipt verification failed
      3  UCID coverage gap (with --ucid-coverage)
    """
    import shutil
    import subprocess

    from .signing import SigningError, key_fpr, load_public_key, verify_bytes, verify_receipt

    bp = Path(bundle_path).resolve()

    # --- Stage 1: integrity ---------------------------------------------------
    errors, manifest, receipts_bytes = _verify_integrity(bp)
    if errors:
        click.secho("fail: integrity", fg="red")
        for e in errors:
            click.echo(f"  - {e}")
        sys.exit(1)
    click.secho("✓ digests recomputed and match (tarball, artifacts, DSSE subject)", fg="green")

    # --- Stage 2: signature (required) -----------------------------------------
    ed_sig = bp.with_name(bp.name + ED25519_SIG_SUFFIX)
    sig = bp.with_name(bp.name + ".sig")
    cert = bp.with_name(bp.name + ".pem")
    if public_key is not None:
        try:
            pub = load_public_key(Path(public_key))
        except SigningError as exc:
            click.secho(f"fail: {exc}", fg="red")
            sys.exit(1)
        if not ed_sig.exists():
            click.secho(f"fail: unsigned — no {ed_sig.name} beside the bundle", fg="red")
            sys.exit(1)
        block = json.loads(ed_sig.read_text())
        if block.get("key_fpr") != key_fpr(pub):
            click.secho(
                f"fail: signed by {block.get('key_fpr')}, not by the key you supplied "
                f"({key_fpr(pub)})",
                fg="red",
            )
            sys.exit(1)
        if not verify_bytes(pub, bp.read_bytes(), block):
            click.secho("fail: Ed25519 signature does not verify", fg="red")
            sys.exit(1)
        click.secho(f"✓ Ed25519 signature valid ({key_fpr(pub)})", fg="green")
        # Every receipt this tool wrote must carry a valid signature from the same key.
        bad = 0
        for line in (receipts_bytes or b"").decode().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("schema_version") != UMBRELLA_RECEIPT_SCHEMA:
                continue  # embedded Beacon receipt — beacon-verify's job
            if not verify_receipt(pub, r):
                bad += 1
        if bad:
            click.secho(f"fail: {bad} receipt(s) in {RECEIPTS_NAME} are unsigned or invalid", fg="red")
            sys.exit(1)
        click.secho(f"✓ receipt signatures valid ({RECEIPTS_NAME})", fg="green")
    elif sig.exists() and cert.exists():
        cosign = shutil.which("cosign")
        if cosign is None:
            click.secho(
                "fail: bundle carries a cosign signature but cosign is not installed — "
                "cannot verify it",
                fg="red",
            )
            sys.exit(1)
        try:
            subprocess.run(
                [
                    cosign, "verify-blob",
                    "--certificate", str(cert),
                    "--signature", str(sig),
                    "--certificate-identity-regexp", ".*",
                    "--certificate-oidc-issuer-regexp", ".*",
                    str(bp),
                ],
                check=True,
            )
            click.secho("✓ cosign verification passed", fg="green")
        except subprocess.CalledProcessError:
            click.secho("fail: cosign verification failed", fg="red")
            sys.exit(1)
    elif ed_sig.exists():
        click.secho(
            f"fail: bundle is Ed25519-signed ({json.loads(ed_sig.read_text()).get('key_fpr')}); "
            "pass --public-key with the signer's public key. "
            "A key shipped beside the bundle is never trusted.",
            fg="red",
        )
        sys.exit(1)
    else:
        click.secho(
            "fail: unsigned — digests match but there is no signature. Sign with "
            "`bundle --sign-key` (then verify with --public-key) or `cosign sign-blob`.",
            fg="red",
        )
        sys.exit(1)

    # --- Stage 3: re-verify embedded Beacon receipts --------------------------
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

    # --- Stage 4: UCID coverage gate ------------------------------------------
    if ucid_coverage:
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
