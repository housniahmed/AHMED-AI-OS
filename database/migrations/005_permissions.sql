CREATE TABLE security_permissions (
 owner_id uuid NOT NULL REFERENCES user_context(id),
 resource text NOT NULL CHECK (length(resource)>0),
 access_level integer NOT NULL CHECK (access_level BETWEEN 0 AND 4),
 PRIMARY KEY(owner_id,resource)
);
ALTER TABLE security_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_permissions FORCE ROW LEVEL SECURITY;
CREATE POLICY owner_scope ON security_permissions USING (owner_id=nullif(current_setting('app.owner_id',true),'')::uuid) WITH CHECK (owner_id=nullif(current_setting('app.owner_id',true),'')::uuid);
