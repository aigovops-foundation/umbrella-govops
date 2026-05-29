"""Chaos monkey — randomly mutate a generated synthetic repo and assert
that the conformance CLI catches every mutation as a failure.

Property: for any non-empty mutation drawn from MUTATIONS, the check suite
MUST surface at least one failing check.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Callable

import pytest
import yaml

from conformance.checks import (
    check_controls_have_checks,
    check_crosswalk_resolved,
    check_schema_valid,
)
from tests._lib.synth import generate_repo

Mutator = Callable[[Path, random.Random], str]


def _pick_control(root: Path, rng: random.Random) -> Path:
    controls = list((root / "domains").rglob("*.yaml"))
    controls = [p for p in controls if "controls" in str(p)]
    return rng.choice(controls)


def mutation_break_yaml(root: Path, rng: random.Random) -> str:
    """Truncate a control YAML mid-line."""
    p = _pick_control(root, rng)
    text = p.read_text()
    p.write_text(text[: max(20, len(text) // 2)] + "\n  ::: not valid yaml :::")
    return f"truncated {p.name}"


def mutation_invalid_runner(root: Path, rng: random.Random) -> str:
    """Set runner to an unsupported value."""
    p = _pick_control(root, rng)
    doc = yaml.safe_load(p.read_text())
    doc["checks"][0]["runner"] = "javascript"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return f"bad runner in {p.name}"


def mutation_strip_checks(root: Path, rng: random.Random) -> str:
    """Empty the checks array."""
    p = _pick_control(root, rng)
    doc = yaml.safe_load(p.read_text())
    doc["checks"] = []
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return f"no checks in {p.name}"


def mutation_bad_id(root: Path, rng: random.Random) -> str:
    """Change control id to lowercase (violates pattern)."""
    p = _pick_control(root, rng)
    doc = yaml.safe_load(p.read_text())
    doc["metadata"]["id"] = "lowercase-001"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return f"bad id in {p.name}"


def mutation_orphan_ucid(root: Path, rng: random.Random) -> str:
    """Point a control at a ucid that doesn't exist in the crosswalk."""
    p = _pick_control(root, rng)
    doc = yaml.safe_load(p.read_text())
    doc["metadata"]["ucid"] = "UCID-DOES-NOT-EXIST"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return f"orphan ucid in {p.name}"


def mutation_dangling_impl(root: Path, rng: random.Random) -> str:
    """Add a non-existent implementing_controls id to the crosswalk."""
    p = root / "crosswalks" / "unified-control-id.yaml"
    doc = yaml.safe_load(p.read_text())
    doc["ucids"][0]["implementing_controls"].append("ZZ-999")
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return "dangling implementing_controls"


MUTATIONS: list[tuple[str, Mutator]] = [
    ("break_yaml", mutation_break_yaml),
    ("invalid_runner", mutation_invalid_runner),
    ("strip_checks", mutation_strip_checks),
    ("bad_id", mutation_bad_id),
    ("orphan_ucid", mutation_orphan_ucid),
    ("dangling_impl", mutation_dangling_impl),
]


@pytest.mark.parametrize("name,mutate", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_chaos_each_mutation_is_caught(
    tmp_path: Path, name: str, mutate: Mutator
) -> None:
    """Every defined mutation must be caught by at least one check."""
    rng = random.Random(name)
    generate_repo(tmp_path, n_controls=30, seed=hash(name) & 0xFFFF)
    description = mutate(tmp_path, rng)

    results = [
        check_schema_valid(tmp_path),
        check_crosswalk_resolved(tmp_path),
        check_controls_have_checks(tmp_path),
    ]
    any_failed = any(r.status == "fail" for r in results)
    assert any_failed, (
        f"chaos mutation {name!r} ({description}) was NOT caught — "
        f"results: {[(r.name, r.status) for r in results]}"
    )

    _record_chaos(name, description, [(r.name, r.status) for r in results])


def test_chaos_random_walk_session(tmp_path: Path) -> None:
    """Random walk: apply 5 random mutations in sequence and assert each step
    keeps the suite failing or fails harder. Never silently passes."""
    rng = random.Random(20260529)
    generate_repo(tmp_path, n_controls=50, seed=20260529)
    base = sum(
        1
        for r in (
            check_schema_valid(tmp_path),
            check_crosswalk_resolved(tmp_path),
            check_controls_have_checks(tmp_path),
        )
        if r.status == "fail"
    )
    assert base == 0, "fresh synthetic repo should start green"

    for step in range(5):
        name, mutate = rng.choice(MUTATIONS)
        mutate(tmp_path, rng)
        results = [
            check_schema_valid(tmp_path),
            check_crosswalk_resolved(tmp_path),
            check_controls_have_checks(tmp_path),
        ]
        n_failed = sum(1 for r in results if r.status == "fail")
        assert n_failed >= 1, (
            f"step {step}: after {name} mutation the suite did not catch anything"
        )


def _record_chaos(name: str, description: str, statuses) -> None:
    out = Path(__file__).resolve().parents[2] / "reports" / "harness" / "chaos.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as f:
        f.write(
            json.dumps(
                {"mutation": name, "description": description, "results": statuses}
            )
            + "\n"
        )
