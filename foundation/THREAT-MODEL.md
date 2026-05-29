# AIGovOps Threat Model

**Scope:** what the AIGovOps program — Beacon (the product) and Umbrella (the program layer) — is engineered to prevent. This model is intentionally **narrow**: we model attacks against *the evidence pipeline*, not against the AI systems being governed.

**Status:** Seed v0.1 — to be reviewed at every Umbrella release.

---

## 1. Assets we are protecting

| ID  | Asset                          | Why it matters                                                                 |
|-----|--------------------------------|--------------------------------------------------------------------------------|
| A1  | Beacon signed receipts         | The atomic evidence record. If forgeable or undetectably mutable, nothing built on top is trustworthy. |
| A2  | EvidenceBundle DSSE envelopes  | The auditor-facing artifact that aggregates receipts and check results.        |
| A3  | UCID registry                  | The citation surface regulators and partners rely on. Renaming or silently retiring a UCID breaks downstream attestations. |
| A4  | Framework registry             | Pinned framework versions. Silent revision of a citation poisons every bundle that cited it. |
| A5  | Signing keys                   | Ed25519 private keys for Beacon receipts and the keyless OIDC identity used by `cosign`. |
| A6  | Build provenance               | SLSA / in-toto attestations covering Umbrella CLI builds.                      |

## 2. Adversaries

| ID  | Adversary                | Capability                                                                 |
|-----|--------------------------|----------------------------------------------------------------------------|
| T1  | Insider with repo write  | Can land PRs; can edit framework registry, controls, fixtures.             |
| T2  | Compromised CI runner    | Can run arbitrary code in CI, exfiltrate secrets, sign with the keyless identity. |
| T3  | Network MITM             | Can intercept downloads of receipts/bundles in transit.                    |
| T4  | Auditor-side replay      | Receives a stale bundle and presents it as current.                        |
| T5  | Downstream integrator    | Embeds Beacon but supplies a tampered public key during verification.      |

## 3. Threats (STRIDE-ish, scoped)

### S — Spoofing
* **S1** Forged Beacon receipt with a fabricated key. **Mitigation:** receipts verify against a published, fingerprinted public key (`audit/keys/public-key.pem` / `.beacon-keys/public-key.pem`). Bundles record `key_fingerprint`. Verifiers MUST pin the fingerprint, not the file path.
* **S2** Forged EvidenceBundle. **Mitigation:** DSSE envelope signed via `cosign sign-blob`, anchored in a transparency log (Rekor by default).

### T — Tampering
* **T1** Silent edit of a historical receipt. **Mitigation:** chained audit log (`entry_sha256` linked to previous, genesis `"GENESIS"`); `beacon-verify` re-walks the chain.
* **T2** Silent edit of an embedded receipt inside `EvidenceBundle.receipts[]`. **Mitigation:** verifier re-runs `beacon-verify` over each embedded receipt; the outer DSSE signature does **not** substitute for receipt-level verification.
* **T3** Silent edit of UCID citations. **Mitigation:** UCID registry change procedure (PR + Designated Expert review); `crosswalk-resolved` check fails if a citation points at a framework version no longer in `frameworks/_registry.yaml`.

### R — Repudiation
* **R1** A signer denies producing a receipt. **Mitigation:** keyless OIDC binds the signer identity (workload identity / GitHub OIDC subject) into the certificate that signed the DSSE envelope; Rekor entry timestamps the act.

### I — Information disclosure
**Out of scope for this model.** Receipts and bundles are public artifacts by design. Projects that need confidentiality MUST keep the underlying telemetry private and only publish hashes — that is an application concern, not a Beacon/Umbrella concern.

### D — Denial of service
* **D1** Flood a verifier with an enormous bundle. **Mitigation:** verifier-side size cap (configurable, default 64 MiB) and `--max-receipts` flag on `umbrella-conformance verify`.

### E — Elevation of privilege
* **E1** Compromised CI runner uses keyless identity to sign anything. **Mitigation:** `predicateType` is fixed to `https://aigovops.org/attestations/govops-evidence/v1`; verifiers MUST reject envelopes whose subject does not match the expected repo + workflow.

## 4. Non-goals

* Defending against a *compromised regulator* who publishes a malicious framework version. Out of scope.
* Defending against *application-level* attacks on the AI system being governed (prompt injection, data poisoning at training time). Beacon records evidence about those events; it does not prevent them.
* Defending against an auditor who simply ignores the bundle. Human process problem.

## 5. Trust boundaries (textual)

```
+----------------------+      +----------------------+      +-----------------------+
|  AI system under    |      |  Beacon runtime      |      |  Umbrella program     |
|  test               | ---> |  (signs receipts)    | ---> |  (binds + bundles)    |
+----------------------+      +----------------------+      +-----------------------+
        ^                              ^                              ^
        |                              |                              |
   trust line 1                  trust line 2                  trust line 3
   (telemetry true)              (signing key safe)            (citations true)
```

* **Trust line 1** — Application owner. AIGovOps cannot validate.
* **Trust line 2** — Beacon. Validated by `beacon-verify` against a pinned public key.
* **Trust line 3** — Umbrella. Validated by `umbrella-conformance verify` against the UCID + framework registries pinned at the bundle's commit SHA.

## 6. Open issues

* Sigstore Rekor v2 migration — review by 2026-Q4.
* Key rotation procedure for the keyless OIDC identity if the GitHub OIDC issuer URL changes.
* Long-lived archival proof (TUF, Sigsum) — not addressed in v0.1.
