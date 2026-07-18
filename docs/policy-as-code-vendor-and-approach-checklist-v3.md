# Policy-as-Code: Vendor and Approach Checklist — v.3

**Maintainer:** AiGovOps Foundation (501c3) — [umbrella-govops](https://github.com/bobrapp/umbrella-govops)
**Companion runtime product:** [AiGovOps Beacon](https://github.com/bobrapp/aigovops-beacon)
**Status:** v.3 — 2026-06-01. Supersedes v.2 (2026-Q1).
**Audience:** AI/ML platform leads, GRC architects, procurement, and notified-body assessors evaluating "Policy-as-Code" (PaC) offerings for AI governance.

> Use this checklist before signing a Policy-as-Code contract, adopting an internal framework, or letting a vendor sticker your AI system as "compliant." A vendor that cannot produce signed runtime evidence is selling you a slideshow.

---

## What changed in v.3

Compared with the v.2 checklist that emphasized control coverage and crosswalk tables, v.3 reflects the **Beacon ↔ Umbrella split** ratified by the Foundation:

| Area | v.2 emphasis | v.3 emphasis |
|---|---|---|
| Identifiers | Vendor's proprietary control IDs | [Unified Control Identifiers (UCIDs)](../UCID-REGISTRY.md) — IANA-style governance |
| Evidence | Documentation + screenshots | Signed runtime receipts (OVERT-pure, Ed25519) bound to UCIDs |
| Bundles | PDF reports | DSSE / in-toto Statement v1 envelopes (`predicateType: https://aigovops.org/attestations/govops-evidence/v1`) |
| Verification | Vendor portal | Offline, third-party, with `beacon-verify` + `umbrella-conformance verify --ucid-coverage` |
| Standards posture | "Aligned with NIST AI RMF" | Standards-first ([OVERT 1.0](https://overt.is/), in-toto, SLSA, DSSE); frameworks cite standards, not the reverse |

---

## How to use this checklist

1. Score each item **Pass / Warn / Fail / N/A** in your evaluation spreadsheet.
2. **Any `Fail` in Section A or Section B is disqualifying.** No amount of documentation overcomes a missing signature.
3. Sections C–F establish the gap you would have to backfill if you adopt the vendor.
4. Save the completed checklist alongside your procurement package — the procurement record itself becomes part of the audit trail.

---

## Section A — Cryptographic evidence (disqualifying if any Fail)

The non-negotiables. A "Policy-as-Code" vendor that cannot satisfy Section A is selling governance theater.

| # | Requirement | Test |
|---|---|---|
| A1 | **Every claimed control emits a signed runtime receipt.** No screenshots, no portal-only attestation. | Ask for 3 receipts from the last 24 h. Verify their signatures **offline** with a tool the vendor did not author. |
| A2 | **Signed receipts use a published, open algorithm** (Ed25519 or P-256). RSA-PKCS1v15 is not acceptable for new deployments. | `openssl asn1parse` / `beacon-verify` round-trips. |
| A3 | **Public key is fingerprinted and pinnable** by the verifier — not just "trust the vendor's HTTPS endpoint." | Vendor publishes `key_fingerprint`. You verify by fingerprint, not URL. |
| A4 | **Receipts are tamper-evident** — chained (foundation format) or individually self-contained (runtime / OVERT format) with explicit `prev_*_sha256` link or signed canonical form. | Mutate a byte in a copy of one receipt; verifier must reject. |
| A5 | **Aggregate evidence bundles are wrapped in DSSE / in-toto Statement v1** (`payloadType: application/vnd.in-toto+json`) with a fixed `predicateType`. | Inspect a sample bundle. `_type` must be `https://in-toto.io/Statement/v1`. |
| A6 | **Bundles are signable via keyless OIDC** (Sigstore / Fulcio / Rekor) and verifiable without proprietary tooling. | `cosign verify-blob` works with no vendor SDK. |
| A7 | **Every embedded receipt is independently re-verifiable** — the outer DSSE signature does **not** substitute for receipt-level verification. | Strip the outer DSSE; verifier must still validate the inner receipts. |
| A8 | **Long-term archival path exists.** Either Rekor entries or an equivalent transparency log; keys rotate without breaking historical evidence. | Vendor publishes their key-rotation runbook. |

**Implementation pointer:** the AiGovOps stack satisfies A1–A8 via [Beacon](https://github.com/bobrapp/aigovops-beacon) (signing) + [Umbrella](https://github.com/bobrapp/umbrella-govops) `EvidenceBundle.receipts[]` (embedding) + `cosign sign-blob` keyless (outer envelope). See the [threat model](../foundation/THREAT-MODEL.md) for the attacks each item defends against.

---

## Section B — Identifier governance (disqualifying if any Fail)

If a vendor's control IDs are branding, you will pay the migration tax forever. Identifiers must be **infrastructure**.

| # | Requirement | Test |
|---|---|---|
| B1 | **Identifiers are versioned, never reused, and never silently renamed.** Once an ID is allocated, that string maps to that concept forever. | Ask for the vendor's deprecation policy. Read it. |
| B2 | **A formal status lifecycle exists** — at minimum: provisional, stable, deprecated, superseded. | Vendor produces a registry document with statuses per identifier. |
| B3 | **Named Designated Expert(s) review every addition and change**, with a published term, conflict-of-interest rules, and recusal procedure. | "Our compliance team" is not an answer. You want a name and a term. |
| B4 | **Changes happen by public pull request** against a versioned registry file. No silent edits. | `git log` on the registry file shows reviewed PRs. |
| B5 | **Identifier syntax is regex-checkable** and documented. | A schema file enforces it (e.g. `^UCID-[A-Z][A-Z0-9]{1,7}(-[A-Z0-9]{1,16})*-[0-9]{3}$`). |
| B6 | **Framework citations are pinned to a specific framework version.** When NIST AI RMF or the EU AI Act publishes a revision, the registry adds a row — it does not silently rewrite citations. | Vendor's crosswalk file shows pinned versions (e.g. `NIST AI RMF 1.0`, not "NIST AI RMF"). |
| B7 | **Split / merge / retire procedures are documented.** What happens when one obligation becomes two, or two collapse into one? | Read the procedure. If it is absent, assume nothing happens — silently. |

**Implementation pointer:** the AiGovOps [UCID Registry](../UCID-REGISTRY.md) and [crosswalks/unified-control-id.yaml](../crosswalks/unified-control-id.yaml) are modeled on [IANA protocol registries](https://www.iana.org/protocols) and RFC 8126.

---

## Section C — Architectural posture

Sections C–F are not disqualifying individually, but a vendor failing most of them will be expensive to absorb.

| # | Requirement | Test |
|---|---|---|
| C1 | **The runtime evidence layer is independently usable** — i.e. a project can adopt the receipt format without adopting the rest of the vendor's stack. | Can you sign and verify with just the open-source receipt library, no SaaS account? |
| C2 | **Asymmetric integration:** the lower layer (runtime) does not depend on the upper layer (program / control catalog). Identifier coupling lives in the upper layer only. | Inspect the receipt schema. If it has a `governance` block referencing the vendor's control catalog, that is coupling — and a Section C1 violation. |
| C3 | **Receipts are OVERT-pure** (or equivalent open standard). No vendor-proprietary fields in the signed payload. | Compare receipts to the OVERT 1.0 spec. |
| C4 | **Two distinct release cadences** — slow + signed for the runtime; fast + informational for the program / framework registry. | Vendor publishes a release calendar showing both. |
| C5 | **Deprecation window ≥ 24 months** for any field removed from the runtime schema. | Read the vendor's published deprecation policy. |
| C6 | **Build provenance for the vendor's own tools** is published (SLSA Level ≥ 3 or in-toto attestations on the CLI binaries). | `cosign verify-attestation` against a vendor-published binary. |
| C7 | **No "enterprise edition"** of the verifier. Verification logic is open source. | Find the verifier source. If you cannot, this is a Section A1 violation in disguise. |

**Implementation pointer:** the [Beacon README](https://github.com/bobrapp/aigovops-beacon#beacon-runs-alone) and the Umbrella [README cadence table](../README.md#beacon-and-umbrella--two-layers-two-cadences) make C1–C5 explicit. [Policy positions P3, P5, P7](../foundation/POLICY-POSITIONS.md) bind the Foundation to this posture publicly.

---

## Section D — Standards alignment

Frameworks update on regulatory clocks (years); standards update on engineering clocks (months). Pin to standards.

| # | Requirement | Test |
|---|---|---|
| D1 | **Signed receipt format conforms to an open standard** ([OVERT 1.0](https://overt.is/), [COSE](https://www.rfc-editor.org/rfc/rfc9052), [JOSE](https://www.rfc-editor.org/rfc/rfc7515), or equivalent). | Vendor names the spec and the version. |
| D2 | **Attestation envelopes conform to [in-toto Statement v1](https://github.com/in-toto/attestation/tree/main/spec/v1)** with a documented, vendor-controlled `predicateType`. | `_type` and `predicateType` are present and stable. |
| D3 | **Outer signatures conform to [DSSE](https://github.com/secure-systems-lab/dsse)** with a `payloadType` of `application/vnd.in-toto+json`. | Inspect a sample envelope. |
| D4 | **Build provenance conforms to [SLSA](https://slsa.dev/)** Level ≥ 3 for the vendor's own production binaries. | Vendor publishes the SLSA level + attestation. |
| D5 | **Canonical JSON** form is documented (RFC 8785 or equivalent) so signatures survive serialization round-trips across languages. | Vendor names the canonicalization spec. |
| D6 | **Transparency log usage** ([Rekor](https://docs.sigstore.dev/logging/overview/) or [Sigsum](https://www.sigsum.org/)) is documented for production signatures. | Vendor's CI workflow publishes log entries; you can fetch one. |

**Implementation pointer:** the [policy position P3 "standards first, frameworks second"](../foundation/POLICY-POSITIONS.md) commits the Foundation to D1–D6 publicly.

---

## Section E — Crosswalk integrity

Crosswalks are how policy survives regulator churn. Verify they are not just marketing tables.

| # | Requirement | Test |
|---|---|---|
| E1 | **The crosswalk is a versioned YAML/JSON file**, not a PDF, not a portal table. | Find it in git. |
| E2 | **Citations are specific to the framework version.** E.g., not "NIST AI RMF" but "NIST AI RMF 1.0, MEASURE-2.11." | Open the file. Specificity is visible per row. |
| E3 | **An automated check verifies that every cited framework reference exists** in the corresponding framework registry. | The vendor's CI runs this check on every PR. |
| E4 | **A second automated check verifies that every identifier has at least one implementing control** in `enforced` status (not draft, not shadow). | Same; this is the difference between a claim and a control. |
| E5 | **A third automated check verifies that every `enforced` control with runtime-evidence requirements has matching receipt evidence** in produced bundles. | Vendor's `verify --ucid-coverage` (or equivalent) gate runs in CI. |
| E6 | **The crosswalk's commit SHA is recorded in every evidence bundle** so future auditors can reproduce the mapping that was in force at the time. | Inspect a bundle's `metadata.commit_sha`. |

**Implementation pointer:** the Umbrella CLI implements `schema-valid`, `crosswalk-resolved`, `controls-have-checks` checks plus `umbrella-conformance verify --ucid-coverage` for E5; the bundle records `metadata.commit_sha` for E6.

---

## Section F — Process, governance, and conflict of interest

A vendor that profits from issuing compliance certificates has a structural incentive to lower the bar.

| # | Requirement | Test |
|---|---|---|
| F1 | **The vendor does not issue compliance certificates or conformity assessments** for its own platform. | "AiGovOps-Certified" stamps are a Section F1 failure. |
| F2 | **Open source license** on the runtime, the verifier, the schemas, and the registry. Apache-2.0 or MIT preferred. | Read the LICENSE files. |
| F3 | **Public threat model** scoped to the evidence pipeline. | Vendor publishes one. (See [our seed](../foundation/THREAT-MODEL.md).) |
| F4 | **Public policy positions** the vendor will defend in regulatory comment letters and standards work. | Vendor publishes a positions document and tracks open questions. (See [ours](../foundation/POLICY-POSITIONS.md).) |
| F5 | **Public glossary** with one authoritative definition per term, cited from every other doc. | Find it. Spot-check one term across multiple vendor docs. |
| F6 | **Forward-looking release calendar** with both committed (tagged releases) and target dates. | Read it. (See [ours](../foundation/RELEASE-CALENDAR.md).) |
| F7 | **The vendor's own CI publishes signed evidence bundles** for its own releases — i.e. the vendor eats its own dogfood. | Find the latest release. Verify its bundle with the verifier from F2. |

---

## Scoring template (copy into your evaluation spreadsheet)

```
A. Cryptographic evidence     [ ] A1 [ ] A2 [ ] A3 [ ] A4 [ ] A5 [ ] A6 [ ] A7 [ ] A8
B. Identifier governance      [ ] B1 [ ] B2 [ ] B3 [ ] B4 [ ] B5 [ ] B6 [ ] B7
C. Architectural posture      [ ] C1 [ ] C2 [ ] C3 [ ] C4 [ ] C5 [ ] C6 [ ] C7
D. Standards alignment        [ ] D1 [ ] D2 [ ] D3 [ ] D4 [ ] D5 [ ] D6
E. Crosswalk integrity        [ ] E1 [ ] E2 [ ] E3 [ ] E4 [ ] E5 [ ] E6
F. Governance / COI           [ ] F1 [ ] F2 [ ] F3 [ ] F4 [ ] F5 [ ] F6 [ ] F7

Disqualifying gates:
  Any Fail in A or B  →  reject
  ≥ 3 Fails in C+D    →  high integration risk; require remediation plan before signing
  Any Fail in F1      →  conflict-of-interest disqualification regardless of other scores
```

---

## How AiGovOps measures itself against this checklist

We publish this so we can be held to it. As of 2026-06-01, the AiGovOps stack (Beacon + Umbrella) scores:

| Section | Score | Evidence |
|---|---|---|
| A. Cryptographic evidence | **8/8** | Ed25519 receipts (A1–A4), DSSE envelope (A5), `cosign sign-blob` keyless (A6), independent receipt re-verification (A7); Rekor + 24-month rotation policy at Beacon v0.2.0 (A8). |
| B. Identifier governance | **7/7** | [UCID-REGISTRY.md](../UCID-REGISTRY.md) covers B1–B7. |
| C. Architectural posture | **7/7** | Beacon runs alone (C1); asymmetric integration via `EvidenceBundle.receipts[]` (C2); OVERT-pure receipts (C3); two-cadence release model (C4); 24-month deprecation (C5); SLSA-attested CLI builds (C6); open-source verifier (C7). |
| D. Standards alignment | **6/6** | OVERT 1.0 (D1); in-toto Statement v1 (D2); DSSE (D3); SLSA L3 in CI (D4); RFC 8785 canonicalization (D5); Rekor in CI (D6). |
| E. Crosswalk integrity | **6/6** | YAML crosswalk in git (E1); pinned framework versions (E2); `crosswalk-resolved` check (E3); `controls-have-checks` check (E4); `verify --ucid-coverage` (E5); `metadata.commit_sha` in bundles (E6). |
| F. Governance / COI | **7/7** | No certification program (F1); Apache-2.0 (F2); [threat model](../foundation/THREAT-MODEL.md) (F3); [policy positions](../foundation/POLICY-POSITIONS.md) (F4); [glossary](../foundation/GLOSSARY.md) (F5); [release calendar](../foundation/RELEASE-CALENDAR.md) (F6); self-signed releases (F7). |

**Total: 41 / 41.** If you find a gap, [open an issue](https://github.com/bobrapp/umbrella-govops/issues/new/choose).

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| v.1 | 2025-Q3 | Initial checklist — control coverage and framework crosswalks only. |
| v.2 | 2026-Q1 | Added basic signing requirements; introduced control catalogs as a category. |
| **v.3** | **2026-06-01** | Reorganized around the Beacon/Umbrella split. Added disqualifying gates in Sections A and B. Added Sections C–F. Added vendor-scoring template and self-scoring table. |

---

## Citing this checklist

> AiGovOps Foundation, *Policy-as-Code: Vendor and Approach Checklist v.3*,
> [bobrapp.github.io/umbrella-govops/policy-as-code-vendor-and-approach-checklist-v3](https://bobrapp.github.io/umbrella-govops/policy-as-code-vendor-and-approach-checklist-v3.html),
> 2026-06-01.

Pin to a specific commit SHA when citing in regulator-facing documents, not `main`.
