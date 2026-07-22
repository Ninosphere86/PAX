CREATE TABLE `audit_logs` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`action` text NOT NULL,
	`question_id` text,
	`question_code` text,
	`summary` text NOT NULL,
	`actor_email` text NOT NULL,
	`actor_name` text NOT NULL,
	`before_json` text,
	`after_json` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
--> statement-breakpoint
CREATE TABLE `permissions` (
	`email` text PRIMARY KEY NOT NULL,
	`display_name` text DEFAULT '' NOT NULL,
	`role` text NOT NULL,
	`added_by` text NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
--> statement-breakpoint
CREATE TABLE `question_bank_snapshots` (
	`id` integer PRIMARY KEY NOT NULL,
	`data_json` text NOT NULL,
	`revision` integer DEFAULT 1 NOT NULL,
	`updated_by` text NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
--> statement-breakpoint
CREATE TABLE `question_overrides` (
	`id` text PRIMARY KEY NOT NULL,
	`code` text NOT NULL,
	`data_json` text NOT NULL,
	`deleted` integer DEFAULT false NOT NULL,
	`updated_by` text NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
--> statement-breakpoint
INSERT OR IGNORE INTO `permissions` (`email`, `display_name`, `role`, `added_by`)
VALUES ('liboyi1986@gmail.com', 'Boyi Li', 'admin', 'system');
