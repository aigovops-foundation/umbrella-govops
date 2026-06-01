# Scope

What Umbrella-GovOps **is**, what it is **not**, and where the boundary sits
with its companion products. This complements
[`GOVERNANCE.md`](GOVERNANCE.md) (how decisions are made) and
[`docs/api/`](docs/api/) (the data contracts themselves).

## In scope

- **Control authoring** — versioned, citable controls under
  `domains/<domain>/controls/`, each bound to a UCID.
- **The UCID registry** — `crosswalks/unified-control-id.yaml`, the pivot from
  one obligation to NIST AI RMF / EU AI Act / ISO 42001 citations.
- **Schemas + conformance** — JSON Schemas (`conformance/schemas/`) and the
  `umbrella-conformance` CLI that validates artifacts and assembles signed
  evidence bundles.
- **Evidence assembly** — `EvidenceBundle` manifests, in-toto / DSSE
  envelopes, SLSA provenance, and the binding of Beacon receipts to UCIDs.
- **Published contracts** — the data model and (DRAFT v0) governance API in
  `docs/api/`, which downstream projects code against.

## Out of scope

- A running governance HTTP **service** — the `docs/api/openapi.yaml` contract
  is DRAFT v0 and unimplemented here.
- **Runtime** discovery, admission, and receipt *emission* — that is
  [Beacon](https://github.com/bobrapp/aigovops-beacon)'s job; Umbrella
  *consumes* Beacon receipts as evidence.
- Human-facing **rendering** of conformity views — that is Lantern's job.
- Judging the *semantic* correctness of framework mappings — that remains a
  human review responsibility in `crosswalks/` PRs.

## Testing infrastructure (this addition)

The repo carries a full test pyramid wired into CI on every PR:

- **Unit** — CLI surface, schema strictness, UCID-registry format / uniqueness
  / no-orphan-reference checks, and YAML parseability of every data file.
- **E2E (integration)** — cross-artifact integrity (no dangling UCID ↔ control
  references in either direction), registry round-trip equality, and the
  conformance CLI exercised against the shipped pass/fail fixtures.
- **Scale** — synthetic repositories of 100 / 1 000 / 10 000 controls and a
  1 000-mapping crosswalk-check, with wall-clock SLAs. Gated to a dedicated job
  + weekly cron so it never slows the PR critical path.
- **Chaos** — deterministic mutation testing, **Hypothesis** property-based
  fuzzing of the validators, and **filesystem chaos** (missing files,
  truncated YAML, BOM, permission errors). Every break must surface as a
  structured failure, never an unhandled crash.

Contract documentation for all of the above lives in
[`docs/api/`](docs/api/). See [`tests/README.md`](tests/README.md) for the
harness reference and [`CONTRIBUTING.md`](CONTRIBUTING.md) for the per-PR
expectations.
