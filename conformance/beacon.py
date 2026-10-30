"""Read what AIGovOps Beacon writes.

Accepted inputs (``umbrella-conformance bundle --beacon-bundle PATH``):

* a **Beacon audit bundle directory** — what ``beacon export`` /
  ``beacon-scan`` produce::

      manifest.json  manifest.sha256  receipts/YYYY-MM-DD.ndjson
      public_keys/<fpr>.pem  gate_decisions.json  ...

  ``manifest.sha256`` is recomputed over ``manifest.json``; the receipt count
  per file must match the manifest; receipt ids must be unique; every row of
  ``gate_decisions.json`` must point at a receipt that is present.
* a Beacon receipt file: ``.ndjson`` / ``.jsonl`` (one receipt per line)
* a ``.json`` file holding one receipt, a list, or ``{"entries": [...]}``
* any other directory: every ``*.ndjson``, ``*.jsonl`` and ``*.json`` in it

Nothing here verifies Beacon's Ed25519 signatures — that is ``beacon-verify``'s
job (``umbrella-conformance verify --beacon-bundle``). What it does refuse is a
bundle whose own manifest no longer matches its contents.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class BeaconInputError(ValueError):
    """Beacon output could not be read, or contradicts its own manifest."""


@dataclass
class BeaconInput:
    receipts: list[dict] = field(default_factory=list)  # EvidenceBundle.receipts[] shape
    raw: list[dict] = field(default_factory=list)  # verbatim Beacon receipts
    source_kind: str = "file"  # "beacon-bundle" | "directory" | "file"
    info: dict[str, Any] = field(default_factory=dict)


def is_beacon_bundle_dir(path: Path) -> bool:
    return path.is_dir() and (path / "manifest.json").is_file() and (path / "receipts").is_dir()


def load(path: Path) -> BeaconInput:
    path = Path(path)
    if is_beacon_bundle_dir(path):
        return _load_bundle_dir(path)
    if path.is_dir():
        files = sorted(
            [*path.glob("*.ndjson"), *path.glob("*.jsonl"), *path.glob("*.json")]
        )
        if not files:
            raise BeaconInputError(f"{path}: no .ndjson, .jsonl or .json receipts found")
        raw: list[dict] = []
        for f in files:
            raw.extend(_read_file(f))
        return _finish(raw, "directory", {"files": [f.name for f in files]})
    return _finish(_read_file(path), "file", {"files": [path.name]})


def _finish(raw: list[dict], kind: str, info: dict[str, Any]) -> BeaconInput:
    if not raw:
        raise BeaconInputError("no receipts found")
    ids = [_receipt_key(r) for r in raw]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise BeaconInputError(f"duplicate receipt id(s): {dupes[:5]}")
    return BeaconInput(
        receipts=[normalize_receipt(r) for r in raw], raw=raw, source_kind=kind, info=info
    )


def _read_lines(f: Path) -> list[dict]:
    out: list[dict] = []
    for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BeaconInputError(f"{f.name}: invalid JSON on line {n}: {exc}") from exc
        if not isinstance(obj, dict):
            raise BeaconInputError(f"{f.name}: line {n} is not a JSON object")
        out.append(obj)
    return out


def _read_file(f: Path) -> list[dict]:
    try:
        if f.suffix in (".ndjson", ".jsonl"):
            return _read_lines(f)
        text = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BeaconInputError(f"{f}: cannot read — {exc}") from exc
    try:
        entry = json.loads(text)
    except json.JSONDecodeError:
        # A .json file that is really NDJSON is common enough to accept.
        return _read_lines(f)
    if isinstance(entry, dict) and isinstance(entry.get("entries"), list):
        items = entry["entries"]
    elif isinstance(entry, list):
        items = entry
    else:
        items = [entry]
    if not all(isinstance(i, dict) for i in items):
        raise BeaconInputError(f"{f.name}: expected JSON object(s)")
    return items


def _load_bundle_dir(d: Path) -> BeaconInput:
    manifest_bytes = (d / "manifest.json").read_bytes()
    try:
        manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as exc:
        raise BeaconInputError(f"{d}/manifest.json: invalid JSON — {exc}") from exc

    sha_file = d / "manifest.sha256"
    if not sha_file.is_file():
        raise BeaconInputError(f"{d}: Beacon bundle has no manifest.sha256")
    recorded = sha_file.read_text().split()[0] if sha_file.read_text().split() else ""
    actual = hashlib.sha256(manifest_bytes).hexdigest()
    if recorded != actual:
        raise BeaconInputError(
            f"{d}: manifest.sha256 does not match manifest.json "
            f"(recorded {recorded[:12]}…, actual {actual[:12]}…)"
        )

    raw: list[dict] = []
    declared = manifest.get("receipt_files")
    if not isinstance(declared, dict):
        raise BeaconInputError(f"{d}: manifest.json has no receipt_files map")
    present = sorted((d / "receipts").glob("*.ndjson"))
    for f in present:
        rows = _read_lines(f)
        if f.name in declared and declared[f.name] != len(rows):
            raise BeaconInputError(
                f"{d}: receipts/{f.name} has {len(rows)} receipt(s); "
                f"manifest declares {declared[f.name]}"
            )
        raw.extend(rows)
    missing = sorted(set(declared) - {f.name for f in present})
    if missing:
        raise BeaconInputError(f"{d}: manifest lists receipt file(s) not present: {missing}")
    undeclared = sorted({f.name for f in present} - set(declared))
    if undeclared:
        raise BeaconInputError(
            f"{d}: receipt file(s) not listed in manifest.json receipt_files: {undeclared}"
        )

    ids = {r.get("id") for r in raw}
    gate_rows: list[dict] = []
    gd = d / "gate_decisions.json"
    if gd.is_file():
        gate_rows = json.loads(gd.read_text()) or []
        dangling = [g.get("receipt_id") for g in gate_rows if g.get("receipt_id") not in ids]
        if dangling:
            raise BeaconInputError(
                f"{d}: gate_decisions.json references receipt(s) not in the bundle: "
                f"{dangling[:5]}"
            )

    info = {
        "beacon_version": manifest.get("beacon_version"),
        "manifest_sha256": actual,
        "public_key_fingerprints": manifest.get("public_key_fingerprints", []),
        "receipt_files": [f.name for f in present],
        "gate_decisions": len(gate_rows),
    }
    return _finish(raw, "beacon-bundle", info)


def _receipt_key(entry: dict) -> str:
    return str(normalize_receipt(entry)["id"])


def normalize_receipt(entry: dict) -> dict:
    """Detect foundation vs runtime format and produce the EvidenceBundle
    receipts[] shape. Does NOT mutate the payload — it is embedded verbatim."""
    if "entry_sha256" in entry and (
        "prev_entry_sha256" in entry or "prev_sha256" in entry
    ):
        return {
            "id": entry["entry_sha256"],
            "format": "foundation",
            "payload": entry,
            "issued_at": (
                entry.get("timestamp_utc") or entry.get("ts") or entry.get("timestamp") or ""
            ),
        }
    rid = entry.get("id") or entry.get("receipt_id")
    if rid is None:
        rid = hashlib.sha256(
            json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
    issued = (
        entry.get("issued_at")
        or entry.get("ts_utc")
        or entry.get("ts")
        or entry.get("timestamp")
        or (entry.get("signature") or {}).get("ts")
        or ""
    )
    return {"id": str(rid), "format": "runtime", "payload": entry, "issued_at": issued}
