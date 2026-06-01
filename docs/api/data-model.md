# Data Model

Umbrella-GovOps is a **data-contract** project: its public surface is the set
of versioned artifacts it publishes, not a running service. This document is a
field-by-field reference for every artifact, with examples drawn from the
repository.

The four first-class artifacts and how they relate:

```
GovernanceDomain ──groups──▶ Control ──cites via metadata.ucid──▶ UCID (in Crosswalk)
                                  │                                   │
                                  └──checks[] produce evidence──▶ EvidenceBundle.checks[]
                                                                      │
                                  Beacon receipts ──embedded──▶ EvidenceBundle.receipts[]
```

See also [schema-catalog.md](schema-catalog.md) for the authoritative schema
paths and [actions.md](actions.md) for the governance action vocabulary.

---

## Unified Control Identifier (UCID)

A **UCID** is a stable, citable identifier for one normative AI-governance
obligation, independent of any single framework. UCIDs are **pivots**, not
controls: one UCID maps to N regulatory citations, M implementing controls,
and K runtime Beacon receipts. The registry source of truth is
[`crosswalks/unified-control-id.yaml`](../../crosswalks/unified-control-id.yaml);
governance and lifecycle are documented in
[`UCID-REGISTRY.md`](../../UCID-REGISTRY.md).

### Syntax

```
UCID-<DOMAIN>-<TOPIC>-<NNN>
```

| Segment | Rule |
| --- | --- |
| `DOMAIN` | Uppercase token, e.g. `DATA`, `OVERSIGHT`, `LOG`, `SEC`, `SUPPLYCHAIN`. |
| `TOPIC` | Optional uppercase/digit segment(s), e.g. `BIAS`, `ROBUST`, `SBOM`. |
| `NNN` | Three-digit zero-padded sequence within `(DOMAIN, TOPIC)`, starting at `001`. |

Canonical regex used by the test suite:
`^UCID-[A-Z][A-Z0-9]{1,11}(-[A-Z0-9]{1,16})*-[0-9]{3}$`. A UCID id is allocated
**forever** — never reused for a different concept, even after deprecation.

### Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | yes | The UCID. Matches the syntax above; unique across the registry. |
| `title` | string | yes | Human-readable obligation summary. |
| `status` | enum | recommended | `provisional` \| `stable` \| `deprecated` \| `superseded`. |
| `created` | date | recommended | ISO-8601 allocation date. |
| `proposer` | string | recommended | GitHub handle of the proposer. |
| `nist_ai_rmf` | string[] | one-of | NIST AI RMF subcategory citations (e.g. `MEASURE-2.11`). |
| `eu_ai_act` | object | one-of | `{ articles: [...], annex_iv: [...] }`. |
| `iso_42001` | string[] | one-of | ISO/IEC 42001 clause citations (e.g. `A.7.4`). |
| `implementing_controls` | string[] | yes | Control ids that implement this UCID. Each must resolve to a control file. |
| `planned_controls` | string[] | no | Control ids planned but not yet authored (must NOT have a file). |
| `superseded_by` / `split_into` / `merged_into` | string[] | conditional | Lifecycle pointers (see UCID-REGISTRY.md §4). |

> At least one of `nist_ai_rmf` / `eu_ai_act` / `iso_42001` MUST be present — a
> UCID with no framework citation is just a control id and defeats the pivot.
> The unit suite enforces this.

### Example

```yaml
- id: UCID-DATA-BIAS-001
  title: Dataset bias examination
  status: provisional
  created: 2026-04-12
  proposer: bobrapp
  nist_ai_rmf: [MEASURE-2.11, MAP-2.3, MANAGE-2.3]
  eu_ai_act:
    articles: ["10(2)(f)", "10(3)"]
    annex_iv: ["2(d)", "2(g)"]
  iso_42001: ["A.7.4"]
  implementing_controls: [DG-002]
```

---

## Control

A **Control** is the concrete, runnable obligation: it binds to a UCID, maps to
framework citations it `satisfies`, and declares at least one `check`. Controls
live at `domains/<domain>/controls/<ID>_<slug>.yaml`.

### Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `apiVersion` | const | yes | `govops.aigovops.org/v1`. |
| `kind` | const | yes | `Control`. |
| `metadata.id` | string | yes | `^[A-Z]{2,4}-[0-9]{3,6}$`, e.g. `DG-002`. |
| `metadata.ucid` | string | yes | The UCID this control implements; must exist in the registry. |
| `metadata.name` | string | yes | Human-readable control name. |
| `metadata.owner` | string | yes | `@handle`. |
| `metadata.severity` | enum | yes | `low` \| `medium` \| `high` \| `critical`. |
| `metadata.status` | enum | yes | `draft` \| `shadow` \| `enforced` \| `deprecated`. |
| `satisfies` | object | recommended | Framework citation map (`nist_ai_rmf`, `eu_ai_act`, `iso_42001`), ≥ 1 property. |
| `applies_to` | object | no | Scoping: `risk_tier`, `modality`. |
| `inputs` | array | no | Declared input paths (`path`, `required`). |
| `checks` | array | yes (≥ 1) | Runnable checks; each has `id`, `name`, `runner`. |
| `checks[].runner` | enum | yes | `pytest` \| `python` \| `opa` \| `rego` \| `shell` \| `container`. |
| `checks[].evidence_outputs` | array | no | Declared output artifacts (`type`, `path`). |
| `on_fail` | object | no | `action`, `notify`, `open_poam`. |
| `exceptions_allowed_from` | string | no | Path to an exceptions directory. |

### Example

```yaml
apiVersion: govops.aigovops.org/v1
kind: Control
metadata:
  id: DG-002
  ucid: UCID-DATA-BIAS-001
  name: Bias evaluation on training and evaluation datasets
  owner: "@bobrapp"
  severity: high
  status: draft
checks:
  - id: DG-002.C1
    name: Demographic parity ratio within threshold
    runner: pytest
    script: domains/data-governance/checks/bias_metrics_test.py::test_demographic_parity
on_fail:
  action: block_merge
  open_poam: true
```

---

## GovernanceDomain

A **GovernanceDomain** groups related controls and declares domain-level
applicability and SLOs. One `domain.yaml` per `domains/<domain>/`.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `apiVersion` / `kind` | const | yes | `govops.aigovops.org/v1` / `GovernanceDomain`. |
| `metadata.id` | string | yes | `^[a-z][a-z0-9-]+$`, e.g. `data-governance`. |
| `metadata.name` | string | yes | Display name. |
| `metadata.owner` | string | yes | `@handle`. |
| `metadata.description` | string | no | Free text. |
| `risk_tier_applicability` | enum[] | no | Subset of `unacceptable` \| `high` \| `limited` \| `minimal` \| `gpai`. |
| `slos` | array | no | `{ metric, target }` objectives. |

---

## EvidenceBundle

An **EvidenceBundle** is the signed manifest emitted by
`umbrella-conformance bundle`. It records the check matrix and embeds the
Beacon receipts that back each check. It is wrapped in an in-toto Statement v1
/ DSSE envelope and signed via `cosign sign-blob`.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `apiVersion` / `kind` | const | yes | `govops.aigovops.org/v1` / `EvidenceBundle`. |
| `metadata.generatedAt` | date-time | yes | UTC timestamp (`...Z`). |
| `metadata.tool` | string | yes | `umbrella-conformance/<version>`. |
| `metadata.repo` | string | no | Repository name. |
| `metadata.commit_sha` | string | no | `^[0-9a-f]{7,64}$`. |
| `checks[]` | array | yes | One entry per conformance check. |
| `checks[].name` | string | yes | Check name (see [actions.md](actions.md)). |
| `checks[].status` | enum | yes | `pass` \| `warn` \| `fail`. |
| `checks[].details` | string[] | no | Human-readable findings. |
| `checks[].ucid` | string | no | UCID this check evidences (for coverage gating). |
| `checks[].evidence_refs` | string[] | no | Receipt ids backing this result. |
| `receipts[]` | array | no | Embedded Beacon receipts (verbatim). |
| `receipts[].id` | string | yes | Receipt id; matches `evidence_refs[]`. |
| `receipts[].format` | enum | yes | `foundation` \| `runtime`. |
| `receipts[].payload` | object | yes | The signed receipt JSON, **unmutated**. |
| `receipts[].issued_at` | date-time | no | Issuance timestamp for freshness. |

Verifiers MUST re-verify each embedded receipt independently of the outer DSSE
signature (run `beacon-verify`).

---

## PolicyOrchestration (informative)

`policies/orchestration.yaml` is the root orchestration document. It is not yet
schema-enforced but follows a stable shape: `metadata` (name, version,
signing_identity), `defaults`, `scope`, and an ordered list of `phases`
(`ingest → classify → domain-checks → crosswalk → bundle → report`). These
phases map directly to the [flows](flows.md) and the
[actions](actions.md) vocabulary.

## AISystem (informative)

`systems/SYS-*.yaml` describes a governed AI system under evaluation: intended
purpose, EU AI Act risk classification, modalities, protected attributes,
artifacts, and human-oversight mode. Controls scope to systems via
`applies_to`.
