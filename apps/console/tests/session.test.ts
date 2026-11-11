import test from "node:test";
import assert from "node:assert/strict";
import { workspaceId } from "../lib/store";

test("signed workspace tokens persist and reject tampering", () => {
  const original = process.env.SESSION_SECRET;
  process.env.SESSION_SECRET = "unit-test-only-secret-with-at-least-32-characters";
  try {
    const first = workspaceId(undefined);
    assert.match(first.id, /^[0-9a-f-]{36}$/);
    assert.deepEqual(workspaceId(first.token), first);
    assert.notEqual(
      workspaceId(first.token.slice(0, -1) + (first.token.endsWith("a") ? "b" : "a")).id,
      first.id,
    );
    assert.notEqual(workspaceId("not-a-valid-token").id, first.id);
  } finally {
    if (original === undefined) delete process.env.SESSION_SECRET;
    else process.env.SESSION_SECRET = original;
  }
});

test("database sessions refuse a missing or short signing secret", () => {
  const original = process.env.SESSION_SECRET;
  process.env.SESSION_SECRET = "short";
  try {
    assert.throws(() => workspaceId(undefined), /at least 32/);
  } finally {
    if (original === undefined) delete process.env.SESSION_SECRET;
    else process.env.SESSION_SECRET = original;
  }
});
