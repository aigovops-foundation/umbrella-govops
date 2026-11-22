# Umbrella-GovOps: notes for Claude

The programme layer of the AiGovOps stack: it compiles AI laws and standards into versioned
controls, each with a Unified Control Identifier (UCID), and binds runtime evidence to them.
Public repo, Apache-2.0.

## Layout

- `domains/<domain>/controls/`: the controls, as YAML contracts.
- `crosswalks/`, `frameworks/`, `UCID-REGISTRY.md`: how frameworks map onto UCIDs.
- `conformance/`, `sdk/`: the `umbrella-conformance` CLI and the SDKs.
- `tests/`: unit, conformance, scale, chaos and end-to-end suites.
- The landing page is published by `.github/workflows/pages.yml` on a push to `main`.

## Checks to run before a pull request

```bash
make install
make test-all
umbrella-conformance check . --check schema-valid --check crosswalk-resolved --check controls-have-checks
```

`make test-all` runs unit, scale, chaos and end-to-end. The end-to-end suite needs
`make install-e2e` first.

## Things that are easy to get wrong

- A UCID is an identifier other people cite. Never renumber, reuse or delete one. A UCID that
  is no longer wanted is marked `deprecated` and kept: see `UCID-REGISTRY.md`.
- A new control follows `conformance/schemas/control.schema.json` and has at least one check. A crosswalk row must
  resolve to an existing UCID.
- A statement about what a law or standard requires needs its citation. Do not paraphrase a
  legal text from memory.
- CODEOWNERS routes governance changes to named reviewers. Do not edit CODEOWNERS to get around it.

## Rules for an agent

- Agents propose, humans approve. Open a pull request; do not merge it, and do not push to `main`.
- Never sign, approve or rule on anything in a human's name.
- Secrets live in 1Password. Never print, paste or commit a key, token or private key.
- A check that was not run is reported as not run. Do not write "passes" from memory.
- Read `CONTRIBUTING.md` where there is one. It wins over this file where they differ.
