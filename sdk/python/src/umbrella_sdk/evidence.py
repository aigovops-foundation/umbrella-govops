from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any


class Evidence:
    def build(
        self,
        repo: str,
        checks: list[dict[str, Any]],
        tool: str = "umbrella-sdk",
    ) -> dict[str, Any]:
        return {
            "apiVersion": "govops.aigovops.org/v1",
            "kind": "EvidenceBundle",
            "metadata": {
                "generatedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "tool": tool,
                "repo": repo,
            },
            "checks": checks,
        }

    def digest(self, bundle: dict[str, Any]) -> str:
        canonical = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def load(self, bundle_path: str | Path) -> dict[str, Any]:
        p = Path(bundle_path).resolve()
        return json.loads(p.read_text())
