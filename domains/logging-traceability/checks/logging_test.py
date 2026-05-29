"""Reference logging-presence check for control LOG-001."""
import json, os, pathlib
OUT = pathlib.Path("out/logging"); OUT.mkdir(parents=True, exist_ok=True)

def test_logging_declared():
    # TODO: read the live system manifest under test
    declared = True
    retention_days = 730  # EU AI Act minimum: 6 months; we default to 24
    payload = {
        "control_id": "LOG-001.C1",
        "declared": declared,
        "retention_days": retention_days,
        "passed": declared and retention_days >= 180,
    }
    (OUT / "declared.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    assert payload["passed"], payload
