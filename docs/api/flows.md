# Flows

End-to-end sequence diagrams for the Umbrella-GovOps lifecycle, from policy
authoring through signed evidence to consumption by the companion products
(Beacon at runtime, Lantern for rendering). Diagrams use
[Mermaid](https://mermaid.js.org/); GitHub renders them inline.

Action verbs used below are defined in [actions.md](actions.md); artifact
shapes in [data-model.md](data-model.md).

---

## 1. Authoring → compile → validate → sign → attest → bundle

The core pipeline that turns hand-authored controls into a signed
`EvidenceBundle`.

```mermaid
sequenceDiagram
    autonumber
    actor Author as Control Author
    participant Repo as umbrella-govops repo
    participant CLI as umbrella-conformance
    participant Schema as JSON Schemas
    participant Cosign as cosign / Fulcio
    participant Rekor as Rekor (transparency log)

    Author->>Repo: PR adds Control + UCID row
    Repo->>CLI: govops-ci: validate-schemas
    CLI->>Schema: validate(kind → schema)
    Schema-->>CLI: schema-valid: pass
    CLI->>CLI: crosswalk-resolved (UCID ↔ control)
    CLI->>CLI: controls-have-checks
    Note over CLI: compile controls → Rego + test plan
    CLI->>CLI: run domain checks → pass/warn/fail
    CLI->>CLI: bundle.assembled (manifest + DSSE envelope)
    CLI->>Cosign: bundle.signed (sign-blob)
    Cosign->>Rekor: bundle.anchored (inclusion proof)
    Rekor-->>CLI: log index + uuid
    CLI-->>Repo: EvidenceBundle + .sig + .pem (attestation.published)
```

---

## 2. Receipt creation → binding → coverage gate

How runtime Beacon receipts become evidence bound to UCIDs.

```mermaid
sequenceDiagram
    autonumber
    participant Beacon as Beacon (runtime)
    participant Bundle as umbrella-conformance bundle
    participant Manifest as EvidenceBundle
    participant Verify as umbrella-conformance verify

    Beacon->>Beacon: inference.observed / admission.allowed
    Beacon-->>Bundle: signed receipts (JSONL or dir)
    Bundle->>Manifest: embed receipts[] verbatim
    Bundle->>Manifest: checks[].evidence_refs[] = receipt ids
    Manifest-->>Verify: verify --beacon-bundle --ucid-coverage
    Verify->>Beacon: beacon-verify (re-verify each receipt)
    alt enforced control missing a receipt
        Verify-->>Verify: gate.failed (exit 3 — coverage gap)
    else all enforced controls backed
        Verify-->>Verify: UCID coverage OK (exit 0)
    end
```

---

## 3. Consumption by Beacon and rendering by Lantern

Downstream consumption of the published contracts and bundles.

```mermaid
sequenceDiagram
    autonumber
    participant Umbrella as umbrella-govops
    participant Beacon as Beacon agent
    participant Lantern as Lantern (renderer)
    actor Auditor

    Umbrella-->>Beacon: published UCID registry + control schemas
    Beacon->>Beacon: bind runtime events to UCIDs
    Beacon-->>Umbrella: receipts for the next EvidenceBundle
    Umbrella-->>Lantern: signed EvidenceBundle + crosswalk
    Lantern->>Lantern: render conformity assessment / heatmap
    Lantern-->>Auditor: human-readable, verifiable view
    Auditor->>Umbrella: verify bundle (cosign + beacon-verify)
```

---

## 4. UCID lifecycle (registry state machine)

```mermaid
stateDiagram-v2
    [*] --> provisional: new UCID PR
    provisional --> stable: ≥1 enforced control + expert sign-off
    provisional --> [*]: withdraw (id retired)
    stable --> deprecated: deprecation rationale
    stable --> superseded: replacement registered (superseded_by)
    deprecated --> [*]: retained for historical bundles
    superseded --> [*]: retained for historical bundles
```

---

## 5. CI gate flow (govops-ci + harness)

```mermaid
flowchart TD
    A[PR opened] --> B[govops-ci: conformance + SDK]
    A --> H[harness: unit / chaos / e2e]
    B --> C[validate-schemas]
    C --> D[compile-policies]
    D --> E[run-checks matrix]
    E --> F[build-evidence-bundle: sign + attest]
    F --> G[OPA policy gate]
    H --> I[harness-summary]
    G --> J{all green?}
    I --> J
    J -- yes --> K[merge allowed]
    J -- no --> L[gate.failed → block_merge]
    M[[weekly cron / dispatch]] --> N[scale jobs: 1k + 10k]
```
