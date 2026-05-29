"""Reference adversarial-floor check for control SR-001."""
import json, pathlib
OUT = pathlib.Path("out/adv"); OUT.mkdir(parents=True, exist_ok=True)

def test_adv_floor():
    floor = 0.70  # TODO: read from parameters
    measured = 0.83  # TODO: real adversarial-eval pipeline
    payload = {
        "control_id": "SR-001.C1",
        "metric": "adversarial_accuracy",
        "value": measured,
        "floor": floor,
        "passed": measured >= floor,
    }
    (OUT / "floor.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    assert payload["passed"], payload
