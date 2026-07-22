import { getWorkspaceDb, getWorkspaceIdentity, safeJsonParse } from "../../../lib/workspace";

type SnapshotRow = { data_json: string; revision: number; updated_at: string; updated_by: string };
type OverrideRow = { id: string; data_json: string; deleted: number };

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const db = getWorkspaceDb();
    const identity = await getWorkspaceIdentity();
    const [snapshot, overrideResult, logResult] = await Promise.all([
      db.prepare("SELECT data_json, revision, updated_at, updated_by FROM question_bank_snapshots WHERE id = 1").first<SnapshotRow>(),
      db.prepare("SELECT id, data_json, deleted FROM question_overrides ORDER BY updated_at ASC").all<OverrideRow>(),
      db.prepare(
        "SELECT id, action, question_id, question_code, summary, actor_email, actor_name, created_at FROM audit_logs ORDER BY id DESC LIMIT 200",
      ).all(),
    ]);

    let permissions: unknown[] = [];
    if (identity.role === "admin") {
      const result = await db.prepare(
        "SELECT email, display_name, role, added_by, created_at, updated_at FROM permissions ORDER BY CASE role WHEN 'admin' THEN 0 ELSE 1 END, email ASC",
      ).all();
      permissions = result.results;
    }

    return Response.json(
      {
        user: identity.user,
        role: identity.role,
        snapshot: snapshot ? safeJsonParse<unknown[]>(snapshot.data_json) : null,
        snapshotMeta: snapshot
          ? { revision: snapshot.revision, updatedAt: snapshot.updated_at, updatedBy: snapshot.updated_by }
          : null,
        overrides: overrideResult.results.map((row: OverrideRow) => ({
          id: row.id,
          deleted: Boolean(row.deleted),
          question: safeJsonParse<unknown>(row.data_json),
        })),
        logs: identity.user ? logResult.results : [],
        permissions,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "无法读取共享题库";
    return Response.json({ error: message }, { status: 500 });
  }
}
