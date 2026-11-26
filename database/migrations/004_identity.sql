ALTER TABLE user_context ADD COLUMN identity_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE user_context ADD COLUMN active_goal_ids uuid[] NOT NULL DEFAULT '{}';
ALTER TABLE user_context ADD COLUMN active_project_ids uuid[] NOT NULL DEFAULT '{}';
