import test from "node:test";
import assert from "node:assert/strict";
import { cases, taxonomy } from "../lib/data";
import { applyPatches, transition, validatePatches } from "../lib/review";
import { safeHtml } from "../lib/sanitize";
import { emptyWorkspace, getPayload, ReviewRequest } from "../lib/types";
const c = cases.find((c) => c.reports.some((r) => r.reportId === "R001"))!;
const input = (): ReviewRequest => ({
  caseId: c.id,
  sourceHash: c.sourceHash,
  expectedVersion: 0,
  action: "approve",
  reason: "Checked the phasor calculation",
  patches: c.patches,
  requestId: "test-request-1",
});

test("all exported proposals pass the console's scope guards", () => {
  for (const item of cases)
    assert.deepEqual(validatePatches(item, item.patches, taxonomy), [], item.reports[0].reportId);
});
test("approval changes only the workspace copy and records before/after", () => {
  const before = JSON.stringify(c);
  const state = transition(emptyWorkspace(), input(), c, taxonomy, "2026-11-11T10:00:00Z");
  assert.equal(getPayload(state.reviews[c.id].question).answer, "A");
  assert.equal(getPayload(state.audit[0].before).answer, "C");
  assert.equal(getPayload(state.audit[0].after).answer, "A");
  assert.equal(JSON.stringify(c), before);
});
test("retry is idempotent, stale reviews and repeated applications fail", () => {
  const state = transition(emptyWorkspace(), input(), c, taxonomy);
  assert.equal(transition(state, input(), c, taxonomy), state);
  assert.throws(
    () => transition(state, { ...input(), requestId: "different" }, c, taxonomy),
    /changed/,
  );
  assert.throws(() => applyPatches(state.reviews[c.id].question, c.patches), /Stale/);
});
test("editing saves a draft, approval is a separate action", () => {
  const state = transition(emptyWorkspace(), { ...input(), action: "edit" }, c, taxonomy);
  assert.equal(state.reviews[c.id].status, "draft");
  assert.equal(getPayload(state.reviews[c.id].question).answer, "C");
  const approved = transition(
    state,
    { ...input(), expectedVersion: 1, requestId: "approve-draft" },
    c,
    taxonomy,
  );
  assert.equal(approved.reviews[c.id].status, "approved");
  assert.equal(approved.audit.length, 2);
});
test("rejection requires a reason and does not mutate content", () => {
  assert.throws(
    () => transition(emptyWorkspace(), { ...input(), action: "reject", reason: "" }, c, taxonomy),
    /reason/,
  );
  const rejected = transition(emptyWorkspace(), { ...input(), action: "reject" }, c, taxonomy);
  assert.equal(rejected.reviews[c.id].status, "rejected");
  assert.equal(getPayload(rejected.reviews[c.id].question).answer, "C");
});
test("manual-only findings do not write content on approval", () => {
  const diagram = cases.find((c) => c.decision.repair === "diagram")!;
  const state = transition(
    emptyWorkspace(),
    { ...input(), caseId: diagram.id, sourceHash: diagram.sourceHash, patches: [] },
    diagram,
    taxonomy,
  );
  assert.equal(state.reviews[diagram.id].status, "needs_authoring");
  assert.deepEqual(state.reviews[diagram.id].question, diagram.question);
  assert.ok(
    validatePatches(
      diagram,
      [{ field: "question", find: "figure", replace: "guessed diagram" }],
      taxonomy,
    ).length,
  );
});
test("sanitization removes script, events, SVG and URLs while preserving MathML", () => {
  const html =
    '<h3 onclick="alert(1)">Text<script>alert(1)</script><svg onload="alert(1)"></svg><math xmlns="http://www.w3.org/1998/Math/MathML"><mfrac><mn>1</mn><mn>2</mn></mfrac></math><a href="javascript:alert(1)">x</a></h3>';
  const clean = safeHtml(html);
  assert.ok(!/script|onclick|onload|javascript:|<svg/.test(clean));
  assert.ok(clean.includes("<math") && clean.includes("<mfrac>"));
});
test("MathML damage is blocked by the faculty editor too", () => {
  const item = cases.find((c) => c.reports.some((r) => r.reportId === "R014"))!;
  const original = item.patches[0];
  assert.ok(
    validatePatches(
      item,
      [{ ...original, replace: "<math><mfrac><mn>7</mn><mn>8</mn></math>" }],
      taxonomy,
    ).length,
  );
});
