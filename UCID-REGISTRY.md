# Umbrella Unified Control Identifier (UCID) Registry

**Status:** Living document
**Maintained by:** AIGovOps Foundation (501c3)
**Designated Expert:** Bob Rapp (`@bobrapp`) — Co-founder, AIGovOps Foundation
**Backup Expert:** *vacant — Foundation board to designate by 2026-Q3*
**Registry source of truth:** [`crosswalks/unified-control-id.yaml`](crosswalks/unified-control-id.yaml)
**Companion runtime product:** [Beacon](https://github.com/bobrapp/aigovops-beacon) (binds receipts to UCIDs via `evidence_refs`)

---

## 1. Purpose

A **Unified Control Identifier (UCID)** is a stable, citable identifier for a single normative
AI-governance obligation — independent of any single regulatory framework. UCIDs are how the
Umbrella program lets a control author write *one* requirement that **cites** NIST AI RMF, the
EU AI Act, ISO/IEC 42001, and future frameworks without rewriting the control every time a
regulator updates wording.

UCIDs are **not** controls. They are **pivots**. A UCID maps:

```
UCID  →  N regulatory citations (the "what the law says")
UCID  →  M implementing controls (the "how we prove it" — e.g. DG-002, HO-001)
UCID  →  K Beacon receipts at runtime (the "what actually happened" — via evidence_refs)
```

This registry follows the operational model of [IANA protocol registries](https://www.iana.org/protocols)
and [RFC 8126 "Guidelines for Writing an IANA Considerations Section in RFCs"](https://www.rfc-editor.org/rfc/rfc8126):
formal statuses, designated experts, public change requests, and an immutable history.

---

## 2. Status values

Every UCID carries exactly one status. Statuses move only forward (except `superseded`, which
may be assigned to any non-`deprecated` UCID when a replacement is registered).

| Status        | Meaning                                                                                                                  | Stability promise                                                                                       |
|---------------|--------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| `provisional` | Newly proposed. Citations may shift, title may be renamed, may be merged or withdrawn before reaching `stable`.          | None. Implementers SHOULD NOT pin runtime evidence to provisional UCIDs.                                |
| `stable`      | Reviewed by Designated Expert, citations frozen against then-current framework versions, at least one implementing control merged. | UCID **id** and **title** will not change. Citations may gain entries (new frameworks) but not lose them.|
| `deprecated`  | No longer recommended for new bindings. Retained for historical evidence bundles.                                        | id permanent; will never be reassigned.                                                                  |
| `superseded`  | Replaced by one or more newer UCIDs (recorded in `superseded_by`). Old evidence still resolvable.                        | id permanent; will never be reassigned.                                                                  |

**Rule:** A UCID id is allocated **forever**. Once registered, the identifier string
(`UCID-DATA-BIAS-001`, etc.) is never reused for a different concept — even after deprecation.

---

## 3. Identifier syntax

```
UCID-<DOMAIN>-<TOPIC>-<NNN>
```

* `DOMAIN` — 2–8 uppercase letters: `DATA`, `OVERSIGHT`, `LOG`, `SEC`, `TRANSP`, `RISK`, `INCIDENT`, `SUPPLYCHAIN`, ...
* `TOPIC`  — 1–16 uppercase letters/digits, separated by `-`. Optional if `DOMAIN` is unambiguous.
* `NNN`    — three-digit zero-padded sequence within `(DOMAIN, TOPIC)`. Starts at `001`.

Regex (matches the `ucid` field in `conformance/schemas/control.schema.json`):

```
^UCID-[A-Z][A-Z0-9]{1,7}(-[A-Z0-9]{1,16})*-[0-9]{3}$
```

Examples:

* `UCID-DATA-BIAS-001` ✅
* `UCID-LOG-001` ✅ (no TOPIC)
* `UCID-SUPPLYCHAIN-SBOM-001` ✅
* `ucid-data-bias-001` ❌ (lowercase)
* `UCID-DATA-BIAS-1` ❌ (sequence not zero-padded)

---

## 4. Change procedure

All registry changes happen by **public pull request** against
[`crosswalks/unified-control-id.yaml`](crosswalks/unified-control-id.yaml) and this document.

### 4.1 New UCID (`provisional`)

1. Open a PR adding a new entry to `unified-control-id.yaml`. Minimum fields:
   * `id`, `title`, `status: provisional`, at least one of `nist_ai_rmf` / `eu_ai_act` / `iso_42001`, `created`, `proposer`.
2. Add a row to §8 below with status `provisional`.
3. Designated Expert reviews within **14 calendar days**. If silent past 14 days, the proposer
   may escalate to the AIGovOps Foundation board via `governance@aigovops.org`.
4. PR merges with two approving reviews (Designated Expert + one Foundation member).

### 4.2 Promotion `provisional → stable`

Required:

* At least one `implementing_controls` entry with `status: enforced` in `domains/*/controls/`.
* All cited framework references resolved to a specific framework version pinned in
  [`frameworks/_registry.yaml`](frameworks/_registry.yaml).
* A passing CI run on `main` that includes `crosswalk-resolved` and `controls-have-checks` checks.
* Designated Expert sign-off recorded in the PR.

### 4.3 Deprecation / supersession

* `stable → deprecated` requires a deprecation rationale and a notice in the next quarterly
  release calendar entry. Existing evidence bundles continue to verify.
* `stable → superseded` requires registration of the replacement UCID(s) and a `superseded_by`
  field listing them. The replacement UCID MAY be `provisional` at the moment of supersession.

### 4.4 Split, merge, withdraw

* **Split** — one `stable` UCID becomes ≥ 2 new UCIDs: register the new UCIDs as `provisional`,
  mark the original `superseded` once the new ones reach `stable`, record `split_into` on the original.
* **Merge** — ≥ 2 `stable` UCIDs become one: register the merged UCID as `provisional`, mark the
  originals `superseded` once the merged UCID reaches `stable`, record `merged_into`.
* **Withdraw** — only permitted while a UCID is `provisional`. The id is then **retired** —
  never reissued, never reused, removed from `unified-control-id.yaml` but recorded in §9 below.

---

## 5. Designated Expert role

The Designated Expert is responsible for:

* Reviewing all new UCID PRs within 14 days.
* Confirming citation accuracy against the **pinned framework version** in
  [`frameworks/_registry.yaml`](frameworks/_registry.yaml).
* Confirming that no existing UCID already covers the same normative obligation.
* Approving status transitions.
* Maintaining this document.

The Designated Expert serves a **two-year term**, renewable, appointed by the AIGovOps Foundation
board. Conflicts of interest (employer paying the expert to push a specific UCID) MUST be
declared and recused for that PR.

Current Designated Expert: **Bob Rapp** (`@bobrapp`, bobrapp@hotmail.com) — term 2026-Q2 → 2028-Q2.

---

## 6. Relationship to controls and Beacon receipts

```
                  UCID (in this registry)
                   │
                   ├── cites ──→  framework refs (NIST/EU/ISO/...)
                   │
                   ├── implemented_by ──→ controls (DG-002, HO-001, ...)
                   │
                   └── evidenced_by ──→ Beacon receipts at runtime
                                          (EvidenceBundle.checks[].evidence_refs[])
```

A control schema entry MAY include a `beacon:` block. When a `status: enforced` control declares
`beacon: required`, `umbrella-conformance verify --beacon-bundle <path>` will fail if no Beacon
receipt is found that references the control's UCID within the configured freshness window.

Beacon receipts themselves are **OVERT-pure**: they do not embed UCIDs in the signed payload.
The binding lives in the *Umbrella* EvidenceBundle's `checks[].evidence_refs[]` array, which
points at receipt IDs. This keeps Beacon usable by projects that have never heard of Umbrella.

---

## 7. Versioning of the registry

The registry as a whole is versioned by **Umbrella release** (see
[foundation/RELEASE-CALENDAR.md](foundation/RELEASE-CALENDAR.md)). Each Umbrella release tags a
commit; the registry state at that commit is the canonical registry for that release.

Citations from frameworks are pinned by `frameworks/_registry.yaml` entries (which carry their
own version strings — e.g. NIST AI RMF 1.0, EU AI Act OJ L 2024/1689). When a framework
publishes a new version, the Designated Expert opens a PR adding the new version to the registry
and either (a) confirms existing UCID citations still resolve, or (b) opens follow-up PRs to
update affected UCIDs.

---

## 8. Active registry (as of 2026-05-29)

| UCID                       | Title                              | Status        | Created     | Implementing controls | Notes |
|----------------------------|------------------------------------|---------------|-------------|------------------------|-------|
| `UCID-DATA-BIAS-001`       | Dataset bias examination           | `provisional` | 2026-04-12  | DG-002                 | First UCID; awaiting promotion review. |
| `UCID-OVERSIGHT-001`       | Human oversight measures           | `provisional` | 2026-04-12  | HO-001                 | HO-002, HO-003 planned. |
| `UCID-LOG-001`             | Automatic logging of events        | `provisional` | 2026-04-12  | LOG-001                | LOG-002 planned. |
| `UCID-SEC-ROBUST-001`      | Security and adversarial robustness| `provisional` | 2026-04-12  | SR-001                 | Tracks EU AI Act Art. 15. |

All four UCIDs are eligible for promotion to `stable` in the Umbrella v0.2 release once the
implementing controls reach `status: enforced` and CI checks pass. See
[foundation/RELEASE-CALENDAR.md](foundation/RELEASE-CALENDAR.md).

---

## 9. Retired identifiers

*(none yet — this section will record withdrawn `provisional` UCID ids that must never be reused)*

---

## 10. Open questions / future work

* Should `UCID-LOG-001` split into a UCID per logged event-class (input/output/decision/error)?
  Tracked in [#TBD](https://github.com/bobrapp/umbrella-govops/issues).
* OECD AI Principles citations are not yet in scope; pending a separate framework-registry PR.
* Once ≥ 25 UCIDs are registered, this document migrates to a published site under
  [bobrapp.github.io/umbrella-govops/registry/](https://bobrapp.github.io/umbrella-govops/registry/).

---

## 11. Citing a UCID

In external documents, cite a UCID as:

> AIGovOps UCID-OVERSIGHT-001, *Human oversight measures*, Umbrella-GovOps registry
> (`https://github.com/bobrapp/umbrella-govops/blob/main/UCID-REGISTRY.md`), accessed YYYY-MM-DD.

Tools consuming the YAML registry SHOULD pin to a specific commit SHA, not `main`.
