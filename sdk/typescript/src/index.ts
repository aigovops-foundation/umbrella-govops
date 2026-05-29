import { Controls } from "./controls.js";
import { CrosswalkClient } from "./crosswalk.js";
import { Evidence } from "./evidence.js";
import { journeys } from "./journeys.js";

export * from "./types.js";
export { Controls, CrosswalkClient, Evidence, journeys };

export interface UmbrellaOptions {
  repoRoot?: string;
}

/**
 * Entry point that matches the homepage code snippet:
 *
 *   import { umbrella } from '@aigovops/umbrella-sdk';
 *   const controls = umbrella(opts).controls.load().byUcid('UCID-DATA-BIAS-001');
 */
export function umbrella(opts: UmbrellaOptions = {}) {
  const root = opts.repoRoot ?? process.cwd();
  return {
    controls: new Controls(root),
    crosswalk: new CrosswalkClient(root),
    evidence: new Evidence(),
    journey: journeys,
    version: "0.1.0-alpha.1" as const,
  };
}

// Default export for ESM convenience
export default umbrella;
