// Smoke tests for the TypeScript SDK. Run against built dist.
import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { umbrella, journeys } from "../dist/index.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../..");

test("umbrella() returns expected surface", () => {
  const u = umbrella({ repoRoot: REPO_ROOT });
  assert.ok(u.controls);
  assert.ok(u.crosswalk);
  assert.ok(u.evidence);
  assert.ok(u.journey);
  assert.equal(u.version, "0.1.0-alpha.1");
});

test("controls.load() reads at least one control", () => {
  const u = umbrella({ repoRoot: REPO_ROOT });
  const all = u.controls.load().all();
  assert.ok(all.length >= 1, `expected >=1 control, got ${all.length}`);
  const dg = u.controls.byId("DG-002");
  assert.ok(dg, "DG-002 should resolve");
  assert.equal(dg.metadata.ucid, "UCID-DATA-BIAS-001");
});

test("crosswalk.resolve() returns the right UCID", () => {
  const u = umbrella({ repoRoot: REPO_ROOT });
  u.crosswalk.load();
  const ucid = u.crosswalk.resolve("UCID-DATA-BIAS-001");
  assert.ok(ucid);
  assert.ok(ucid.implementing_controls.includes("DG-002"));
});

test("crosswalk.equivalents() finds the same UCID from NIST identifier", () => {
  const u = umbrella({ repoRoot: REPO_ROOT });
  u.crosswalk.load();
  const matches = u.crosswalk.equivalents("nist_ai_rmf", "MEASURE-2.11");
  assert.ok(matches.length >= 1);
  assert.equal(matches[0].id, "UCID-DATA-BIAS-001");
});

test("journeys.list() returns 3 journeys", () => {
  const all = journeys.list();
  assert.equal(all.length, 3);
  assert.deepEqual(
    all.map((j) => j.key).sort(),
    ["at-yes", "return-to-yes", "to-yes"]
  );
});

test("journey.get('to-yes') returns 4 steps", () => {
  const j = journeys.get("to-yes");
  assert.equal(j.steps.length, 4);
});

test("evidence.build() + digest() produces stable hash", () => {
  const u = umbrella({ repoRoot: REPO_ROOT });
  const b = u.evidence.build({
    repo: "umbrella-govops",
    checks: [{ name: "schema-valid", status: "pass" }],
  });
  const d1 = u.evidence.digest(b);
  const d2 = u.evidence.digest(b);
  assert.equal(d1, d2);
  assert.match(d1, /^[a-f0-9]{64}$/);
});
