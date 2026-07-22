import { INITIAL_ADMIN_EMAIL, getWorkspaceDb, getWorkspaceIdentity, jsonError } from "../../../lib/workspace";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(request: Request) {
  try {
    const identity = await getWorkspaceIdentity();
    if (!identity.user) return jsonError("请先登录公司账号", 401);
    if (identity.role !== "admin") return jsonError("只有管理员可以修改成员权限", 403);

    const payload = (await request.json()) as { email?: string; displayName?: string; role?: "editor" | "viewer" };
    const email = payload.email?.trim().toLowerCase() ?? "";
    const displayName = payload.displayName?.trim().slice(0, 80) ?? "";
    if (!EMAIL_PATTERN.test(email)) return jsonError("请输入有效的邮箱地址", 400);
    if (email === INITIAL_ADMIN_EMAIL) return jsonError("初始管理员权限不能被移除", 400);
    if (payload.role !== "editor" && payload.role !== "viewer") return jsonError("无效的权限类型", 400);

    const db = getWorkspaceDb();
    const now = new Date().toISOString();
    const actionText = payload.role === "editor" ? "设为编辑者" : "改为只读";
    const permissionStatement = payload.role === "editor"
      ? db.prepare(
          `INSERT INTO permissions (email, display_name, role, added_by, created_at, updated_at)
           VALUES (?, ?, 'editor', ?, ?, ?)
           ON CONFLICT(email) DO UPDATE SET display_name = excluded.display_name, role = 'editor',
           added_by = excluded.added_by, updated_at = excluded.updated_at`,
        ).bind(email, displayName, identity.user.email, now, now)
      : db.prepare("DELETE FROM permissions WHERE email = ? AND role != 'admin'").bind(email);

    await db.batch([
      permissionStatement,
      db.prepare(
        `INSERT INTO audit_logs
         (action, question_id, question_code, summary, actor_email, actor_name, before_json, after_json, created_at)
         VALUES ('权限修改', NULL, NULL, ?, ?, ?, NULL, NULL, ?)`,
      ).bind(`${email}：${actionText}`, identity.user.email, identity.user.displayName, now),
    ]);

    const result = await db.prepare(
      "SELECT email, display_name, role, added_by, created_at, updated_at FROM permissions ORDER BY CASE role WHEN 'admin' THEN 0 ELSE 1 END, email ASC",
    ).all();
    const log = await db.prepare(
      "SELECT id, action, question_id, question_code, summary, actor_email, actor_name, created_at FROM audit_logs ORDER BY id DESC LIMIT 1",
    ).first();
    return Response.json({ ok: true, permissions: result.results, log });
  } catch (error) {
    const message = error instanceof Error ? error.message : "权限保存失败";
    return Response.json({ error: message }, { status: 500 });
  }
}
