import { env } from "cloudflare:workers";
import { getChatGPTUser } from "../app/chatgpt-auth";

export type WorkspaceRole = "admin" | "editor" | "viewer";

export const INITIAL_ADMIN_EMAIL = "liboyi1986@gmail.com";

export function getWorkspaceDb() {
  if (!env.DB) throw new Error("题库共享数据库暂不可用");
  return env.DB;
}

export async function getWorkspaceIdentity() {
  const user = await getChatGPTUser();
  if (!user) return { user: null, role: "viewer" as WorkspaceRole };

  const email = user.email.trim().toLowerCase();
  if (email === INITIAL_ADMIN_EMAIL) {
    return { user: { ...user, email }, role: "admin" as WorkspaceRole };
  }

  const row = await getWorkspaceDb()
    .prepare("SELECT role FROM permissions WHERE email = ? LIMIT 1")
    .bind(email)
    .first<{ role: WorkspaceRole }>();

  return {
    user: { ...user, email },
    role: (row?.role === "editor" || row?.role === "admin" ? row.role : "viewer") as WorkspaceRole,
  };
}

export function canEdit(role: WorkspaceRole) {
  return role === "admin" || role === "editor";
}

export function jsonError(message: string, status: number) {
  return Response.json({ error: message }, { status });
}

export function safeJsonParse<T>(value: string | null): T | null {
  if (!value) return null;
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}
