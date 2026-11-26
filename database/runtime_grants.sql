-- Run as migration administrator after creating a separate LOGIN role ahmed_runtime.
-- Provision credentials outside Git. Do not grant membership in the migration role.
ALTER ROLE ahmed_runtime NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
REVOKE CREATE ON SCHEMA public FROM ahmed_runtime;
GRANT USAGE ON SCHEMA public TO ahmed_runtime;
GRANT SELECT, INSERT, UPDATE ON user_context, memories, goals, projects TO ahmed_runtime;
GRANT SELECT, INSERT ON approval_ledger TO ahmed_runtime;
GRANT UPDATE (state,approver_id,claimed_at,finished_at,receipt) ON approval_ledger TO ahmed_runtime;
GRANT SELECT, INSERT ON approval_events TO ahmed_runtime;
GRANT USAGE ON SEQUENCE approval_events_event_id_seq TO ahmed_runtime;

GRANT SELECT ON schema_migrations TO ahmed_runtime;
GRANT SELECT, INSERT, UPDATE ON security_permissions TO ahmed_runtime;

GRANT SELECT, INSERT ON conversations, conversation_messages TO ahmed_runtime;
GRANT UPDATE (updated_at) ON conversations TO ahmed_runtime;
GRANT USAGE ON SEQUENCE conversation_messages_seq_seq TO ahmed_runtime;
