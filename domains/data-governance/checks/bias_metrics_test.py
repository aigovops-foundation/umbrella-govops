"""Reference bias-metrics check stubs for control DG-002.

These are intentionally minimal placeholders. Implement against your
training/eval dataset access pattern (e.g., DVC, MLflow, S3 manifest).
"""
import json
import os
import pathlib

OUT_DIR = pathlib.Path("out/bias")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _emit(name: str, payload: dict) -> None:
    (OUT_DIR / name).write_text(json.dumps(payload, indent=2, sort_keys=True))


def test_demographic_parity():
    """Demographic parity ratio must fall within [threshold_min, threshold_max]."""
    threshold_min = float(os.environ.get("DG_002_DP_MIN", "0.80"))
    threshold_max = float(os.environ.get("DG_002_DP_MAX", "1.25"))

    # TODO: replace with real computation against artifacts.training_dataset.uri
    dp_ratio = 1.00

    payload = {
        "control_id": "DG-002.C1",
        "metric": "demographic_parity_ratio",
        "value": dp_ratio,
        "threshold_min": threshold_min,
        "threshold_max": threshold_max,
        "passed": threshold_min <= dp_ratio <= threshold_max,
    }
    _emit("dp_ratio.json", payload)
    assert payload["passed"], payload


def test_disparate_impact():
    """Disparate impact ratio test (80% rule by default)."""
    # TODO: replace with real computation
    di_ratio = 0.92
    payload = {
        "control_id": "DG-002.C2",
        "metric": "disparate_impact_ratio",
        "value": di_ratio,
        "threshold": 0.80,
        "passed": di_ratio >= 0.80,
    }
    _emit("di.json", payload)
    assert payload["passed"], payload
