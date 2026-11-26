-- Runtime role must not own tables or have BYPASSRLS.
-- Tenant setting is a trusted application assertion, not independent authentication.
DO $$
DECLARE t text;
BEGIN
 FOREACH t IN ARRAY ARRAY['memories','goals','projects','approval_ledger'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY owner_scope ON %I USING (%I = nullif(current_setting(''app.owner_id'',true),'''')::uuid) WITH CHECK (%I = nullif(current_setting(''app.owner_id'',true),'''')::uuid)',t,
   CASE WHEN t='approval_ledger' THEN 'owner_id' ELSE 'user_context_id' END,
   CASE WHEN t='approval_ledger' THEN 'owner_id' ELSE 'user_context_id' END);
 END LOOP;
END $$;
ALTER TABLE user_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_context FORCE ROW LEVEL SECURITY;
CREATE POLICY owner_scope ON user_context USING (id=nullif(current_setting('app.owner_id',true),'')::uuid) WITH CHECK (id=nullif(current_setting('app.owner_id',true),'')::uuid);
ALTER TABLE approval_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_events FORCE ROW LEVEL SECURITY;
CREATE POLICY owner_scope ON approval_events USING (EXISTS (SELECT 1 FROM approval_ledger a WHERE a.id=approval_id)) WITH CHECK (actor_id=nullif(current_setting('app.owner_id',true),'')::uuid AND EXISTS (SELECT 1 FROM approval_ledger a WHERE a.id=approval_id));
CREATE FUNCTION protect_approval_payload() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.owner_id IS DISTINCT FROM OLD.owner_id OR NEW.payload IS DISTINCT FROM OLD.payload OR NEW.expires_at IS DISTINCT FROM OLD.expires_at OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
  RAISE EXCEPTION 'immutable approval fields';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER immutable_approval BEFORE UPDATE ON approval_ledger FOR EACH ROW EXECUTE FUNCTION protect_approval_payload();
CREATE FUNCTION deny_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'audit history is append-only'; END $$;
CREATE TRIGGER append_only_events BEFORE UPDATE OR DELETE ON approval_events FOR EACH ROW EXECUTE FUNCTION deny_audit_mutation();
CREATE TRIGGER no_audit_truncate BEFORE TRUNCATE ON approval_events FOR EACH STATEMENT EXECUTE FUNCTION deny_audit_mutation();
