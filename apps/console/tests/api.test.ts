import test from "node:test";
import assert from "node:assert/strict";
import { NextRequest } from "next/server";
import { GET, POST } from "../app/api/workspace/route";

test("unconfigured storage is explicitly a browser sandbox and cannot pretend to persist writes", async () => {
  const original = process.env.DATABASE_URL;
  delete process.env.DATABASE_URL;
  try {
    const response = await GET(new NextRequest("http://localhost:3000/api/workspace"));
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { storage: "browser", state: null });
    const write = await POST(
      new NextRequest("http://localhost:3000/api/workspace", { method: "POST" }),
    );
    assert.equal(write.status, 503);
  } finally {
    if (original === undefined) delete process.env.DATABASE_URL;
    else process.env.DATABASE_URL = original;
  }
});

test("cross-origin writes are rejected before attempting any database connection", async () => {
  const original = process.env.DATABASE_URL;
  process.env.DATABASE_URL = "postgres://invalid-for-unit-test";
  try {
    const response = await POST(
      new NextRequest("http://localhost:3000/api/workspace", {
        method: "POST",
        headers: { origin: "https://untrusted.example" },
      }),
    );
    assert.equal(response.status, 403);
  } finally {
    if (original === undefined) delete process.env.DATABASE_URL;
    else process.env.DATABASE_URL = original;
  }
});

test("oversized review requests are rejected before reading or writing storage", async () => {
  const original = process.env.DATABASE_URL;
  process.env.DATABASE_URL = "postgres://invalid-for-unit-test";
  try {
    const response = await POST(
      new NextRequest("http://localhost:3000/api/workspace", {
        method: "POST",
        headers: { origin: "http://localhost:3000", "content-length": "100001" },
      }),
    );
    assert.equal(response.status, 409);
    assert.match((await response.json()).error, /too large/);
  } finally {
    if (original === undefined) delete process.env.DATABASE_URL;
    else process.env.DATABASE_URL = original;
  }
});
