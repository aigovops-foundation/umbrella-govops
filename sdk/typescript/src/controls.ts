import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";
import type { Control } from "./types.js";

function walk(dir: string, out: string[] = []): string[] {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (entry.isFile() && full.endsWith(".yaml")) out.push(full);
  }
  return out;
}

export class Controls {
  private items: Control[] = [];

  constructor(private repoRoot: string) {}

  load(): this {
    const root = path.join(this.repoRoot, "domains");
    for (const p of walk(root)) {
      try {
        const doc = yaml.load(fs.readFileSync(p, "utf8")) as Control | null;
        if (doc && doc.kind === "Control") this.items.push(doc);
      } catch {
        // skip malformed; conformance CLI is the canonical validator
      }
    }
    return this;
  }

  all(): Control[] {
    return [...this.items];
  }

  byId(id: string): Control | undefined {
    return this.items.find((c) => c.metadata.id === id);
  }

  byUcid(ucid: string): Control[] {
    return this.items.filter((c) => c.metadata.ucid === ucid);
  }

  byStatus(status: Control["metadata"]["status"]): Control[] {
    return this.items.filter((c) => c.metadata.status === status);
  }

  byDomain(domain: string): Control[] {
    return this.items.filter((c) =>
      c.metadata.id.startsWith(domainPrefix(domain))
    );
  }
}

function domainPrefix(domain: string): string {
  const map: Record<string, string> = {
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
  };
  return map[domain] ?? "";
}
