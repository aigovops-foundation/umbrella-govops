"""Synthetic-repo generator for scale + chaos suites.

Produces a fully-formed Umbrella-GovOps repo of arbitrary size: N controls
across M domains, with a crosswalk that resolves cleanly.
"""
from __future__ import annotations

import random
from pathlib import Path

import yaml

DOMAIN_PREFIXES = [
    ("data-governance", "DG"),
    ("model-lifecycle", "ML"),
    ("human-oversight", "HO"),
    ("security-robustness", "SR"),
    ("logging-traceability", "LOG"),
    ("transparency-disclosure", "TD"),
    ("risk-management-system", "RMS"),
    ("post-market-monitoring", "PMM"),
    ("incident-response", "IR"),
    ("third-party-and-supply-chain", "TPS"),
]


def make_control(prefix: str, n: int, ucid: str) -> dict:
    return {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "Control",
        "metadata": {
            "id": f"{prefix}-{n:03d}",
            "ucid": ucid,
            "name": f"Synthetic {prefix} control {n}",
            "owner": "@synth",
            "severity": random.choice(["low", "medium", "high"]),
            "status": random.choice(["draft", "shadow", "enforced"]),
        },
        "satisfies": {"iso_42001": [{"clause": "A.7.4"}]},
        "checks": [
            {
                "id": f"{prefix}-{n:03d}.C1",
                "name": "synthetic pytest check",
                "runner": "pytest",
                "script": f"tests/synthetic/{prefix.lower()}_test.py::test_ok",
            }
        ],
    }


def make_domain_yaml(domain_id: str) -> dict:
    return {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "GovernanceDomain",
        "metadata": {
            "id": domain_id,
            "name": domain_id.replace("-", " ").title(),
            "owner": "@synth",
            "description": "Synthetic domain for harness testing.",
        },
        "risk_tier_applicability": ["high", "limited"],
    }


def generate_repo(
    root: Path,
    n_controls: int = 100,
    seed: int = 42,
    n_domains: int | None = None,
) -> dict:
    """Generate a synthetic Umbrella repo with N controls.

    Returns a stats dict: {n_controls, n_ucids, n_domains}.
    """
    random.seed(seed)
    root.mkdir(parents=True, exist_ok=True)
    (root / "crosswalks").mkdir(exist_ok=True)
    (root / "domains").mkdir(exist_ok=True)
    (root / "frameworks").mkdir(exist_ok=True)

    domains = DOMAIN_PREFIXES[: n_domains or len(DOMAIN_PREFIXES)]
    per_domain = max(1, n_controls // len(domains))

    ucids: list[dict] = []
    total = 0

    for domain_id, prefix in domains:
        domain_root = root / "domains" / domain_id
        (domain_root / "controls").mkdir(parents=True, exist_ok=True)
        (domain_root / "domain.yaml").write_text(
            yaml.safe_dump(make_domain_yaml(domain_id), sort_keys=False)
        )
        ucid = f"UCID-{prefix}-SYNTH-001"
        impl: list[str] = []
        for i in range(1, per_domain + 1):
            total += 1
            if total > n_controls:
                break
            ctrl = make_control(prefix, i, ucid)
            (domain_root / "controls" / f"{prefix}-{i:03d}.yaml").write_text(
                yaml.safe_dump(ctrl, sort_keys=False)
            )
            impl.append(f"{prefix}-{i:03d}")
        ucids.append(
            {
                "id": ucid,
                "title": f"Synthetic {prefix} UCID",
                "nist_ai_rmf": ["MEASURE-2.11"],
                "iso_42001": ["A.7.4"],
                "implementing_controls": impl,
            }
        )

    crosswalk = {
        "apiVersion": "govops.aigovops.org/v1",
        "kind": "Crosswalk",
        "metadata": {
            "name": "unified-control-id",
            "description": "Synthetic crosswalk",
        },
        "ucids": ucids,
    }
    (root / "crosswalks" / "unified-control-id.yaml").write_text(
        yaml.safe_dump(crosswalk, sort_keys=False)
    )

    return {"n_controls": total, "n_ucids": len(ucids), "n_domains": len(domains)}
