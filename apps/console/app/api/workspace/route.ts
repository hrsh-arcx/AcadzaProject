import { NextRequest, NextResponse } from "next/server";
import { databaseEnabled, loadWorkspace, saveWorkspace, workspaceId } from "@/lib/store";
import { cases, taxonomy } from "@/lib/data";
import { transition } from "@/lib/review";
import { ReviewRequest } from "@/lib/types";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  if (!databaseEnabled()) return NextResponse.json({ storage: "browser", state: null });
  try {
    const workspace = workspaceId(request.cookies.get("acadza_workspace")?.value);
    const state = await loadWorkspace(workspace.id);
    const response = NextResponse.json({ storage: "database", state });
    response.cookies.set("acadza_workspace", workspace.token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict",
      path: "/",
      maxAge: 60 * 60 * 24 * 8,
    });
    response.headers.set("Cache-Control", "no-store");
    return response;
  } catch {
    return NextResponse.json(
      { error: "Review storage is unavailable. Check database and session configuration." },
      { status: 503 },
    );
  }
}

export async function POST(request: NextRequest) {
  if (!databaseEnabled())
    return NextResponse.json(
      { error: "Database is not configured; use the labelled browser sandbox" },
      { status: 503 },
    );
  const origin = request.headers.get("origin");
  // Next's internal request URL can use localhost behind the deployment proxy.
  // Compare the browser's origin to the actual incoming Host, never an arbitrary
  // client-supplied forwarded-host value.
  let sameOrigin = false;
  try {
    const parsed = new URL(origin || "");
    sameOrigin =
      ["http:", "https:"].includes(parsed.protocol) &&
      parsed.host === (request.headers.get("host") || request.nextUrl.host);
  } catch {
    /* Invalid/missing origins cannot write. */
  }
  if (!sameOrigin)
    return NextResponse.json({ error: "Cross-origin review rejected" }, { status: 403 });
  try {
    if (Number(request.headers.get("content-length") || 0) > 100_000)
      throw new Error("Review request too large");
    const body = await request.text();
    if (body.length > 100_000) throw new Error("Review request too large");
    const input = JSON.parse(body) as ReviewRequest;
    if (
      !input ||
      typeof input.requestId !== "string" ||
      input.requestId.length > 80 ||
      !Array.isArray(input.patches)
    )
      throw new Error("Invalid review request");
    const c = cases.find((c) => c.id === input.caseId);
    if (!c) return NextResponse.json({ error: "Unknown case" }, { status: 404 });
    const session = request.cookies.get("acadza_workspace")?.value;
    if (!session)
      return NextResponse.json({ error: "Open a workspace before reviewing" }, { status: 403 });
    const workspace = workspaceId(session);
    if (workspace.token !== session)
      return NextResponse.json({ error: "Invalid workspace session" }, { status: 403 });
    const state = await loadWorkspace(workspace.id);
    const next = transition(state, input, c, taxonomy);
    if (next !== state) await saveWorkspace(workspace.id, state.version, next);
    return NextResponse.json({ state: next });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Review failed" },
      { status: 409 },
    );
  }
}
