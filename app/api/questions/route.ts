import { canEdit, getWorkspaceDb, getWorkspaceIdentity, jsonError } from "../../../lib/workspace";

type QuestionPayload = {
  id?: string;
  code?: string;
  title?: string;
  [key: string]: unknown;
};

const FIELD_NAMES: Record<string, string> = {
  code: "题目编号",
  title: "题干",
  image: "题图",
  options: "选项",
  type: "题型",
  category: "大类",
  section: "章节",
  difficulty: "难度",
  answer: "正确答案",
  explanation: "简析",
  detailedExplanation: "试题详解",
  tags: "标签",
  status: "发布状态",
};

function validQuestion(value: unknown): value is QuestionPayload {
  if (!value || typeof value !== "object") return false;
  const question = value as QuestionPayload;
  return Boolean(question.id?.trim() && question.code?.trim() && question.title?.trim());
}

function changeSummary(before: QuestionPayload | null, after: QuestionPayload | null, action: string) {
  if (action === "新增") return `新增题目「${after?.title || "未命名题目"}」`;
  if (action === "删除") return `删除题目「${before?.title || "未命名题目"}」`;
  const changed = Object.keys(FIELD_NAMES).filter(
    (key) => JSON.stringify(before?.[key] ?? null) !== JSON.stringify(after?.[key] ?? null),
  );
  return changed.length ? `修改：${changed.map((key) => FIELD_NAMES[key]).join("、")}` : "保存题目（内容无变化）";
}

export async function POST(request: Request) {
  try {
    const identity = await getWorkspaceIdentity();
    if (!identity.user) return jsonError("请先登录公司账号", 401);
    if (!canEdit(identity.role)) return jsonError("当前账号没有编辑权限", 403);

    const payload = (await request.json()) as {
      operation?: "create" | "update" | "delete";
      before?: QuestionPayload | null;
      after?: QuestionPayload | null;
    };
    const operation = payload.operation;
    const before = payload.before ?? null;
    const after = payload.after ?? null;
    if (!operation || !["create", "update", "delete"].includes(operation)) return jsonError("无效的操作类型", 400);
    if (operation === "delete" ? !validQuestion(before) : !validQuestion(after)) return jsonError("题目数据不完整", 400);

    const question = operation === "delete" ? before! : after!;
    const action = operation === "create" ? "新增" : operation === "delete" ? "删除" : "修改";
    const summary = changeSummary(before, after, action);
    const now = new Date().toISOString();
    const db = getWorkspaceDb();

    const statements = [
      db.prepare(
        `INSERT INTO question_overrides (id, code, data_json, deleted, updated_by, updated_at)
         VALUES (?, ?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET code = excluded.code, data_json = excluded.data_json,
         deleted = excluded.deleted, updated_by = excluded.updated_by, updated_at = excluded.updated_at`,
      ).bind(
        question.id,
        question.code,
        JSON.stringify(question),
        operation === "delete" ? 1 : 0,
        identity.user.email,
        now,
      ),
      db.prepare(
        `INSERT INTO audit_logs
         (action, question_id, question_code, summary, actor_email, actor_name, before_json, after_json, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      ).bind(
        action,
        question.id,
        question.code,
        summary,
        identity.user.email,
        identity.user.displayName,
        before ? JSON.stringify(before) : null,
        after ? JSON.stringify(after) : null,
        now,
      ),
    ];
    await db.batch(statements);
    const log = await db.prepare(
      "SELECT id, action, question_id, question_code, summary, actor_email, actor_name, created_at FROM audit_logs ORDER BY id DESC LIMIT 1",
    ).first();

    return Response.json({ ok: true, log });
  } catch (error) {
    const message = error instanceof Error ? error.message : "题目保存失败";
    return Response.json({ error: message }, { status: 500 });
  }
}
