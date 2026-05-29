# Architecture

See the [root README](../README.md) for the full blueprint. This document will
hold deeper diagrams, sequence flows for the orchestrator, and ADR cross-links
as the engine is built out.

## Layers

1. **Framework Layer** — `frameworks/` — OSCAL catalogs (NIST AI RMF, EU AI Act, ISO 42001).
2. **Domain Layer** — `domains/` — Human-authored controls per governance area.
3. **Crosswalk Layer** — `crosswalks/` — Unified Control ID pivot.
4. **Policy Layer** — `policies/` — Compiled Rego + orchestration DAG.
5. **Evidence Layer** — `evidence/` — Signed, immutable bundles + Rekor receipts.
6. **Reporting Layer** — `reports/` — Conformity packs, RMF profiles, heatmaps.
