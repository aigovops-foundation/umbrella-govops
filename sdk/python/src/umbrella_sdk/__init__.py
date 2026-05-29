"""umbrella_sdk: Python SDK for Umbrella-GovOps.

Mirrors the @aigovops/umbrella-sdk TypeScript surface.

    from umbrella_sdk import umbrella
    u = umbrella()
    controls = u.controls.load().all()
    ucid = u.crosswalk.load().resolve("UCID-DATA-BIAS-001")
    journey = u.journey.get("to-yes")
"""
from __future__ import annotations

from pathlib import Path

from .controls import Controls
from .crosswalk import CrosswalkClient
from .evidence import Evidence
from .journeys import journeys

__version__ = "0.1.0-alpha.1"


class Umbrella:
    def __init__(self, repo_root: str | Path | None = None) -> None:
        root = Path(repo_root) if repo_root else Path.cwd()
        self.controls = Controls(root)
        self.crosswalk = CrosswalkClient(root)
        self.evidence = Evidence()
        self.journey = journeys
        self.version = __version__


def umbrella(repo_root: str | Path | None = None) -> Umbrella:
    return Umbrella(repo_root)


__all__ = [
    "umbrella",
    "Umbrella",
    "Controls",
    "CrosswalkClient",
    "Evidence",
    "journeys",
    "__version__",
]
