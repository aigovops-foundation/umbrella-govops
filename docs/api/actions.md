# Actions Reference

The governance **action vocabulary** Umbrella-GovOps recognizes. An *action* is
a named, observable step in the policy-as-code lifecycle. Actions are the
verbs that appear in orchestration phases, in conformance check results, and —
at runtime — in the Beacon receipts that an `EvidenceBundle` embeds.

Umbrella itself is the **compiler / rules engine**; the runtime verbs
(`inference.observed`, `admission.allowed/denied`) are emitted by
[Beacon](https://github.com/bobrapp/aigovops-beacon) and *consumed* here as
evidence. This reference documents both sides so downstream projects share one
vocabulary.

Naming convention: `subject.verb` in past tense for observed facts
(`bundle.signed`), present/imperative for orchestration phases (`compile`).

---

## 1. Pipeline actions (orchestration phases)

These mirror `policies/orchestration.yaml` → `phases[]` and the
[flows](flows.md). Each runs in order; `depends_on` enforces the DAG.

| Action | Phase id | Semantics | Required inputs | Downstream effect |
| --- | --- | --- | --- | --- |
| `ingest` | `ingest` | Load framework catalogs and validate their schemas. | `frameworks/**` OSCAL catalogs | Catalogs available to `classify`. |
| `classify` | `classify` | Determine EU AI Act risk tier per system. | `systems/SYS-*.yaml` | Risk tier annotated; gates domain scope. |
| `compile` | (CLI) | Compile controls → Rego + executable test plan. | `domains/**/controls/*.yaml` | `out/plan.json` policy bundle. |
| `validate` | `crosswalk` (partial) | Validate every artifact against its JSON Schema. | all YAML | `schema-valid` result. |
| `domain-checks` | `domain-checks` | Run all domain controls (parallel). | controls + their `checks[]` | Per-control pass/warn/fail. |
| `crosswalk` | `crosswalk` | Resolve every result to NIST + EU + ISO ids. | `crosswalks/unified-control-id.yaml` | `crosswalk-resolved` result. |
| `bundle` | `bundle` | Build, sign, log, publish the evidence bundle. | check results + receipts | `EvidenceBundle` + DSSE envelope. |
| `report` | `report` | Render conformity assessment, RMF profile, heatmap. | signed bundle | OSCAL AR / Annex IV PDF / heatmap HTML. |

---

## 2. Conformance check actions

Each is a pure `Path -> CheckResult` function in
[`conformance/checks/`](../../conformance/checks/). Result `status` is one of
`pass` / `warn` / `fail`.

| Action (check name) | Semantics | Trips `fail` when… | Trips `warn` when… |
| --- | --- | --- | --- |
| `schema-valid` | Validate every known-`kind` YAML against its JSON Schema. | Any YAML is invalid or violates its schema. | No YAML matched a known kind. |
| `crosswalk-resolved` | Every control UCID exists in the registry; every implementing control resolves to a file. | Orphan UCID or dangling implementing control. | Registry file absent. |
| `controls-have-checks` | Every control declares ≥ 1 runnable check with a valid runner. | A control has no checks or an unknown runner. | No controls found. |
| `evidence-signed` | Each evidence bundle has a manifest + signature. | Missing `manifest.json` / `signature.json`. | No bundles yet. |
| `slsa-provenance-present` | Each release has SLSA v1 provenance. | Missing/invalid `provenance.json`. | No releases yet. |
| `overt-predicate-valid` | The OVERT predicate is present and well-formed. | Bad predicate type or missing required key. | Predicate not registered. |

---

## 3. Evidence + signing actions (observed facts)

Emitted during `bundle` and recorded in the `EvidenceBundle` / DSSE envelope.

| Action | Semantics | Required fields | Crosswalk target |
| --- | --- | --- | --- |
| `gate.evaluated` | A policy gate ran against aggregated results. | `gate_id`, `decision`, `inputs_digest` | UCID(s) the gate enforces. |
| `gate.failed` | A gate produced a blocking deny. | `gate_id`, `reasons[]` | UCID(s) with unmet evidence. |
| `bundle.assembled` | Manifest + DSSE envelope written. | `bundle_sha256`, `tool`, `commit_sha` | n/a (covers all checks). |
| `bundle.signed` | `cosign sign-blob` produced `.sig` + `.pem`. | `bundle_sha256`, `certificate`, `signature` | n/a. |
| `bundle.anchored` | Signature anchored in a transparency log (Rekor). | `rekor_log_index`, `rekor_uuid` | n/a. |
| `attestation.published` | SLSA / in-toto attestation published for the subject. | `predicateType`, `subject.digest.sha256` | n/a. |

> Field shapes for `bundle.*` follow `EvidenceBundle` metadata; see
> [data-model.md § EvidenceBundle](data-model.md#evidencebundle).

### Example — `bundle.signed`

```json
{
  "action": "bundle.signed",
  "bundle_sha256": "9f3a…",
  "certificate": "-----BEGIN CERTIFICATE-----\n…",
  "signature": "MEUCIQ…",
  "issued_at": "2026-05-29T00:00:00Z"
}
```

---

## 4. Runtime actions (consumed from Beacon)

Umbrella does not emit these — it embeds the receipts that carry them into
`EvidenceBundle.receipts[]` and binds them to checks via `evidence_refs`.

| Action | Origin | Semantics | Required fields | Crosswalk target |
| --- | --- | --- | --- | --- |
| `admission.allowed` | Beacon admission gate | A request was permitted to reach a model. | `subject`, `policy_id`, `decision` | UCID for the admission control. |
| `admission.denied` | Beacon admission gate | A request was blocked by policy. | `subject`, `policy_id`, `reasons[]` | UCID for the admission control. |
| `inference.observed` | Beacon runtime | An inference event was recorded. | `model`, `inputs_digest`, `ts` | UCID(s) for logging/traceability. |
| `trust_tier_change` | Beacon inventory | A model's trust tier changed. | `inventory_id`, `new_tier` | UCID for oversight/lifecycle. |

A receipt is embedded verbatim; its `id` becomes a member of
`checks[].evidence_refs[]`, and `umbrella-conformance verify --ucid-coverage`
fails if an enforced control with `beacon: required` has no backing receipt.

---

## 5. Action → status mapping

| Lifecycle outcome | EvidenceBundle `checks[].status` | Gate effect |
| --- | --- | --- |
| Obligation met with evidence | `pass` | allow |
| Obligation not applicable / no evidence yet | `warn` | allow (advisory) |
| Obligation unmet or artifact broken | `fail` | `gate.failed` → block_merge |
