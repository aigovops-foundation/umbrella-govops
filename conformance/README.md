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

# Validate every control + crosswalk + evidence file
umbrella-conformance check .

# Run a single check matrix and produce a signable bundle
umbrella-conformance bundle --out ./out

# Verify a signed bundle (cosign keyless)
umbrella-conformance verify ./out/bundle.tar.gz
```

## Exit codes
- `0` — all checks passed
- `1` — schema or check violation
- `2` — internal error / missing dependency

## What it checks

| Check | What it verifies |
|---|---|
| `schema-valid` | Every YAML under `domains/`, `crosswalks/`, `policies/`, `frameworks/` validates against its JSON Schema |
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
