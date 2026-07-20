# Umbrella-GovOps Test Harness

End-to-end test harness for the Umbrella-GovOps governance compiler. The
harness has four pillars — **unit**, **scale**, **chaos**, **e2e** — each
runnable in isolation locally and wired into CI on every PR plus a nightly
schedule.

```
tests/
├── _lib/          # shared synthetic-repo generator (synth.py)
├── unit/          # pytest unit tests — CLI surface + JSON schema strictness
├── conformance/   # existing repo-level conformance checks
├── scale/         # 100 / 1000 / 10k synthetic-control throughput tests
├── chaos/         # mutation tests — assert every break is caught
└── e2e/           # Playwright smoke tests against the live landing page
```

All artifacts land in `reports/harness/` (JUnit XML, JSONL run logs,
Playwright HTML/JSON reports, screenshots, traces).

## Quick start

```bash
make install        # python deps
make install-e2e    # Playwright + Chromium
make test-all       # everything: unit + scale + chaos + e2e
make harness-report # show artifact paths
```

Run a single suite:

```bash
make test-unit
make test-scale
make test-chaos
make test-e2e
```

The opt-in 10k-control scale run (heavy — ~30s wall):

```bash
make test-scale-10k
```

## Suite reference

### 1. Unit — `tests/unit/`

| File | Coverage |
| --- | --- |
| `test_cli.py` | `umbrella-conformance` command surface: `--version`, `check` (on the real repo + JSON output + name filter), `init` scaffolder, `bundle` tarball generation. |
| `test_schemas_strict.py` | JSON Schemas reject the exact bad inputs they advertise as invalid: missing metadata, lowercase / non-pattern IDs, empty `checks` lists, unknown `runner` enums, malformed UCID patterns. Also validates every shipped schema is itself a valid Draft 2020-12 schema. |

Runs via `pytest` against the live `conformance/` package; no fixtures
required beyond what the repo already ships.

### 2. Scale — `tests/scale/`

`test_scale.py` builds synthetic repositories of N controls + 10 domains
using `tests/_lib/synth.py`, runs the full check suite end-to-end, and
asserts an SLA:

| N | Default | SLA |
| --- | --- | --- |
| 100 | always | <2 s |
| 1 000 | always | <5 s / 1 000 |
| 10 000 | opt-in via `SCALE_N=10000` | <5 s / 1 000 |

Throughput numbers are appended to `reports/harness/scale.jsonl` so the
nightly run produces a long-running trend line you can graph later.

### 3. Chaos — `tests/chaos/`

Mutation testing. Six deterministic mutators each produce a known-broken
repo; the test asserts that `umbrella-conformance check` exits non-zero on
every one of them.

| Mutator | What it breaks | Check it must trip |
| --- | --- | --- |
| `break_yaml` | inserts invalid YAML in a control file | `schema-valid` (parser layer) |
| `invalid_runner` | sets `runner: blender` | `schema-valid` (enum) |
| `strip_checks` | empties the `checks:` list | `controls-have-checks` |
| `bad_id` | renames a control id to lowercase | `schema-valid` (pattern) |
| `orphan_ucid` | references a UCID with no implementers | `crosswalk-resolved` |
| `dangling_impl` | implementer points to a non-existent control id | `crosswalk-resolved` |

A `random_walk_session` test stacks 1–3 mutations per session for a fixed
number of iterations to catch any combination that silently passes.

Per-mutation outcomes are appended to `reports/harness/chaos.jsonl`.

**Adding a new mutator:**

1. Add a function in `tests/chaos/test_chaos.py` that takes the synth repo
   path and applies the mutation in place.
2. Register it in the `MUTATIONS` dict at the top of the file.
3. Either it trips an existing check (preferred) or you add the matching
   check to `conformance/checks/`.

### 4. E2E — `tests/e2e/`

Playwright smoke tests against `https://aigovops-foundation.github.io/umbrella-govops/`
(override with `BASE_URL=...`). Ten tests cover:

- Hero h1 still carries the core promise.
- Medallion SVG renders in the hero.
- `#framework-table` lists 38 framework rows (header + 38 ≈ 39 `<tr>`).
- `#roles` section has 6 practitioner-path cards.
- Oath ribbon copy is still on the page.
- Every primary nav anchor (`#roles`, `#frameworks`, …) resolves to a real
  section.
- `<title>` brands the project.
- No uncaught JS exceptions on initial render.
- Sister-site link to `aigovops-beacon` is reachable when present.
- A full-page screenshot is attached to the run report.

Artifacts: HTML report (`reports/harness/playwright-html/index.html`),
JSON results, traces and failure screenshots under
`reports/harness/playwright-artifacts/`.

## CI integration

See `.github/workflows/harness.yml`. Jobs run on:

- every PR to `main`
- every push to `main`
- nightly schedule at `17 9 * * *` UTC (~02:17 PT)
- manual `workflow_dispatch`

The 10k-control scale job runs **only** nightly or on manual dispatch — too
expensive for the PR critical path.

Each job uploads its own artifact bundle, and a final
`harness-summary` job writes a one-line status table to the GitHub Actions
Step Summary so a single glance tells you which pillar broke.

## Local debugging tips

- Playwright failed in CI but you can't reproduce locally? Pull the trace
  artifact and run `npx playwright show-trace path/to/trace.zip`.
- Scale SLA regression? Re-run with `SCALE_N=...` and compare against
  prior entries in `reports/harness/scale.jsonl`.
- A chaos mutator no longer trips its check? That means the check is now
  too permissive — investigate the check, not the mutator.

## What the harness is **not**

- It is not a substitute for human review of governance content.
- It does not validate the *semantic* correctness of framework mappings;
  that lives in `crosswalks/` review.
- It does not exercise authenticated flows on the live site (none exist).

## See also

- `conformance/` — the CLI under test
- `sdk/python/` & `sdk/typescript/` — language SDKs
- `crosswalks/unified-control-id.yaml` — UCID registry the chaos suite
  mutates copies of
- Root `README.md` § Testing — top-level entry point
