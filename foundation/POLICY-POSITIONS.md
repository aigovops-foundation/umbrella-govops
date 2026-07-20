# AiGovOps Foundation — Policy Positions

**Scope:** Public stances the AiGovOps Foundation (501c3) will defend in regulatory comment letters, standards work, and public statements. Positions are **deliberately few**: each one must be defensible from first principles and consistent across Beacon and Umbrella technical choices.

**Status:** Seed v0.1 — board ratification pending at the 2026-Q3 meeting.

---

## P1 — Evidence must be machine-verifiable

> AI-governance evidence intended for regulator or auditor review MUST be cryptographically signed in a format that any third party can verify offline, with documented algorithms and public keys.

**Why:** Trust in AI systems cannot rest on screenshots, vendor dashboards, or proprietary audit tools. The same principle that produced reproducible builds and SBOM signing must apply to governance evidence.

**Practical implication:** AiGovOps will not endorse evidence formats that require a SaaS vendor's runtime to validate, nor formats that bundle verification logic with the evidence itself (a self-attesting envelope is not a proof).

---

## P2 — Identifiers are infrastructure, not branding

> AI-governance identifier schemes (control ids, framework citations, evidence types) are **infrastructure** and should be governed as such: stable forever, never reused, change procedures public, designated experts named.

**Why:** Every regulator-internal numbering system that has been allowed to drift has cost real money in re-mapping work. We model UCID governance on [IANA protocol registries](https://www.iana.org/protocols) precisely so this does not happen again.

**Practical implication:** AiGovOps publishes the [UCID Registry](../UCID-REGISTRY.md) with formal statuses and a Designated Expert. We will press standards bodies to adopt the same posture for their own identifiers.

---

## P3 — Standards first, frameworks second

> When a behavior can be encoded in an open, vendor-neutral *standard* (OVERT, in-toto, SLSA, DSSE, COSE, JOSE), AiGovOps will encode it there. **Frameworks** (NIST AI RMF, ISO/IEC 42001, EU AI Act) cite standards; standards do not cite frameworks.

**Why:** Frameworks update on regulatory clocks (years). Standards update on engineering clocks (months). If Beacon's signed receipt format had been pinned to "the NIST AI RMF appendix" it would already be out of date.

**Practical implication:** Beacon's signed receipt format follows [OVERT 1.0](https://overt.is/). Umbrella's evidence binding follows in-toto Statement v1. Framework registry entries are *citations*, not *schemas*.

---

## P4 — Runtime evidence is mandatory; controls without evidence are theater

> Any AI-governance control claimed by a deployed system MUST be backed by signed runtime evidence. A control that produces only documentation, screenshots, or self-reported attestations is **not** a control AiGovOps will recognize as `enforced`.

**Why:** Most published "AI governance frameworks" reduce to a Word document. The single technical contribution AiGovOps makes is forcing the runtime back into the picture.

**Practical implication:** Umbrella's `evidence-signed` and `overt-predicate-valid` checks must pass for a control to reach `status: enforced`. We will resist any regulator pressure to recognize unsigned attestations as sufficient.

---

## P5 — Open source by default, public by default

> The Beacon reference implementation, the Umbrella framework registry, and the UCID registry are MIT/Apache-2.0, public, and developed in the open. Forks are encouraged. Proprietary fork-and-extend is permitted but cannot use AiGovOps trademarks.

**Why:** A governance regime that is itself opaque cannot ask others to be transparent.

**Practical implication:** No "enterprise edition." No closed source verifier. Trademark policy enforced for "AiGovOps-conformant" claims.

---

## P6 — We do not certify

> AiGovOps Foundation does not issue compliance certificates, conformity assessments, or audit opinions. We publish signed evidence and the tools to verify it. Conformity assessment is the regulator's, the notified body's, or the auditor's job.

**Why:** Conflict-of-interest survival rule. The moment AiGovOps becomes a certifier, every technical choice gets routed through liability counsel.

**Practical implication:** No "AiGovOps Certified" stamp. Audit firms can use Umbrella bundles; AiGovOps will not endorse any single firm.

---

## P7 — Beacon stays usable by people who never heard of Umbrella

> The Beacon runtime, schemas, and verifier MUST work for projects that have no relationship to AiGovOps Foundation. We will not introduce a `governance` block or UCID coupling into Beacon's signed payload.

**Why:** Asymmetric integration is the only durable shape. Umbrella users need Beacon. Beacon users do not need Umbrella.

**Practical implication:** Beacon receipts remain OVERT-pure. UCID binding lives in `EvidenceBundle.checks[].evidence_refs[]`, which is an Umbrella construct.

---

## Open positions (debate before ratification)

* **P8 (draft)** — Should AiGovOps require Sigstore transparency-log entries (Rekor) for every `enforced` control? Cost vs. integrity.
* **P9 (draft)** — Position on AI-system "right to explanation" claims that lack signed runtime evidence — refuse, defer to regulator, or publish counter-evidence?

These are tracked as issues and will be added to this document only after a Foundation board vote.
