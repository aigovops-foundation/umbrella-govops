"""Scale tests — synthesize 1k+ controls and assert the conformance CLI
holds linear-ish throughput and never regresses past hard SLA thresholds.

Run with:
    pytest tests/scale -v
    SCALE_N=10000 pytest tests/scale -v   # 10k-control stress run
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from conformance.checks import (
    check_controls_have_checks,
    check_crosswalk_resolved,
    check_schema_valid,
)
from tests._lib.synth import generate_repo

# SLA: validating 1000 controls must complete in under 5 seconds wall-clock
SLA_PER_THOUSAND_SECONDS = 5.0


@pytest.mark.parametrize("n", [100, 1000])
def test_scale_full_check_suite(tmp_path: Path, n: int) -> None:
    """At N controls, the full check suite must pass and meet SLA."""
    stats = generate_repo(tmp_path, n_controls=n, seed=n)
    assert stats["n_controls"] >= min(n, 10)

    t0 = time.perf_counter()
    r1 = check_schema_valid(tmp_path)
    r2 = check_crosswalk_resolved(tmp_path)
    r3 = check_controls_have_checks(tmp_path)
    elapsed = time.perf_counter() - t0

    assert r1.status == "pass", r1.details[:5]
    assert r2.status == "pass", r2.details[:5]
    assert r3.status == "pass", r3.details[:5]

    sla = SLA_PER_THOUSAND_SECONDS * max(1, n / 1000)
    assert elapsed < sla, f"scale@{n} took {elapsed:.2f}s, SLA {sla:.2f}s"

    _record_metric(n, elapsed)


def test_scale_10k_if_requested(tmp_path: Path) -> None:
    """Opt-in 10k stress test. Skip unless SCALE_N=10000 is set."""
    target = int(os.environ.get("SCALE_N", "0"))
    if target < 10000:
        pytest.skip("set SCALE_N=10000 to run the 10k stress test")
    stats = generate_repo(tmp_path, n_controls=target, seed=target)
    t0 = time.perf_counter()
    r1 = check_schema_valid(tmp_path)
    r2 = check_crosswalk_resolved(tmp_path)
    elapsed = time.perf_counter() - t0
    assert r1.status == "pass"
    assert r2.status == "pass"
    sla = SLA_PER_THOUSAND_SECONDS * (target / 1000)
    assert elapsed < sla, f"scale@{target} took {elapsed:.2f}s, SLA {sla:.2f}s"
    _record_metric(target, elapsed)


def _record_metric(n: int, elapsed: float) -> None:
    report = Path(__file__).resolve().parents[2] / "reports" / "harness" / "scale.jsonl"
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("a") as f:
        f.write(json.dumps({"n_controls": n, "elapsed_s": round(elapsed, 4)}) + "\n")
