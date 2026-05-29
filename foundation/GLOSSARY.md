# Glossary — AIGovOps program terms

**Scope:** This is the **authoritative** glossary for Umbrella, Beacon, and any AIGovOps Foundation project. When the same word appears in any project's docs, it MUST mean what is written here. PRs that introduce a new term anywhere in the program must update this file in the same PR.

**Maintained by:** AIGovOps Foundation board.

---

## Core identifiers

### Control
A YAML contract under `domains/<domain>/controls/` describing exactly **one** AI-governance requirement and the automated `checks[]` that prove it. Has an id matching `^[A-Z]{2,4}-[0-9]{3}$` (e.g. `DG-002`). Carries a `status` of `draft`, `shadow`, `enforced`, or `deprecated`.

### UCID — Unified Control Identifier
A stable, citable pivot identifier in the form `UCID-<DOMAIN>-<TOPIC>-<NNN>` (e.g. `UCID-DATA-BIAS-001`). A UCID maps one normative obligation to N regulatory citations and M implementing controls. **A UCID is not a control.** See [UCID-REGISTRY.md](../UCID-REGISTRY.md) for the full governance model.

### Framework
A regulator-published normative document — e.g. NIST AI RMF 1.0, EU AI Act (Regulation (EU) 2024/1689), ISO/IEC 42001:2023. Registered in [`frameworks/_registry.yaml`](../frameworks/_registry.yaml) with a pinned version.

### Crosswalk
The mapping from frameworks ↔ UCIDs ↔ controls. Source of truth: [`crosswalks/unified-control-id.yaml`](../crosswalks/unified-control-id.yaml).

---

## Runtime evidence terms

### Receipt
A single Beacon-signed JSON object recording one evidence event. OVERT-pure: contains no `governance` block in the signed payload. Two formats exist:

* **Foundation receipts** — chained audit log entries (`src/audit_log.py`); each entry's hash chains to the previous, genesis literal `"GENESIS"`.
* **Runtime receipts** — single-shot OVERT receipts (`beacons/_common.py`); standalone signed payloads with `signature.alg=ed25519`.

### EvidenceBundle
The Umbrella-emitted artifact (`apiVersion: govops.aigovops.org/v1`, `kind: EvidenceBundle`) produced by `umbrella-conformance bundle`. Conforms to [`conformance/schemas/evidence-bundle.schema.json`](../conformance/schemas/evidence-bundle.schema.json). Contains:

* `metadata` — generation timestamp, tool version
* `checks[]` — each automated control check + its result + `evidence_refs[]` pointing into `receipts[]`
* `receipts[]` — embedded Beacon receipts (verbatim, signed) that back the check results

### evidence_refs[]
Per-check pointers from `EvidenceBundle.checks[].evidence_refs[]` into `EvidenceBundle.receipts[]` by receipt id. This is the **only** place where UCID-to-receipt binding lives — Beacon receipts themselves do not know UCIDs exist.

### DSSE envelope
The signed wrapper around an EvidenceBundle as produced by `cosign sign-blob`. Uses `payloadType: application/vnd.in-toto+json` and `predicateType: https://aigovops.org/attestations/govops-evidence/v1`. The DSSE envelope is what you publish to a transparency log.

---

## Roles

### Designated Expert
The named individual responsible for reviewing additions and changes to a registry (UCID registry, framework registry). Two-year term. Currently Bob Rapp (`@bobrapp`).

### Conformance check
A function listed in `conformance/cli.py:ALL_CHECKS` (currently 6: `schema-valid`, `crosswalk-resolved`, `controls-have-checks`, `evidence-signed`, `slsa-provenance-present`, `overt-predicate-valid`). Runs over the repo and emits one entry into `EvidenceBundle.checks[]`.

---

## Statuses

### Control status
* `draft` — being written, not yet enforced.
* `shadow` — checks run but failures do not block CI.
* `enforced` — failures block CI.
* `deprecated` — replaced; retained for historical bundles.

### UCID status
See [UCID-REGISTRY.md §2](../UCID-REGISTRY.md#2-status-values): `provisional`, `stable`, `deprecated`, `superseded`.

---

## What we deliberately do NOT define here

* **Risk** — too domain-specific. Define locally per control.
* **Compliance** — Umbrella does not assert compliance; it produces signed evidence others use to assess compliance.
* **Audit** — same.
