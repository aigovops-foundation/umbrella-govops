# @aigovops/umbrella-sdk

TypeScript SDK for [Umbrella-GovOps](https://aigovops-foundation.github.io/umbrella-govops/).

```bash
npm install @aigovops/umbrella-sdk
```

## Quickstart

```ts
import { umbrella } from "@aigovops/umbrella-sdk";

const u = umbrella(); // defaults to cwd

// Load every Control YAML under domains/
const controls = u.controls.load().all();

// Find a single control by ID
const dg = u.controls.byId("DG-002");

// Resolve a Unified Control ID across frameworks
u.crosswalk.load();
const ucid = u.crosswalk.resolve("UCID-DATA-BIAS-001");

// Reverse lookup: given a NIST identifier, find every framework equivalent
const matches = u.crosswalk.equivalents("nist_ai_rmf", "MEASURE-2.11");

// Walk a practitioner journey
const toYes = u.journey.get("to-yes");
console.log(toYes.steps.map((s) => s.title));
```

## API surface

| Namespace | Method | Returns |
|---|---|---|
| `controls` | `load()`, `all()`, `byId(id)`, `byUcid(ucid)`, `byStatus(s)`, `byDomain(d)` | `Control[]` / `Control` |
| `crosswalk` | `load()`, `ucids()`, `resolve(ucid)`, `byFramework(name)`, `equivalents(framework, id)` | `CrosswalkUcid[]` |
| `evidence` | `build({...})`, `digest(b)`, `load(path)` | `EvidenceBundle` / `string` |
| `journey` | `get(key)`, `list()` | `Journey` |

Types are exported as named exports. See `src/types.ts`.

## Why a stub SDK?

The site shows this `import` already. Shipping a buildable stub now means:
- Codebases can pin a real version and depend on the API contract.
- The Conformance CLI (`umbrella-conformance`) remains the canonical producer of evidence; the SDK is the canonical consumer.
- Future remote backends (registry API, hosted crosswalk) slot in behind the same surface.

## Build

```bash
npm install
npm run build
npm test
```
