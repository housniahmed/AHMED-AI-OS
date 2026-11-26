CREATE TABLE conversations (
 id uuid PRIMARY KEY, owner_id uuid NOT NULL REFERENCES user_context(id),
 title text NOT NULL CHECK(length(trim(title))>0),
 status text NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(id,owner_id)
);
CREATE TABLE conversation_messages (
 seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 id uuid NOT NULL UNIQUE,
 conversation_id uuid NOT NULL,
 owner_id uuid NOT NULL,
 role text NOT NULL CHECK(role IN ('user','assistant')),
 content text NOT NULL CHECK(length(trim(content))>0),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(conversation_id,owner_id) REFERENCES conversations(id,owner_id)
);
CREATE INDEX conversation_messages_history ON conversation_messages(conversation_id,seq);
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations FORCE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages FORCE ROW LEVEL SECURITY;
CREATE POLICY owner_scope ON conversations USING(owner_id=nullif(current_setting('app.owner_id',true),'')::uuid) WITH CHECK(owner_id=nullif(current_setting('app.owner_id',true),'')::uuid);
CREATE POLICY owner_scope ON conversation_messages USING(owner_id=nullif(current_setting('app.owner_id',true),'')::uuid) WITH CHECK(owner_id=nullif(current_setting('app.owner_id',true),'')::uuid);
