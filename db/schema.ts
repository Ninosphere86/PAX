import { sql } from "drizzle-orm";
import { index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const permissions = sqliteTable("permissions", {
  email: text("email").primaryKey(),
  displayName: text("display_name").notNull().default(""),
  role: text("role", { enum: ["admin", "editor"] }).notNull(),
  addedBy: text("added_by").notNull(),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const questionBankSnapshots = sqliteTable("question_bank_snapshots", {
  id: integer("id").primaryKey(),
  dataJson: text("data_json").notNull(),
  revision: integer("revision").notNull().default(1),
  updatedBy: text("updated_by").notNull(),
  updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const questionOverrides = sqliteTable(
  "question_overrides",
  {
    id: text("id").primaryKey(),
    code: text("code").notNull(),
    dataJson: text("data_json").notNull(),
    deleted: integer("deleted", { mode: "boolean" }).notNull().default(false),
    updatedBy: text("updated_by").notNull(),
    updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [index("question_overrides_code_idx").on(table.code)],
);

export const auditLogs = sqliteTable(
  "audit_logs",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    action: text("action").notNull(),
    questionId: text("question_id"),
    questionCode: text("question_code"),
    summary: text("summary").notNull(),
    actorEmail: text("actor_email").notNull(),
    actorName: text("actor_name").notNull(),
    beforeJson: text("before_json"),
    afterJson: text("after_json"),
    createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [index("audit_logs_created_at_idx").on(table.createdAt)],
);
