// Core type definitions mirroring conformance/schemas/*.json

export type Severity = "low" | "medium" | "high" | "critical";
export type ControlStatus = "draft" | "shadow" | "enforced" | "deprecated";
export type CheckStatus = "pass" | "warn" | "fail";
export type RiskTier = "unacceptable" | "high" | "limited" | "minimal" | "gpai";

export interface ControlMetadata {
  id: string;
  ucid: string;
  name: string;
  owner: string;
  severity: Severity;
  status: ControlStatus;
}

export interface ControlCheck {
  id: string;
  name: string;
  runner: "pytest" | "python" | "opa" | "rego" | "shell" | "container";
  script?: string;
  parameters?: Record<string, unknown>;
  evidence_outputs?: Array<{ type: string; path: string }>;
}

export interface Control {
  apiVersion: "govops.aigovops.org/v1";
  kind: "Control";
  metadata: ControlMetadata;
  satisfies?: Record<string, unknown>;
  applies_to?: { risk_tier?: RiskTier[]; modality?: string[] };
  inputs?: Array<{ path: string; required?: boolean }>;
  checks: ControlCheck[];
  on_fail?: { action?: string; notify?: string[]; open_poam?: boolean };
}

export interface CrosswalkUcid {
  id: string;
  title: string;
  nist_ai_rmf?: string[];
  eu_ai_act?: { articles?: string[]; annex_iv?: string[] };
  iso_42001?: string[];
  implementing_controls: string[];
  planned_controls?: string[];
}

export interface Crosswalk {
  apiVersion: "govops.aigovops.org/v1";
  kind: "Crosswalk";
  metadata: { name: string; description?: string };
  ucids: CrosswalkUcid[];
}

export interface EvidenceBundle {
  apiVersion: "govops.aigovops.org/v1";
  kind: "EvidenceBundle";
  metadata: { generatedAt: string; tool: string; repo?: string };
  checks: Array<{ name: string; status: CheckStatus; details?: string[] }>;
  signature?: { format: "cosign-keyless"; certificate?: string; signature?: string };
}

export type JourneyKey = "to-yes" | "at-yes" | "return-to-yes";

export interface JourneyStep {
  id: string;
  title: string;
  description: string;
  estimated_minutes?: number;
}

export interface Journey {
  key: JourneyKey;
  title: string;
  steps: JourneyStep[];
}
