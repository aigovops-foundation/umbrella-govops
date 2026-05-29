import type { Journey, JourneyKey } from "./types.js";

const JOURNEYS: Record<JourneyKey, Journey> = {
  "to-yes": {
    key: "to-yes",
    title: "Get to Yes",
    steps: [
      {
        id: "scope",
        title: "Scope your system",
        description:
          "Declare modality, risk tier, deployment context, and target frameworks.",
        estimated_minutes: 3,
      },
      {
        id: "select-controls",
        title: "Pick the minimum control set",
        description:
          "Umbrella selects the controls satisfied by your declared frameworks via UCID.",
        estimated_minutes: 2,
      },
      {
        id: "first-evidence",
        title: "Run the first check matrix",
        description:
          "Execute `umbrella-conformance check` locally and resolve any failing controls.",
        estimated_minutes: 5,
      },
      {
        id: "sign-and-ship",
        title: "Sign the bundle and ship",
        description:
          "Cosign-keyless sign your first evidence bundle and tag the release.",
        estimated_minutes: 5,
      },
    ],
  },
  "at-yes": {
    key: "at-yes",
    title: "Stay at Yes",
    steps: [
      {
        id: "drift-watch",
        title: "Drift detection",
        description:
          "Nightly diff between declared controls and shipped evidence; alerts on regression.",
      },
      {
        id: "framework-updates",
        title: "Track framework deltas",
        description:
          "Subscribe to crosswalk updates as new framework versions land.",
      },
      {
        id: "audit-ready",
        title: "Continuous audit-ready posture",
        description:
          "Every PR produces a signed evidence bundle archivable for regulators.",
      },
    ],
  },
  "return-to-yes": {
    key: "return-to-yes",
    title: "Return to Yes",
    steps: [
      {
        id: "incident",
        title: "Declare the incident",
        description:
          "Open a POAM (plan of action & milestones) referencing the failed control(s).",
      },
      {
        id: "scope-blast",
        title: "Blast-radius scope",
        description:
          "Use the crosswalk to identify every framework obligation affected.",
      },
      {
        id: "remediate",
        title: "Remediate and re-sign",
        description:
          "Patch, re-run conformance, sign the remediation bundle, close the POAM.",
      },
      {
        id: "post-mortem",
        title: "Publish post-mortem",
        description:
          "Add the incident to evidence/post-mortems/ — auditors love this.",
      },
    ],
  },
};

export const journeys = {
  get(key: JourneyKey): Journey {
    const j = JOURNEYS[key];
    if (!j) throw new Error(`unknown journey key: ${key}`);
    return j;
  },
  list(): Journey[] {
    return Object.values(JOURNEYS);
  },
};
