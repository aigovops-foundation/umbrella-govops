import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";
import type { Crosswalk, CrosswalkUcid } from "./types.js";

export class CrosswalkClient {
  private data: Crosswalk | null = null;

  constructor(private repoRoot: string) {}

  load(): this {
    const p = path.join(
      this.repoRoot,
      "crosswalks",
      "unified-control-id.yaml"
    );
    if (!fs.existsSync(p)) {
      throw new Error(`crosswalk not found at ${p}`);
    }
    this.data = yaml.load(fs.readFileSync(p, "utf8")) as Crosswalk;
    return this;
  }

  ucids(): CrosswalkUcid[] {
    return this.data?.ucids ?? [];
  }

  resolve(ucid: string): CrosswalkUcid | undefined {
    return this.ucids().find((u) => u.id === ucid);
  }

  byFramework(framework: "nist_ai_rmf" | "iso_42001" | "eu_ai_act"): CrosswalkUcid[] {
    return this.ucids().filter((u) => {
      const v = (u as unknown as Record<string, unknown>)[framework];
      if (Array.isArray(v)) return v.length > 0;
      if (v && typeof v === "object") return Object.keys(v).length > 0;
      return false;
    });
  }

  /** Given an obligation in framework A (e.g. NIST "MEASURE-2.11"), return the
   * UCIDs that satisfy it and the equivalents in every other framework. */
  equivalents(framework: string, identifier: string): CrosswalkUcid[] {
    return this.ucids().filter((u) => {
      const v = (u as unknown as Record<string, unknown>)[framework];
      if (Array.isArray(v)) return v.includes(identifier);
      if (v && typeof v === "object") {
        for (const arr of Object.values(v as Record<string, unknown>)) {
          if (Array.isArray(arr) && arr.includes(identifier)) return true;
        }
      }
      return false;
    });
  }
}
