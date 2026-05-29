from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_DOMAIN_PREFIX = {
    "data-governance": "DG-",
    "human-oversight": "HO-",
    "logging-traceability": "LOG-",
    "model-lifecycle": "ML-",
    "security-robustness": "SR-",
    "incident-response": "IR-",
    "transparency-disclosure": "TD-",
    "risk-management-system": "RMS-",
    "third-party-and-supply-chain": "TPS-",
    "post-market-monitoring": "PMM-",
}


@dataclass
class Control:
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return self.data.get("metadata", {}).get("id", "")

    @property
    def ucid(self) -> str:
        return self.data.get("metadata", {}).get("ucid", "")

    @property
    def status(self) -> str:
        return self.data.get("metadata", {}).get("status", "")

    @property
    def name(self) -> str:
        return self.data.get("metadata", {}).get("name", "")


class Controls:
    def __init__(self, repo_root: Path) -> None:
        self._root = repo_root
        self._items: list[Control] = []

    def load(self) -> Controls:
        domains = self._root / "domains"
        if not domains.exists():
            return self
        for p in domains.rglob("*.yaml"):
            try:
                doc = yaml.safe_load(p.read_text())
            except yaml.YAMLError:
                continue
            if isinstance(doc, dict) and doc.get("kind") == "Control":
                self._items.append(Control(doc))
        return self

    def all(self) -> list[Control]:
        return list(self._items)

    def by_id(self, control_id: str) -> Control | None:
        for c in self._items:
            if c.id == control_id:
                return c
        return None

    def by_ucid(self, ucid: str) -> list[Control]:
        return [c for c in self._items if c.ucid == ucid]

    def by_status(self, status: str) -> list[Control]:
        return [c for c in self._items if c.status == status]

    def by_domain(self, domain: str) -> list[Control]:
        prefix = _DOMAIN_PREFIX.get(domain, "")
        if not prefix:
            return []
        return [c for c in self._items if c.id.startswith(prefix)]
