# Umbrella-GovOps

**A private GitHub repository blueprint for treating AI governance as executable code.**

> Governance is not a PDF. It is a pipeline.
> Every control is a YAML contract, every assertion is a test, every audit is a signed artifact.

---

## 1. Design Premise

`Umbrella-GovOps` is the **control plane** for AI governance across the AIGovOps Foundation portfolio and any downstream enterprise consumer. It encodes obligations from the [NIST AI Risk Management Framework 1.0](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf) (Govern / Map / Measure / Manage) and the [EU AI Act Annex IV technical documentation requirements](https://artificialintelligenceact.eu/annex/4/) as declarative YAML, compiles them into executable checks inside CI/CD, and emits **cryptographically signed, versioned evidence bundles** that satisfy conformity assessment, third-party audit, and post-market monitoring obligations.

The design draws on four established standards so auditors do not need to learn a new vocabulary:

| Layer | Standard | Role in Umbrella-GovOps |
|---|---|---|
| Control catalog | [NIST OSCAL](https://pages.nist.gov/OSCAL/) (Catalog, Profile, SSP, AR, POA&M) | Canonical machine-readable representation of controls and assessment results |
| Policy evaluation | [Open Policy Agent / Rego](https://openpolicyagent.org) | Deterministic policy decisions inside CI gates |
| Artifact attestation | [in-toto](https://docs.sigstore.dev/cosign/verifying/attestation/) + [SLSA provenance](https://www.legitsecurity.com/blog/slsa-provenance-blog-series-part-2-deeper-dive-into-slsa-provenance) | Tamper-evident link between source, build, and evidence |
| Signing | [Sigstore (Cosign + Fulcio + Rekor)](https://sbomify.com/2024/08/12/what-is-sigstore/) and [OpenSSF Model Signing (OMS)](https://openssf.org/blog/2025/06/25/an-introduction-to-the-openssf-model-signing-oms-specification/) | Keyless, identity-bound signatures with public transparency log |

---

## 2. Repository Folder Structure

```
umbrella-govops/
├── README.md
├── LICENSE                                    # Apache-2.0 for code; CC-BY-4.0 for docs
├── CODEOWNERS                                 # Governance domain owners gate every change
├── SECURITY.md                                # Disclosure, key rotation, Rekor identities
├── .github/
│   ├── workflows/
│   │   ├── govops-ci.yml                      # Master orchestrator (see §6)
│   │   ├── evidence-bundle.yml                # Builds, signs, publishes evidence
│   │   ├── drift-detection.yml                # Nightly: prod state vs. declared policy
│   │   ├── post-market-monitoring.yml         # EU AI Act Art. 72 telemetry sweep
│   │   └── framework-sync.yml                 # Pulls upstream NIST/EU updates
│   ├── CODEOWNERS
│   └── pull_request_template.md               # Forces governance impact declaration
│
├── frameworks/                                # Upstream source-of-truth (read-mostly)
│   ├── nist-ai-rmf-1.0/
│   │   ├── catalog.oscal.yaml                 # OSCAL catalog of GOVERN/MAP/MEASURE/MANAGE
│   │   ├── playbook-actions.yaml              # NIST AIRC Playbook suggested actions
│   │   └── crosswalk.iso42001.yaml
│   ├── eu-ai-act/
│   │   ├── annex-iii-high-risk.yaml           # Use-case classification rules
│   │   ├── annex-iv-tech-doc.oscal.yaml       # 9 sections of technical documentation
│   │   ├── chapter-iii-section-2.yaml         # Articles 9–15 (risk mgmt, data, logging,
│   │   │                                      #   transparency, oversight, accuracy/sec.)
│   │   └── gpai-code-of-practice.yaml         # GPAI / systemic-risk obligations
│   ├── iso-42001/
│   └── _schemas/                              # JSON Schemas every framework file validates against
│       ├── control.schema.json
│       └── requirement.schema.json
│
├── domains/                                   # ← The heart of the repo
│   ├── _domain.schema.yaml                    # Schema every domain manifest must satisfy
│   ├── data-governance/
│   │   ├── domain.yaml                        # Owner, scope, risk tier, SLOs
│   │   ├── controls/
│   │   │   ├── DG-001_dataset-provenance.yaml
│   │   │   ├── DG-002_bias-evaluation.yaml
│   │   │   └── DG-003_pii-minimization.yaml
│   │   ├── checks/                            # Executable test scripts (Python/Bash/Rego)
│   │   │   ├── dataset_provenance_test.py
│   │   │   ├── bias_metrics_test.py
│   │   │   └── pii_scan.rego
│   │   └── evidence-templates/
│   ├── model-lifecycle/                       # Training, eval, model cards, signing
│   ├── human-oversight/                       # EU AI Act Art. 14
│   ├── transparency-disclosure/               # Art. 13, watermarking, user notice
│   ├── security-robustness/                   # Art. 15, adversarial, red-team
│   ├── logging-traceability/                  # Art. 12 automatic event logs
│   ├── risk-management-system/                # Art. 9, NIST MANAGE
│   ├── post-market-monitoring/                # Art. 72
│   ├── incident-response/                     # Serious incident reporting (Art. 73)
│   └── third-party-and-supply-chain/          # GPAI providers, SBOM, model signing
│
├── policies/                                  # Compiled enforcement layer
│   ├── orchestration.yaml                     # Top-level policy graph (see §3)
│   ├── rego/
│   │   ├── ci_gate.rego                       # allow/deny decisions in CI
│   │   ├── deployment_gate.rego               # Kubernetes admission / release gate
│   │   └── data_classification.rego
│   ├── conftest/                              # Conftest test suites for Rego
│   └── exceptions/
│       ├── _exception.schema.yaml
│       └── EXC-2026-014_legacy-retraining.yaml   # Time-boxed, signed waivers
│
├── crosswalks/                                # Many-to-many requirement maps
│   ├── nist-to-eu.yaml                        # NIST subcategory → EU Article
│   ├── eu-to-nist.yaml
│   ├── nist-to-iso42001.yaml
│   └── unified-control-id.yaml                # Internal UCID master mapping
│
├── evidence/                                  # Generated artifacts; immutable
│   ├── bundles/
│   │   └── 2026-Q2/
│   │       ├── bundle-v2026.05.29-1430.tar.zst
│   │       ├── bundle-v2026.05.29-1430.intoto.jsonl
│   │       └── bundle-v2026.05.29-1430.sig
│   ├── manifests/
│   │   └── bundle-v2026.05.29-1430.manifest.yaml
│   └── transparency-log-receipts/             # Rekor inclusion proofs
│
├── reports/                                   # Human-readable outputs
│   ├── conformity-assessment/                 # EU AI Act Art. 47 declarations
│   ├── nist-rmf-profile/                      # GOVERN/MAP/MEASURE/MANAGE status
│   ├── cross-framework-heatmap/               # Per-system, per-framework coverage
│   └── post-market-monitoring/
│
├── systems/                                   # Per-AI-system inventory (the registry)
│   ├── _system.schema.yaml
│   ├── SYS-001_clinical-triage-assistant.yaml
│   ├── SYS-002_credit-decisioning-llm.yaml
│   └── SYS-003_fencing-judging-cv.yaml
│
├── tools/                                     # CLI and engine
│   ├── govops/                                # Python package: `pip install -e .`
│   │   ├── orchestrator.py                    # Parses orchestration.yaml, runs graph
│   │   ├── compiler.py                        # YAML controls → Rego + pytest plans
│   │   ├── evaluator.py                       # Runs checks, collects results
│   │   ├── attestor.py                        # Builds in-toto statement, calls cosign
│   │   ├── crosswalk.py                       # Resolves UCID across frameworks
│   │   └── reporters/
│   │       ├── oscal_ar.py                    # Emits OSCAL Assessment Results
│   │       ├── annex_iv_pdf.py
│   │       └── heatmap_html.py
│   └── scripts/
│       ├── verify-bundle.sh                   # cosign verify-attestation + rekor lookup
│       └── rotate-keys.sh
│
├── tests/                                     # Self-tests of the governance engine
│   ├── unit/
│   ├── integration/
│   └── golden-bundles/                        # Known-good signed bundles for regression
│
└── docs/
    ├── architecture.md
    ├── threat-model.md
    ├── auditor-guide.md
    └── adr/                                   # Architecture Decision Records
```

---

## 3. The YAML Policy Orchestration Layer

The orchestration layer is a **directed acyclic graph** of policy evaluations, declared in `policies/orchestration.yaml`. Every node is a *control*, every edge is a *dependency*, and every leaf produces signed evidence.

### 3.1 Top-level orchestration manifest

```yaml
# policies/orchestration.yaml
apiVersion: govops.aigovops.org/v1
kind: PolicyOrchestration
metadata:
  name: umbrella-govops-root
  version: 2026.05.29
  signing_identity: https://github.com/aigovops/umbrella-govops/.github/workflows/evidence-bundle.yml@refs/heads/main

defaults:
  evidence_retention: P7Y           # EU AI Act Art. 18: 10y for providers; we use 7y min
  severity_on_fail: blocking
  evidence_format: in-toto-v1.0

# Which AI systems this orchestration applies to (glob over systems/)
scope:
  systems: ["SYS-*"]
  exclude_risk_tier: ["prohibited"]

# Ordered phases — each phase is a CI stage
phases:
  - id: ingest
    description: Load framework catalogs and validate schemas
    runs:
      - frameworks/nist-ai-rmf-1.0/catalog.oscal.yaml
      - frameworks/eu-ai-act/annex-iv-tech-doc.oscal.yaml

  - id: classify
    description: Determine EU AI Act risk tier per system
    depends_on: [ingest]
    runs:
      - domains/risk-management-system/controls/RMS-001_risk-tier-classification.yaml

  - id: domain-checks
    description: Run all domain controls in parallel
    depends_on: [classify]
    parallel: true
    runs:
      - domains/data-governance/**
      - domains/model-lifecycle/**
      - domains/human-oversight/**
      - domains/transparency-disclosure/**
      - domains/security-robustness/**
      - domains/logging-traceability/**

  - id: crosswalk
    description: Resolve every result to NIST + EU + ISO IDs
    depends_on: [domain-checks]
    runs:
      - crosswalks/unified-control-id.yaml

  - id: bundle
    description: Build, sign, log, publish evidence bundle
    depends_on: [crosswalk]
    runs:
      - tools/govops/attestor.py

  - id: report
    description: Render conformity + RMF profile + heatmap
    depends_on: [bundle]
    runs:
      - tools/govops/reporters/oscal_ar.py
      - tools/govops/reporters/annex_iv_pdf.py
      - tools/govops/reporters/heatmap_html.py
```

### 3.2 Control definition schema (every YAML in `domains/*/controls/`)

```yaml
# domains/data-governance/controls/DG-002_bias-evaluation.yaml
apiVersion: govops.aigovops.org/v1
kind: Control
metadata:
  id: DG-002
  ucid: UCID-DATA-BIAS-001            # Stable internal ID; crosswalk pivot
  name: Bias evaluation on training and evaluation datasets
  owner: "@aigovops/data-governance-wg"
  severity: high
  status: enforced                    # draft | shadow | enforced

# Which framework obligations this control satisfies
satisfies:
  nist_ai_rmf:
    - subcategory: MEASURE-2.11       # Fairness and bias evaluations
      coverage: full
    - subcategory: MAP-2.3
      coverage: partial
  eu_ai_act:
    - article: "10(2)(f)"             # Data governance — examination of biases
      coverage: full
    - article: "10(3)"
      annex_iv_section: "2(d)"
      coverage: full
  iso_42001:
    - clause: "A.7.4"

# Applicability — only fires for systems matching this selector
applies_to:
  risk_tier: ["high", "limited"]
  modality: ["tabular", "vision", "nlp"]

# Inputs the control needs from the system manifest
inputs:
  - path: artifacts.training_dataset.uri
    required: true
  - path: artifacts.model.uri
    required: true
  - path: protected_attributes
    required: true

# How we PROVE compliance — the executable check(s)
checks:
  - id: DG-002.C1
    name: Demographic parity ratio within threshold
    runner: pytest
    script: domains/data-governance/checks/bias_metrics_test.py::test_demographic_parity
    parameters:
      threshold_min: 0.80
      threshold_max: 1.25
    evidence_outputs:
      - type: metric-report
        path: out/bias/dp_ratio.json
      - type: sbom-fragment
        path: out/bias/sbom.cdx.json

  - id: DG-002.C2
    name: Disparate impact statistical test
    runner: python
    script: domains/data-governance/checks/bias_metrics_test.py::test_disparate_impact
    evidence_outputs:
      - type: metric-report
        path: out/bias/di.json

  - id: DG-002.C3
    name: OPA policy — no protected attributes used as direct features
    runner: opa
    script: domains/data-governance/checks/pii_scan.rego
    query: data.govops.data.no_direct_protected_features
    evidence_outputs:
      - type: opa-decision
        path: out/bias/opa_decision.json

# Failure handling
on_fail:
  action: block_merge
  notify: ["#govops-alerts", "[email protected]"]
  open_poam: true                     # Auto-creates POA&M entry in OSCAL format

# Exceptions (waivers) must reference a signed exception YAML
exceptions_allowed_from: policies/exceptions/
```

### 3.3 Exception (waiver) schema — time-boxed and signed

```yaml
# policies/exceptions/EXC-2026-014_legacy-retraining.yaml
apiVersion: govops.aigovops.org/v1
kind: Exception
metadata:
  id: EXC-2026-014
  control_id: DG-002
  system_id: SYS-002
  reason: |
    Legacy credit model under retraining migration; bias evaluation runs
    on shadow pipeline only until 2026-08-31.
  granted_by: "[email protected]"
  approved_by: ["@cto", "@chief-ai-risk-officer"]
  effective: 2026-05-15
  expires: 2026-08-31                 # Hard expiry; pipeline re-blocks automatically
  compensating_controls: [DG-002.C2]
signature:
  type: sigstore-bundle
  ref: evidence/exceptions/EXC-2026-014.sig
```

---

## 4. Mapping Framework Requirements to Automated Checks

Each control's `satisfies:` block creates a many-to-many mapping resolved at compile time. The **Unified Control ID (UCID)** layer in `crosswalks/unified-control-id.yaml` is the pivot:

```yaml
# crosswalks/unified-control-id.yaml (excerpt)
ucids:
  - id: UCID-DATA-BIAS-001
    title: Dataset bias examination
    nist_ai_rmf: [MEASURE-2.11, MAP-2.3, MANAGE-2.3]
    eu_ai_act:
      articles: ["10(2)(f)", "10(3)"]
      annex_iv: ["2(d)", "2(g)"]
    iso_42001: ["A.7.4"]
    implementing_controls: [DG-002]

  - id: UCID-OVERSIGHT-001
    title: Human oversight measures
    nist_ai_rmf: [GOVERN-3.2, MANAGE-2.4]
    eu_ai_act:
      articles: ["14"]
      annex_iv: ["2(e)", "3"]
    implementing_controls: [HO-001, HO-002, HO-003]

  - id: UCID-LOG-001
    title: Automatic logging of events
    nist_ai_rmf: [MEASURE-2.8, MANAGE-4.1]
    eu_ai_act:
      articles: ["12", "19"]
    implementing_controls: [LOG-001, LOG-002]
```

The compiler (`tools/govops/compiler.py`) walks all `domains/**/controls/*.yaml`, resolves UCIDs, and produces:

1. A **test plan** (`out/plan.json`) listing every check that must run for the current PR's scope.
2. A **Rego policy bundle** (`out/policies.tar.gz`) consumable by OPA in CI and by Kubernetes admission controllers in prod.
3. A **coverage matrix** (`out/coverage.yaml`) — every NIST subcategory and every EU AI Act article shown as `covered | partial | gap | n/a` per system.

Gaps automatically open Plan of Action and Milestones (POA&M) entries in OSCAL format.

---

## 5. Cross-Framework Compliance Reporting

Three primary report artifacts, all generated from the same evidence corpus:

### 5.1 NIST AI RMF Profile (`reports/nist-rmf-profile/`)
OSCAL `assessment-results` document covering Govern, Map, Measure, Manage. Subcategory rollups with trend deltas vs. prior quarter.

### 5.2 EU AI Act Conformity Pack (`reports/conformity-assessment/`)
Renders Annex IV technical documentation (9 sections) plus a draft EU Declaration of Conformity per [Article 47](https://artificialintelligenceact.eu/article/6/). Includes signed Annex IV PDF, machine-readable OSCAL SSP, and post-market monitoring plan stub.

### 5.3 Cross-framework heatmap (`reports/cross-framework-heatmap/`)
Single-page HTML matrix: rows = AI systems in `systems/`, columns = unified control IDs grouped by framework. Cells link to the signed evidence bundle line that satisfies the cell. Auditors can navigate from any cell to a Rekor transparency-log entry in two clicks.

---

## 6. CI/CD Integration

### 6.1 Pipeline topology (`.github/workflows/govops-ci.yml`)

```yaml
name: govops-ci
on:
  pull_request:
    paths: ['domains/**', 'policies/**', 'systems/**', 'frameworks/**']
  push:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'   # Nightly drift detection

permissions:
  id-token: write         # OIDC for Sigstore keyless signing
  contents: read
  attestations: write     # GitHub artifact attestations
  packages: write

jobs:
  validate-schemas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e tools/govops
      - run: govops validate --strict

  compile-policies:
    needs: validate-schemas
    steps:
      - run: govops compile --out ./out
      - uses: actions/upload-artifact@v4
        with: { name: policy-bundle, path: out/policies.tar.gz }

  run-checks:
    needs: compile-policies
    strategy:
      matrix:
        domain: [data-governance, model-lifecycle, human-oversight,
                 transparency-disclosure, security-robustness,
                 logging-traceability, risk-management-system]
    steps:
      - run: govops run --domain ${{ matrix.domain }} --out ./results/${{ matrix.domain }}
      - uses: actions/upload-artifact@v4
        with: { name: results-${{ matrix.domain }}, path: results/ }

  build-evidence-bundle:
    needs: run-checks
    steps:
      - uses: actions/download-artifact@v4
      - name: Assemble bundle
        run: govops bundle --in ./results --out evidence/bundles/${{ github.run_id }}
      - name: Generate SLSA provenance + in-toto statement
        run: govops attest --bundle evidence/bundles/${{ github.run_id }}
      - name: Keyless sign with Sigstore (Cosign + Fulcio + Rekor)
        run: |
          cosign sign-blob --yes \
            --bundle evidence/bundles/${{ github.run_id }}.sig.bundle \
            evidence/bundles/${{ github.run_id }}/bundle.tar.zst
      - name: GitHub artifact attestation
        uses: actions/attest-build-provenance@v1
        with:
          subject-path: 'evidence/bundles/${{ github.run_id }}/bundle.tar.zst'

  gate:
    needs: build-evidence-bundle
    steps:
      - name: OPA policy gate
        run: |
          opa eval --bundle out/policies.tar.gz \
            --input results/aggregate.json \
            --fail-defined 'data.govops.ci_gate.deny[_]'
```

### 6.2 Evidence bundle layout

Each bundle is a **deterministic tarball** containing:

```
bundle-v2026.05.29-1430/
├── manifest.yaml                    # Bundle index — hashes of every file below
├── plan.json                        # Which checks ran, against which systems
├── results/                         # Raw outputs from every check
│   ├── DG-002.C1/dp_ratio.json
│   └── ...
├── oscal/
│   ├── assessment-results.yaml      # OSCAL AR model
│   ├── ssp.yaml                     # OSCAL System Security Plan
│   └── poam.yaml                    # OSCAL POA&M for gaps
├── annex-iv/
│   └── technical-documentation.pdf  # Annex IV §1–9 rendered
├── sbom/
│   ├── source.cdx.json              # CycloneDX SBOM of repo state
│   └── models.oms.json              # OpenSSF Model Signing manifest
└── meta/
    ├── git.commit.txt
    ├── git.tree.txt
    └── builder.workflow-ref.txt
```

Alongside the tarball, the pipeline emits:

- `bundle.tar.zst.sig` — Sigstore detached signature
- `bundle.intoto.jsonl` — [in-toto attestation](https://docs.sigstore.dev/cosign/verifying/attestation/) with predicate type `https://aigovops.org/attestations/govops-evidence/v1`
- `bundle.slsa.jsonl` — SLSA provenance predicate
- `rekor-receipt.json` — public transparency-log inclusion proof

### 6.3 Verification (one command for auditors)

```bash
tools/scripts/verify-bundle.sh evidence/bundles/2026-Q2/bundle-v2026.05.29-1430

# Internally:
cosign verify-attestation \
  --type https://aigovops.org/attestations/govops-evidence/v1 \
  --certificate-identity-regexp "https://github.com/aigovops/umbrella-govops/.+" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  bundle.tar.zst
```

Identity-bound, keyless verification — no long-lived secrets to rotate, full chain to a [Rekor](https://sbomify.com/2024/08/12/what-is-sigstore/) transparency-log entry that proves *when* the bundle was produced and *which workflow run* produced it.

---

## 7. The In-toto Attestation Predicate

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    { "name": "bundle.tar.zst",
      "digest": { "sha256": "9f3a…" } }
  ],
  "predicateType": "https://aigovops.org/attestations/govops-evidence/v1",
  "predicate": {
    "bundleVersion": "2026.05.29-1430",
    "orchestration": {
      "repo": "aigovops/umbrella-govops",
      "commit": "c4f1d2…",
      "workflowRef": ".github/workflows/govops-ci.yml@refs/heads/main"
    },
    "scope": {
      "systems": ["SYS-001", "SYS-002", "SYS-003"]
    },
    "frameworks": [
      { "id": "nist-ai-rmf-1.0", "catalogHash": "sha256:7a1b…" },
      { "id": "eu-ai-act",        "catalogHash": "sha256:33ec…" }
    ],
    "results": {
      "controlsEvaluated": 147,
      "passed": 144,
      "failed": 0,
      "waived": 3,
      "coverage": { "nist_subcategories": 0.94, "eu_articles": 0.91 }
    },
    "sbom":   { "ref": "sbom/source.cdx.json",  "digest": "sha256:…" },
    "models": { "ref": "sbom/models.oms.json",  "digest": "sha256:…" }
  }
}
```

This single predicate is what an auditor, a customer security review, or a notified body actually consumes — every numeric claim is reproducible from the signed bundle.

---

## 8. Governance Lifecycle Hooks

| Event | Trigger | Outcome |
|---|---|---|
| New AI system onboarded | New file in `systems/` | Risk classification runs; orchestration scopes expand |
| Framework update (e.g., NIST AI RMF 1.1) | `framework-sync.yml` cron | PR opened with diff in `frameworks/`; CODEOWNERS review required |
| Control change | PR touches `domains/**/controls/*.yaml` | Shadow run for 7 days before `status: enforced` |
| Production drift detected | Nightly `drift-detection.yml` | Issue auto-opened, POA&M entry created |
| Serious incident (EU AI Act Art. 73) | Webhook from runtime monitor | `incident-response` domain workflow assembles signed disclosure package |
| Quarterly audit | Manual `workflow_dispatch` | Conformity pack + RMF profile + heatmap regenerated and signed |

---

## 9. Threat Model Summary

The control plane is itself a high-value target. Mitigations encoded in the repo:

- **Branch protection + CODEOWNERS** on `frameworks/`, `policies/`, `crosswalks/` — no single-actor merges.
- **Keyless signing only** — no long-lived keys to exfiltrate; identity bound to workflow ref ([Sigstore design](https://sbomify.com/2024/08/12/what-is-sigstore/)).
- **Transparency-log dependence** — every bundle's existence is publicly auditable in Rekor, defeating silent backdated evidence.
- **Reproducible builds** — deterministic tarball ordering and pinned tool versions; auditors can rebuild and bit-compare.
- **Exception expiry** — waivers are time-boxed in YAML; no perpetual "we'll fix it later."
- **OSCAL POA&M as a first-class output** — gaps cannot be hidden; they are versioned alongside passes.

---

## 10. Roadmap (suggested first four sprints)

1. **Sprint 1** — Schemas + `domains/_domain.schema.yaml`, ingestion of NIST AI RMF catalog as OSCAL, three reference controls in `data-governance`.
2. **Sprint 2** — Annex IV ingestion, UCID crosswalk, compiler MVP, first signed bundle in CI.
3. **Sprint 3** — All ten governance domains stubbed with at least one enforced control each; conformity pack renderer.
4. **Sprint 4** — Drift detection, post-market monitoring webhook, auditor verification CLI, public sample bundle for the AIGovOps Foundation reference deployment.

---

## 11. Why This Design Holds Up Under Audit

- Every claim in a report ties back, via cryptographic hash, to a specific check execution recorded in a public transparency log.
- Every check ties back, via UCID, to a specific NIST subcategory *and* EU AI Act article — no framework is privileged.
- Every waiver expires automatically; the system cannot quietly accumulate technical-governance debt.
- Every framework update is a reviewable PR, not a Word-document email — auditors see exactly when obligations changed and how the org responded.

Governance, as code, with receipts.
