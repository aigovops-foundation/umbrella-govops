import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import type { CheckStatus, EvidenceBundle } from "./types.js";

export interface BuildBundleInput {
  repo: string;
  checks: Array<{ name: string; status: CheckStatus; details?: string[] }>;
  tool?: string;
}

export class Evidence {
  /** Build an unsigned evidence bundle manifest. The conformance CLI is the
   * canonical producer in CI; this is for in-process testing + previews. */
  build(input: BuildBundleInput): EvidenceBundle {
    return {
      apiVersion: "govops.aigovops.org/v1",
      kind: "EvidenceBundle",
      metadata: {
        generatedAt: new Date().toISOString(),
        tool: input.tool ?? "@aigovops/umbrella-sdk",
        repo: input.repo,
      },
      checks: input.checks,
    };
  }

  /** Sigstore-keyless signing requires external cosign binary; we expose a
   * digest helper here and a CI-ready signing recipe in docs. */
  digest(bundle: EvidenceBundle): string {
    const canonical = JSON.stringify(bundle, Object.keys(bundle).sort());
    return crypto.createHash("sha256").update(canonical).digest("hex");
  }

  load(bundlePath: string): EvidenceBundle {
    const abs = path.resolve(bundlePath);
    if (!fs.existsSync(abs)) throw new Error(`bundle not found: ${abs}`);
    return JSON.parse(fs.readFileSync(abs, "utf8"));
  }
}
