import { createHmac, randomUUID, timingSafeEqual } from "node:crypto";
import postgres from "postgres";
import { emptyWorkspace, Workspace } from "./types";

let client: ReturnType<typeof postgres> | undefined;
function db() {
  if (!client)
    client = postgres(process.env.DATABASE_URL!, {
      max: 2,
      prepare: false,
      idle_timeout: 20,
      connect_timeout: 10,
    });
  return client;
}
export function databaseEnabled() {
  return Boolean(process.env.DATABASE_URL);
}
export function workspaceId(cookie: string | undefined): { id: string; token: string } {
  const secret = process.env.SESSION_SECRET;
  if (!secret || secret.length < 32)
    throw new Error("Database mode needs SESSION_SECRET with at least 32 characters");
  const sign = (id: string) => createHmac("sha256", secret).update(id).digest("hex");
  const [id, signature] = (cookie || "").split(".");
  if (
    id &&
    /^[0-9a-f-]{36}$/.test(id) &&
    signature &&
    /^[0-9a-f]{64}$/.test(signature) &&
    timingSafeEqual(Buffer.from(sign(id)), Buffer.from(signature))
  )
    return { id, token: cookie! };
  const fresh = randomUUID();
  return { id: fresh, token: `${fresh}.${sign(fresh)}` };
}
export async function loadWorkspace(id: string): Promise<Workspace> {
  const sql = db();
  // CREATE IF NOT EXISTS makes a clean deployment usable without a separate console.
  await sql`CREATE TABLE IF NOT EXISTS acadza_workspaces (id uuid PRIMARY KEY, version integer NOT NULL, state jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now())`;
  const initial = emptyWorkspace();
  await sql`INSERT INTO acadza_workspaces (id, version, state) VALUES (${id}, 0, ${sql.json(initial)}) ON CONFLICT DO NOTHING`;
  const rows = await sql`SELECT state FROM acadza_workspaces WHERE id=${id}`;
  return rows[0].state as Workspace;
}
export async function saveWorkspace(id: string, expected: number, next: Workspace) {
  const sql = db();
  const rows =
    await sql`UPDATE acadza_workspaces SET state=${sql.json(next)}, version=${next.version}, updated_at=now() WHERE id=${id} AND version=${expected} RETURNING version`;
  if (!rows.length) throw new Error("Another review changed this workspace. Refresh and retry.");
}
