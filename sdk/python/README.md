# umbrella-sdk (Python)

Python SDK for [Umbrella-GovOps](https://aigovops-foundation.github.io/umbrella-govops/). Mirrors the
[`@aigovops/umbrella-sdk`](../typescript/README.md) TypeScript surface.

```bash
pip install umbrella-sdk
```

## Quickstart

```python
from umbrella_sdk import umbrella

u = umbrella()  # defaults to cwd

# Controls
controls = u.controls.load().all()
dg = u.controls.by_id("DG-002")

# Crosswalk
u.crosswalk.load()
ucid = u.crosswalk.resolve("UCID-DATA-BIAS-001")

# Reverse lookup from a NIST identifier
matches = u.crosswalk.equivalents("nist_ai_rmf", "MEASURE-2.11")

# Journey
to_yes = u.journey.get("to-yes")
for step in to_yes.steps:
    print(f"  {step.id}: {step.title}")
```

## Develop

```bash
pip install -e ".[dev]"
pytest
```
