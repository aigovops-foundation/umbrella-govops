# Contributing to Umbrella-GovOps

Thanks for your interest in contributing. Umbrella-GovOps is an open-source
project of the [AIGovOps Foundation](https://aigovops.org) (a US 501(c)(3)
non-profit). All contributions — code, controls, crosswalks, docs, issues —
are welcome under the project's [Apache-2.0 license](LICENSE).

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

| If you want to… | Start here |
| --- | --- |
| Report a bug or missing check | [Open an issue](https://github.com/bobrapp/umbrella-govops/issues/new) with the `bug` label |
| Propose a new framework or crosswalk row | Open an issue with the `framework` label, then submit a PR against `crosswalks/unified-control-id.yaml` |
| Add a control to a domain | PR under `domains/<domain>/controls/` following the schema in `schemas/control.schema.json` |
| Improve the conformance CLI or SDKs | PR against `conformance/` or `sdk/{python,typescript}/` |
| Report a security vulnerability | **Do not file a public issue.** See [SECURITY.md](SECURITY.md) |

## Development setup

```bash
# Python deps + editable install of the conformance package
make install

# Playwright browser for the e2e suite (only needed for tests/e2e)
make install-e2e
```

Validate locally before opening a PR:

```bash
make test-all
```

That runs the full four-pillar harness — unit, scale, chaos, e2e. See
[tests/README.md](tests/README.md) for details.

## Pull-request checklist

- [ ] Branch from `main`, keep changes focused.
- [ ] New controls follow `schemas/control.schema.json` and have at least one
      check.
- [ ] New crosswalk rows reference real UCIDs and real implementing controls
      (the `crosswalk-resolved` check will catch dangling pointers).
- [ ] Tests pass locally (`make test-all`).
- [ ] If you added a new behavior, add a unit or chaos test that would have
      failed without your change.
- [ ] PR description explains the *why* — what governance gap or audit
      finding does this close?
- [ ] CI is green on your branch (the `harness` and `govops-ci` workflows).

## Test-pyramid expectations

The repo enforces a full pyramid (see [tests/README.md](tests/README.md) and
[docs/api/](docs/api/)). What a PR must add depends on what it changes:

| If your PR adds / changes… | You must also… |
| --- | --- |
| A **JSON Schema** (`conformance/schemas/*.json`) | Ensure it is valid Draft 2020-12 (the `test_every_schema_is_valid_draft_2020_12` unit test covers this) and add a strict-rejection test in `tests/unit/test_schemas_strict.py` for the bad inputs it forbids. |
| A **crosswalk / UCID** row | Keep `crosswalk-resolved` and `tests/unit/test_ucid_registry.py` green — a new UCID needs a canonical id, ≥ 1 framework citation, and real implementing controls (no dangling references). Update `docs/api/data-model.md` if you add a field. |
| A **policy / orchestration** change | Keep `tests/integration/` green (round-trip + cross-artifact integrity). Document any new action verb in `docs/api/actions.md`. |
| A **new validator / check** | Add a chaos mutation in `tests/chaos/test_chaos.py` (or a property in `test_property_fuzz.py`) that the new check catches, plus a filesystem-chaos case if it does I/O. |

Run `make test-py` (unit + scale + chaos) locally before pushing; the scale
layer runs in isolation with `pytest tests/scale -m scale`.

## Style

- Python: PEP 8 + type hints where practical; the repo will eventually wire
  `ruff` into CI.
- YAML controls: 2-space indent; lowercase keys; ISO-8601 dates.
- TypeScript SDK: strict mode is non-negotiable.
- Commits: imperative present tense (`feat: add SLSA L4 check`,
  `fix: handle empty crosswalk`).

## Signing your work

We don't require DCO sign-off today, but please use a real name and email on
commits. Evidence bundles built from the repo are signed automatically via
Sigstore + Fulcio; you don't need a personal signing key.

## Decision-making

For non-trivial changes — new domains, breaking schema bumps, deprecations —
open an issue first to discuss before writing a large PR. Small fixes can go
straight to PR.

Maintainers aim to triage new issues and PRs within 2 business days.

## Questions

Open a [Discussion](https://github.com/bobrapp/umbrella-govops/discussions)
(if enabled) or email `[email protected]`.
