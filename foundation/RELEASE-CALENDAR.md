# AIGovOps Release Calendar

**Scope:** Forward-looking dates for releases across the AIGovOps program. Keep two cadences clearly separate:

* **Beacon** — the product. Slow, signed, versioned. **≈ 2 releases/year.** Releases are signed, tagged, and shipped with a SBOM + benchmark refresh.
* **Umbrella** — the program. Fast, informational. **Quarterly digests** + **monthly framework-registry refresh**.

All dates use UTC. Times shown as `T00:00Z` are "by end of that day UTC."

---

## Beacon release track (the product)

| Tag       | Target date    | Type        | Contents                                                                                                |
|-----------|----------------|-------------|---------------------------------------------------------------------------------------------------------|
| `v0.1.0`  | 2026-06-30     | Minor       | First tagged release. Includes BENCHMARKS.md, RELATED.md, `beacon-verify` console script, OVERT 1.0 receipts. |
| `v0.2.0`  | 2026-Q4 (target 2026-11-30) | Minor | OVERT 1.0 round-trip test vectors published, deprecation policy v1, Sigstore Rekor v2 integration.       |
| `v1.0.0`  | 2027-Q2 (target 2027-05-15) | Major | API stability promise. Frozen receipt schema. 24-month deprecation window starts.                       |

**Deprecation policy (effective at v0.2.0):**

* Any field removed from a Beacon receipt schema gets a **24-month** deprecation window.
* Removal is announced in the Beacon release notes and mirrored in the Umbrella quarterly digest.
* Verifiers MUST continue to accept deprecated-but-present fields for the full window.

---

## Umbrella release track (the program)

### Major Umbrella releases

| Tag       | Target date     | Theme                                                                 |
|-----------|-----------------|-----------------------------------------------------------------------|
| `v0.1`    | 2026-05-29 ✅ (shipped) | First public release: 4 controls, 4 UCIDs (all `provisional`), 38 frameworks in registry, e2e test harness. |
| `v0.2`    | 2026-Q3 (target 2026-09-15) | UCID promotion: `provisional → stable` for the original 4 UCIDs. Beacon receipt embedding lands. DSSE bundle signed in CI. |
| `v0.3`    | 2026-Q4 (target 2026-12-15) | First framework refresh: NIST AI RMF profile updates + ISO/IEC 42001 cross-reference review.            |
| `v1.0`    | 2027-Q3 (target 2027-09-30) | Stable UCID + framework registry contracts. 18-month deprecation window starts.                          |

### Recurring cadence

| Cadence    | What ships                                                                                                  | Owner                       |
|------------|-------------------------------------------------------------------------------------------------------------|-----------------------------|
| **Quarterly digest** | Public summary post: new/changed UCIDs, framework version bumps, deprecations, upcoming Beacon release notes. Published 2nd Tuesday of Jan/Apr/Jul/Oct. | Foundation comms lead.       |
| **Monthly framework refresh** | PR against `frameworks/_registry.yaml`: new framework versions, errata, retired entries. Last Friday of each month. | Designated Expert.           |
| **Weekly UCID triage** | Designated Expert reviews open UCID PRs. Friday 17:00 UTC. No public artifact.                          | Designated Expert.           |

### Next 90 days (rolling)

| Date          | Item                                                                            |
|---------------|---------------------------------------------------------------------------------|
| 2026-06-12    | Monthly framework refresh (Jun)                                                 |
| 2026-06-30    | Beacon v0.1.0 tag                                                               |
| 2026-07-14    | Q3 quarterly digest (covers Apr–Jun)                                            |
| 2026-07-31    | Monthly framework refresh (Jul)                                                 |
| 2026-08-28    | Monthly framework refresh (Aug)                                                 |

---

## How to consume this calendar

* Auditors and downstream integrators SHOULD subscribe to the GitHub releases feed on both repos.
* Quarterly digests will additionally be cross-posted to the AIGovOps Foundation site.
* Dates in this document are **targets**, not commitments — only tagged Beacon releases are commitments under the deprecation policy.

## Updates to this document

This file changes at most monthly. Updates require a PR with at least one Foundation board approval. The previous version is always available via `git log`.
