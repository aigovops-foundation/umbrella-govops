# Governance

Umbrella-GovOps is a project of the **AiGovOps Foundation**, a U.S. 501(c)(3) nonprofit.
This document describes how the project is governed: who decides, how decisions are made,
and how the community participates.

> **Status:** v0.1 — bootstrap. The Foundation board will ratify the v1.0 governance
> document at its first quarterly meeting after incorporation milestones are met.
> Until then, this v0.1 applies.

---

## 1. Principles

1. **Open by default.** All specifications, schemas, crosswalks, and reference
   implementations are published under Apache-2.0 (code) and CC-BY-4.0 (docs).
2. **Neutral.** The Foundation does not sell hosted Umbrella services, certify
   for-profit vendors as exclusive providers, or accept paid placement in the
   framework registry, the UCID Registry, or the vendor checklist.
3. **Verifiable.** Every released artifact (evidence bundle, conformance run,
   spec PDF) is cryptographically signed and independently verifiable. See
   [Beacon](https://aigovops-foundation.github.io/aigovops-beacon/).
4. **Conflicts disclosed.** All maintainers and Designated Experts publish
   conflicts of interest. See [foundation/POLICY-POSITIONS.md](foundation/POLICY-POSITIONS.md).

## 2. Roles

| Role | Responsibility | Term |
|---|---|---|
| **Foundation Board** | Fiduciary oversight, ratifies major spec versions, approves COI policy | Per bylaws |
| **Project Lead** | Roadmap, release cuts, breaking-change decisions | 2 years, renewable |
| **Designated Expert (UCID)** | Reviews UCID Registry additions per [UCID-REGISTRY.md](UCID-REGISTRY.md) | 2 years |
| **Working Group Chairs** | Frameworks-WG, Crosswalks-WG, Evidence-WG, Practitioner-Cert-WG | 1 year, renewable |
| **Maintainers** | Code review, merge rights, release sign-off | Indefinite, may step down |
| **Contributors** | Anyone with a merged PR or a ratified spec proposal | N/A |

Current Project Lead and Designated Expert: **Bob Rapp** (term 2026-Q2 → 2028-Q2).

## 3. Decision making

- **Lazy consensus** for editorial changes, doc fixes, and non-breaking additions.
- **Pull request with 2 maintainer approvals** for code changes touching schemas,
  CLI behavior, or the conformance test suite.
- **Formal proposal** (issue with `proposal` label, 14-day comment window, board
  vote if board-reserved) for: new framework additions, UCID lifecycle changes,
  predicate type changes, license changes, breaking schema changes.
- Tie-breaker on technical decisions: Project Lead. Tie-breaker on Foundation
  policy: Board.

## 4. Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The Foundation Board hears appeals.

## 5. Releases

See [foundation/RELEASE-CALENDAR.md](foundation/RELEASE-CALENDAR.md) for cadence.
- Umbrella moves fast: monthly minor releases, semver patch as needed.
- Beacon moves slow: ~2 signed stable releases per year.
- Every release ships a signed evidence bundle. No exceptions.

## 6. Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All PRs require:
- DCO sign-off (`-s` on every commit)
- A passing `make test-all`
- A schema-validating evidence bundle if the change touches controls or crosswalks

## 7. Amendments

This document is amended by board ratification of a PR with `governance-change`
label, after a 30-day public comment window.

---

*Apache-2.0 · AiGovOps Foundation · contact: governance@aigovopsfoundation.org*
