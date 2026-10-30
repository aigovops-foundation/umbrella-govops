"""schema-valid: validate every governed YAML document against its JSON Schema.

Two families of document are validated:

* Kubernetes-style documents with ``apiVersion``/``kind`` (Control, Crosswalk,
  GovernanceDomain, EvidenceBundle) under ``domains/``, ``crosswalks/`` and
  ``frameworks/``.
* Agent gate policies (``policy:`` + ``controls:`` + ``default: deny``) in the
  repository root, ``policies/`` and ``catalog/`` — the file a practitioner
  writes at level 200. In ``policies/`` and ``catalog/`` every YAML document
  without a ``kind`` is validated as a policy; in the root, any file named
  ``policy.yaml`` / ``*.policy.yaml`` or holding ``policy:`` / ``controls:``
  is. A misspelled key therefore fails validation instead of making the gate
  skip the file.

The check fails when any document is invalid, when any scanned YAML does not
parse, and when there is nothing to validate at all: a policy gate that
validated nothing has not passed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import yaml
from jsonschema import Draft202012Validator, ValidationError

from ..runner import CheckResult

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

# kind → schema file
KIND_TO_SCHEMA = {
    "Control": "control.schema.json",
    "Crosswalk": "crosswalk.schema.json",
    "EvidenceBundle": "evidence-bundle.schema.json",
    "GovernanceDomain": "domain.schema.json",
}
POLICY_SCHEMA = "policy.schema.json"

KIND_DIRS = ("domains", "crosswalks", "frameworks")
POLICY_DIRS = ("policies", "catalog")
YAML_SUFFIXES = (".yaml", ".yml")


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


def _is_policy_name(p: Path) -> bool:
    return p.name in ("policy.yaml", "policy.yml") or p.name.endswith(
        (".policy.yaml", ".policy.yml")
    )


def _looks_like_policy(doc: Any) -> bool:
    return isinstance(doc, dict) and "kind" not in doc and (
        "policy" in doc or "controls" in doc
    )


def _policy_candidates(repo: Path) -> Iterator[tuple[Path, bool]]:
    """Yield (path, in_policy_dir): root-level YAML (not recursive), then
    every YAML under policies/ and catalog/."""
    for p in sorted(repo.iterdir()):
        if p.is_file() and p.suffix in YAML_SUFFIXES:
            yield p, False
    for sub in POLICY_DIRS:
        d = repo / sub
        if d.is_dir():
            for p in sorted(d.rglob("*")):
                if p.is_file() and p.suffix in YAML_SUFFIXES:
                    yield p, True


def _read_yaml(p: Path) -> tuple[Any, str | None]:
    """Parse one YAML file; return (doc, error) and never raise on bad input."""
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")), None
    except yaml.YAMLError as exc:
        return None, f"invalid YAML — {exc}"
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"cannot read — {type(exc).__name__}: {exc}"


def _is_policy(p: Path, doc: Any, in_policy_dir: bool) -> bool:
    if _is_policy_name(p) or _looks_like_policy(doc):
        return True
    # Under policies/ and catalog/, anything that is not a kind-ed document is
    # a policy — so `polcy:` + `contorls:` is an invalid policy, not a skip.
    return in_policy_dir and not (isinstance(doc, dict) and "kind" in doc) and doc is not None


def policy_errors(doc: Any) -> list[str]:
    """Return human-readable errors for an agent gate policy (empty = valid)."""
    if not isinstance(doc, dict):
        return [f"$: expected a mapping, got {type(doc).__name__}"]
    validator = Draft202012Validator(_load_schema(POLICY_SCHEMA))
    errors = [
        f"{_err_path(e)}: {e.message}"
        for e in sorted(validator.iter_errors(doc), key=lambda e: [str(x) for x in e.absolute_path])
    ]
    actions = [
        c.get("action") for c in doc.get("controls") or [] if isinstance(c, dict)
    ]
    dupes = sorted({a for a in actions if a is not None and actions.count(a) > 1})
    for a in dupes:
        errors.append(f"$.controls: action {a!r} is declared more than once")
    return errors


def find_policies(repo: Path) -> list[tuple[Path, dict]]:
    """Return every *valid* agent gate policy in the repo (used by `bundle`)."""
    found: list[tuple[Path, dict]] = []
    for p, in_dir in _policy_candidates(repo):
        doc, err = _read_yaml(p)
        if err is None and _is_policy(p, doc, in_dir) and not policy_errors(doc):
            found.append((p, doc))
    return found


def check_schema_valid(repo: Path) -> CheckResult:
    details: list[str] = []
    errors = 0
    checked = 0

    def rel(p: Path) -> str:
        return str(p.relative_to(repo))

    # --- kind-based documents ------------------------------------------------
    yaml_paths: list[Path] = []
    for sub in KIND_DIRS:
        d = repo / sub
        if d.exists():
            yaml_paths.extend(
                p for p in sorted(d.rglob("*")) if p.is_file() and p.suffix in YAML_SUFFIXES
            )

    for p in yaml_paths:
        doc, err = _read_yaml(p)
        if err is not None:
            errors += 1
            details.append(f"{rel(p)}: {err}")
            continue
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind")
        if kind not in KIND_TO_SCHEMA:
            continue
        validator = Draft202012Validator(_load_schema(KIND_TO_SCHEMA[kind]))
        checked += 1
        for err in validator.iter_errors(doc):
            errors += 1
            details.append(f"{rel(p)}: {_err_path(err)}: {err.message}")

    # --- agent gate policies -------------------------------------------------
    n_policies = 0
    for p, in_dir in _policy_candidates(repo):
        doc, err = _read_yaml(p)
        if err is not None:
            errors += 1
            details.append(f"{rel(p)}: {err}")
            continue
        if not _is_policy(p, doc, in_dir):
            continue
        checked += 1
        n_policies += 1
        for msg in policy_errors(doc):
            errors += 1
            details.append(f"{rel(p)}: {msg}")

    if errors > 0:
        return CheckResult("schema-valid", "fail", details)
    if checked == 0:
        return CheckResult(
            "schema-valid",
            "fail",
            [
                "nothing to validate: no Control/Crosswalk/GovernanceDomain YAML under "
                "domains/, crosswalks/ or frameworks/, and no agent policy "
                "(policy.yaml, *.policy.yaml, or a YAML with `policy:` + `controls:`) "
                "in the root, policies/ or catalog/"
            ],
        )
    msg = f"{checked} document(s) validated against JSON Schema"
    if n_policies:
        msg += f" ({n_policies} agent policy file(s))"
    return CheckResult("schema-valid", "pass", [msg])


def _err_path(err: ValidationError) -> str:
    return "$" + "".join(f".{p}" if isinstance(p, str) else f"[{p}]" for p in err.absolute_path)
