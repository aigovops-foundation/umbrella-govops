# Schema Catalog

Every machine-readable schema Umbrella-GovOps publishes. All schemas are
**JSON Schema Draft 2020-12** and live under
[`conformance/schemas/`](../../conformance/schemas/). The conformance CLI
(`umbrella-conformance check`) validates on-disk YAML against the matching
schema by its `kind` field.

| Schema | Path | `kind` | Version | Purpose |
| --- | --- | --- | --- | --- |
| Control | [`conformance/schemas/control.schema.json`](../../conformance/schemas/control.schema.json) | `Control` | v1 | A single implementing control: id, UCID binding, framework `satisfies` map, and at least one runnable `check`. |
| Crosswalk | [`conformance/schemas/crosswalk.schema.json`](../../conformance/schemas/crosswalk.schema.json) | `Crosswalk` | v1 | The UCID registry: each UCID pivots one obligation to NIST / EU / ISO citations and implementing controls. |
| GovernanceDomain | [`conformance/schemas/domain.schema.json`](../../conformance/schemas/domain.schema.json) | `GovernanceDomain` | v1 | A domain grouping (data-governance, human-oversight, …): id, owner, risk-tier applicability, SLOs. |
| EvidenceBundle | [`conformance/schemas/evidence-bundle.schema.json`](../../conformance/schemas/evidence-bundle.schema.json) | `EvidenceBundle` | v1 | The signed manifest produced by `umbrella-conformance bundle`: check matrix + embedded Beacon receipts. |

## Identifier patterns

| Identifier | Pattern | Example |
| --- | --- | --- |
| Control id | `^[A-Z]{2,4}-[0-9]{3,6}$` | `DG-002`, `HO-001` |
| UCID (registry / canonical) | `^UCID-[A-Z][A-Z0-9]{1,11}(-[A-Z0-9]{1,16})*-[0-9]{3}$` | `UCID-DATA-BIAS-001` |
| UCID (loose, as enforced by `crosswalk.schema.json`) | `^UCID-[A-Z0-9-]+$` | `UCID-OVERSIGHT-001` |
| Domain id | `^[a-z][a-z0-9-]+$` | `data-governance` |
| Commit SHA (bundle metadata) | `^[0-9a-f]{7,64}$` | `deadbeef` |

> **Note on UCID patterns.** `UCID-REGISTRY.md` §3 documents a strict regex
> whose first segment caps at 8 characters; the shipped `UCID-OVERSIGHT-001`
> uses a 9-character domain token. The test suite's canonical helper
> (`tests/_lib/ucid.py`) widens the first segment to 2–12 characters so it
> matches every real and documented-valid UCID while still rejecting the
> negative examples in the registry doc. See
> [data-model.md § UCID](data-model.md#unified-control-identifier-ucid).

## Schemas that are referenced but live elsewhere

| Schema | Owner | Notes |
| --- | --- | --- |
| SLSA Provenance v1 | [slsa.dev](https://slsa.dev/provenance/v1) | `predicateType` asserted by `slsa-provenance-present`. |
| in-toto Statement v1 | [in-toto.io](https://in-toto.io/Statement/v1) | Outer envelope wrapping an EvidenceBundle for `cosign sign-blob`. |
| OVERT predicate | `overt/umbrella-govops.v1.json` (when present) | Validated by `overt-predicate-valid`; predicate type `https://overt.dev/umbrella-govops/v1`. |
| Beacon receipt | [aigovops-beacon](https://github.com/bobrapp/aigovops-beacon) | Embedded verbatim into `EvidenceBundle.receipts[]`; re-verified with `beacon-verify`. |
