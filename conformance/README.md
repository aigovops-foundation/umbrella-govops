# umbrella-conformance

The conformance CLI for Umbrella-GovOps. Validates that a control bundle,
evidence package, or release attestation meets the Umbrella v1 schema and
the OVERT `umbrella-govops.v1` predicate.

## Install

```bash
pipx install umbrella-conformance
# or
pip install umbrella-conformance
```

## Quickstart

```bash
# Scaffold a new umbrella repo
umbrella-conformance init my-ai-app

# Validate every control + crosswalk + agent policy (non-zero exit if invalid,
# or if there is nothing to validate)
umbrella-conformance check .

# Produce a signed bundle (Ed25519; or sign bundle.tar.gz with cosign sign-blob)
umbrella-conformance keygen --out ./keys
umbrella-conformance bundle --out ./out --sign-key ./keys/signing.pem \
  [--beacon-bundle ./beacon-bundle-dir | ./receipts/2026-10-29.ndjson]

# Verify: recomputes every sha256, requires a valid signature (no unsigned pass)
umbrella-conformance verify ./out/bundle.tar.gz --public-key ./keys/signing.pub.pem
```

### Bundle layout (`--out`)

| File | What it is |
|---|---|
| `bundle.tar.gz` | everything below, plus `SHA256SUMS` |
| `bundle.sha256` | sha256 of `bundle.tar.gz` |
| `SHA256SUMS` | sha256 of every artifact; `verify` recomputes each, inside the tarball and the loose copies |
| `manifest.json` / `bundle.intoto.json` | EvidenceBundle and its in-toto / DSSE envelope |
| `receipts.ndjson` | one Beacon-envelope receipt per policy control and per check (signed with `--sign-key`), plus embedded Beacon runtime receipts — `lantern read` input |
| `policies/` | the agent policy files that passed `schema-valid` |
| `bundle.tar.gz.sig.json` | Ed25519 signature (with `--sign-key`) |

### Beacon inputs (`--beacon-bundle`)

A Beacon audit bundle directory (`manifest.json`, `manifest.sha256`,
`receipts/*.ndjson`, `public_keys/`, `gate_decisions.json`), a `.ndjson` /
`.jsonl` receipt file, a `.json` receipt file, or a directory of receipt files.
A Beacon bundle whose `manifest.sha256` or receipt counts do not match is
refused. Receipt signatures are re-verified by `verify --beacon-bundle`
(shells out to `beacon-verify`).

## Exit codes
- `0` — all checks passed
- `1` — schema or check violation
- `2` — internal error / missing dependency

## What it checks

| Check | What it verifies |
|---|---|
| `schema-valid` | Every YAML under `domains/`, `crosswalks/`, `frameworks/` validates against its JSON Schema, and every agent gate policy (`policy.yaml`, `*.policy.yaml`, or `policy:` + `controls:` in the root, `policies/`, `catalog/`) validates against `schemas/policy.schema.json` (tiers C0–C4, allow/hold/deny, hold needs `approver_role`, deny needs `reason`, `default: deny`). Fails if nothing was validated. |
| `crosswalk-resolved` | Every UCID referenced by a control exists in the crosswalk, and every `implementing_controls` ID resolves to a real file |
| `evidence-signed` | Each evidence bundle has a `signature.json` produced by a Sigstore-trusted identity |
| `slsa-provenance-present` | Each release artifact has a SLSA v1.0 provenance attestation |
| `overt-predicate-valid` | The `umbrella-govops.v1` OVERT predicate is present and conforms |
| `controls-have-checks` | Every control declares at least one runnable check |

## Architecture

```
conformance/
├── cli.py              # Click entrypoint
├── checks/             # One file per check (pluggable)
│   ├── schema.py
│   ├── crosswalk.py
│   ├── evidence.py
│   ├── slsa.py
│   ├── overt.py
│   └── controls.py
├── schemas/            # JSON Schema definitions
│   ├── control.schema.json
│   ├── crosswalk.schema.json
│   ├── evidence-bundle.schema.json
│   └── attestation.schema.json
└── fixtures/
    ├── pass/           # Sample bundles that pass every check
    └── fail/           # Sample bundles designed to trip specific checks
```
