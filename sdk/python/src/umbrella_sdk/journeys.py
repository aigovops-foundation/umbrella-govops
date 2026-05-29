from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

JourneyKey = Literal["to-yes", "at-yes", "return-to-yes"]


@dataclass(frozen=True)
class JourneyStep:
    id: str
    title: str
    description: str
    estimated_minutes: int | None = None


@dataclass(frozen=True)
class Journey:
    key: JourneyKey
    title: str
    steps: tuple[JourneyStep, ...]


_JOURNEYS: dict[str, Journey] = {
    "to-yes": Journey(
        key="to-yes",
        title="Get to Yes",
        steps=(
            JourneyStep(
                "scope",
                "Scope your system",
                "Declare modality, risk tier, deployment context, and target frameworks.",
                3,
            ),
            JourneyStep(
                "select-controls",
                "Pick the minimum control set",
                "Umbrella selects the controls satisfied by your declared frameworks via UCID.",
                2,
            ),
            JourneyStep(
                "first-evidence",
                "Run the first check matrix",
                "Execute `umbrella-conformance check` locally and resolve any failing controls.",
                5,
            ),
            JourneyStep(
                "sign-and-ship",
                "Sign the bundle and ship",
                "Cosign-keyless sign your first evidence bundle and tag the release.",
                5,
            ),
        ),
    ),
    "at-yes": Journey(
        key="at-yes",
        title="Stay at Yes",
        steps=(
            JourneyStep(
                "drift-watch",
                "Drift detection",
                "Nightly diff between declared controls and shipped evidence; alerts on regression.",
            ),
            JourneyStep(
                "framework-updates",
                "Track framework deltas",
                "Subscribe to crosswalk updates as new framework versions land.",
            ),
            JourneyStep(
                "audit-ready",
                "Continuous audit-ready posture",
                "Every PR produces a signed evidence bundle archivable for regulators.",
            ),
        ),
    ),
    "return-to-yes": Journey(
        key="return-to-yes",
        title="Return to Yes",
        steps=(
            JourneyStep(
                "incident",
                "Declare the incident",
                "Open a POAM (plan of action & milestones) referencing the failed control(s).",
            ),
            JourneyStep(
                "scope-blast",
                "Blast-radius scope",
                "Use the crosswalk to identify every framework obligation affected.",
            ),
            JourneyStep(
                "remediate",
                "Remediate and re-sign",
                "Patch, re-run conformance, sign the remediation bundle, close the POAM.",
            ),
            JourneyStep(
                "post-mortem",
                "Publish post-mortem",
                "Add the incident to evidence/post-mortems/ — auditors love this.",
            ),
        ),
    ),
}


class _JourneysAPI:
    def get(self, key: str) -> Journey:
        if key not in _JOURNEYS:
            raise KeyError(f"unknown journey key: {key}")
        return _JOURNEYS[key]

    def list(self) -> list[Journey]:
        return list(_JOURNEYS.values())


journeys = _JourneysAPI()
