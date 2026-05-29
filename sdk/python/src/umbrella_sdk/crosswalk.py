from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Ucid:
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return self.data.get("id", "")

    @property
    def title(self) -> str:
        return self.data.get("title", "")

    @property
    def implementing_controls(self) -> list[str]:
        return self.data.get("implementing_controls", []) or []


class CrosswalkClient:
    def __init__(self, repo_root: Path) -> None:
        self._root = repo_root
        self._data: dict[str, Any] | None = None

    def load(self) -> CrosswalkClient:
        p = self._root / "crosswalks" / "unified-control-id.yaml"
        if not p.exists():
            raise FileNotFoundError(f"crosswalk not found at {p}")
        self._data = yaml.safe_load(p.read_text())
        return self

    def ucids(self) -> list[Ucid]:
        if not self._data:
            return []
        return [Ucid(u) for u in self._data.get("ucids", []) if isinstance(u, dict)]

    def resolve(self, ucid_id: str) -> Ucid | None:
        for u in self.ucids():
            if u.id == ucid_id:
                return u
        return None

    def equivalents(self, framework: str, identifier: str) -> list[Ucid]:
        """Reverse-lookup: given a framework identifier, return matching UCIDs."""
        results: list[Ucid] = []
        for u in self.ucids():
            v = u.data.get(framework)
            if isinstance(v, list) and identifier in v:
                results.append(u)
            elif isinstance(v, dict):
                for arr in v.values():
                    if isinstance(arr, list) and identifier in arr:
                        results.append(u)
                        break
        return results
