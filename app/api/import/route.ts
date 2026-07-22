import { getWorkspaceDb, getWorkspaceIdentity, jsonError } from "../../../lib/workspace";

export async function POST(request: Request) {
  try {
    const identity = await getWorkspaceIdentity();
    if (!identity.user) return jsonError("请先登录公司账号", 401);
    if (identity.role !== "admin") return jsonError("只有管理员可以批量导入题库", 403);

    const payload = (await request.json()) as { questions?: unknown[] };
    if (!Array.isArray(payload.questions) || !payload.questions.length || payload.questions.length > 5000) {
      return jsonError("导入题库数量无效", 400);
    }

    const now = new Date().toISOString();
    const db = getWorkspaceDb();
    const current = await db.prepare("SELECT revision FROM question_bank_snapshots WHERE id = 1").first<{ revision: number }>();
    const revision = (current?.revision ?? 0) + 1;
    await db.batch([
      db.prepare(
        `INSERT INTO question_bank_snapshots (id, data_json, revision, updated_by, updated_at)
         VALUES (1, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET data_json = excluded.data_json, revision = excluded.revision,
         updated_by = excluded.updated_by, updated_at = excluded.updated_at`,
      ).bind(JSON.stringify(payload.questions), revision, identity.user.email, now),
      db.prepare("DELETE FROM question_overrides"),
      db.prepare(
        `INSERT INTO audit_logs
         (action, question_id, question_code, summary, actor_email, actor_name, before_json, after_json, created_at)
         VALUES ('批量导入', NULL, NULL, ?, ?, ?, NULL, NULL, ?)`,
      ).bind(`批量导入 ${payload.questions.length} 道题，生成共享题库版本 ${revision}`, identity.user.email, identity.user.displayName, now),
    ]);

    const log = await db.prepare(
      "SELECT id, action, question_id, question_code, summary, actor_email, actor_name, created_at FROM audit_logs ORDER BY id DESC LIMIT 1",
    ).first();
    return Response.json({ ok: true, revision, log });
  } catch (error) {
    const message = error instanceof Error ? error.message : "批量导入失败";
    return Response.json({ error: message }, { status: 500 });
  }
}
