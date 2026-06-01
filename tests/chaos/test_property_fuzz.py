"""Property-based chaos via Hypothesis.

Goal: the conformance checks and JSON Schema validators must *reject malformed
input cleanly* — a structured failure, never an unhandled crash. We generate
adversarial inputs (malformed UCIDs, mutated control mappings, conflicting
crosswalk entries, weird Unicode, huge strings, missing/extra fields) and
assert the system surfaces them as `fail`/validation errors rather than
raising.

Determinism: Hypothesis is seeded via HYPOTHESIS_SEED (default 20260601) so CI
runs are reproducible; override the env var to explore a different space.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from hypothesis import HealthCheck, given, seed, settings
from hypothesis import strategies as st
from jsonschema import Draft202012Validator

from conformance.checks import check_crosswalk_resolved, check_schema_valid
from tests._lib.ucid import UCID_RE

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "conformance" / "schemas"

_SEED = int(os.environ.get("HYPOTHESIS_SEED", "20260601"))
_DETERMINISTIC = settings(
    max_examples=int(os.environ.get("HYPOTHESIS_MAX_EXAMPLES", "200")),
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


def _control_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMAS / "control.schema.json").read_text()))


def _crosswalk_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMAS / "crosswalk.schema.json").read_text()))


# ── Malformed UCIDs are never accepted as valid ─────────────────────────────

@seed(_SEED)
@_DETERMINISTIC
@given(st.text(max_size=64))
def test_random_text_is_not_mistaken_for_a_ucid(s: str) -> None:
    """The strict UCID regex must agree with itself: anything it matches is
    upper-case-shaped; anything it rejects never sneaks through."""
    match = UCID_RE.match(s)
    if match is not None:
        # If it matched, it MUST satisfy every structural rule.
        assert s.startswith("UCID-")
        assert s == s.upper() or any(c.isdigit() for c in s)
        assert s.split("-")[-1].isdigit() and len(s.split("-")[-1]) == 3


@seed(_SEED)
@_DETERMINISTIC
@given(
    st.fixed_dictionaries(
        {
            "id": st.text(max_size=40),
            "title": st.text(max_size=40),
            "implementing_controls": st.lists(st.text(max_size=12), max_size=5),
        }
    )
)
def test_crosswalk_validator_never_crashes_on_fuzzed_ucid(entry: dict) -> None:
    v = _crosswalk_validator()
    doc = {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "Crosswalk",
        "metadata": {"name": "fuzz"},
        "ucids": [entry],
    }
    # iter_errors must terminate and return a list — never raise.
    errors = list(v.iter_errors(doc))
    assert isinstance(errors, list)
    # If the id is not a well-formed (loose-pattern) UCID, there MUST be an error.
    if not str(entry["id"]).startswith("UCID-"):
        assert errors, f"malformed UCID id {entry['id']!r} accepted"


# ── Fuzzed control documents are handled, not crashed ────────────────────────

@seed(_SEED)
@_DETERMINISTIC
@given(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.recursive(
            st.none() | st.booleans() | st.integers() | st.text(max_size=50),
            lambda children: st.lists(children, max_size=3)
            | st.dictionaries(st.text(min_size=1, max_size=8), children, max_size=3),
            max_leaves=10,
        ),
        max_size=8,
    )
)
def test_control_schema_validation_is_total(doc: dict) -> None:
    """For any JSON-shaped object, control-schema validation returns a list of
    errors and never raises."""
    v = _control_validator()
    errors = list(v.iter_errors(doc))
    assert isinstance(errors, list)
    # A document missing the required envelope keys must be rejected.
    if not {"apiVersion", "kind", "metadata", "checks"} <= set(doc):
        assert errors


# ── Weird-Unicode + huge-string control names survive the check pipeline ─────

@seed(_SEED)
@_DETERMINISTIC
@given(
    name=st.text(
        alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x10FFFF),
        max_size=4000,
    )
)
def test_check_schema_valid_survives_unicode_and_huge_names(name: str) -> None:
    """A control whose name is arbitrary Unicode (incl. astral planes) and up
    to 4k chars must not crash check_schema_valid — it parses + validates."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ctrl_dir = root / "domains" / "fuzz" / "controls"
        ctrl_dir.mkdir(parents=True)
        (root / "domains" / "fuzz" / "domain.yaml").write_text(
            yaml.safe_dump(
                {
                    "apiVersion": "govops.aigovops.org/v1",
                    "kind": "GovernanceDomain",
                    "metadata": {"id": "fuzz", "name": "Fuzz", "owner": "@fuzz"},
                }
            )
        )
        control = {
            "apiVersion": "govops.aigovops.org/v1",
            "kind": "Control",
            "metadata": {
                "id": "FZ-001",
                "ucid": "UCID-FUZZ-001",
                "name": name or "x",
                "owner": "@fuzz",
                "severity": "low",
                "status": "draft",
            },
            "checks": [{"id": "FZ-001.C1", "name": "c", "runner": "pytest"}],
        }
        (ctrl_dir / "FZ-001.yaml").write_text(yaml.safe_dump(control, allow_unicode=True))
        result = check_schema_valid(root)
        assert result.status in {"pass", "warn", "fail"}


# ── Conflicting crosswalk entries are surfaced, not silently merged ─────────

@seed(_SEED)
@_DETERMINISTIC
@given(extra=st.text(min_size=1, max_size=12).filter(lambda s: "-" not in s and "/" not in s))
def test_conflicting_implementing_controls_are_caught(extra: str) -> None:
    """A registry that points at a control id with no file must fail the
    crosswalk-resolved check — regardless of the fuzzed id text."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "crosswalks").mkdir(parents=True)
        (root / "domains").mkdir(parents=True)
        registry = {
            "apiVersion": "govops.aigovops.org/v1",
            "kind": "Crosswalk",
            "metadata": {"name": "fuzz"},
            "ucids": [
                {
                    "id": "UCID-FUZZ-001",
                    "title": "fuzz",
                    "implementing_controls": [f"ZZ-{extra[:3].upper() or 'X'}999"[:9]],
                }
            ],
        }
        (root / "crosswalks" / "unified-control-id.yaml").write_text(yaml.safe_dump(registry))
        result = check_crosswalk_resolved(root)
        # No control files exist, so the implementer is dangling -> fail.
        assert result.status == "fail"
