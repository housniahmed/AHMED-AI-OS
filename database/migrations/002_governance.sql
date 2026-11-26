CREATE TABLE IF NOT EXISTS approval_ledger (
 id uuid PRIMARY KEY,
 owner_id uuid NOT NULL REFERENCES user_context(id),
 payload jsonb NOT NULL,
 state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','approved','rejected','executing','succeeded','uncertain')),
 expires_at timestamptz NOT NULL,
 approver_id uuid,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 claimed_at timestamptz,
 finished_at timestamptz,
 receipt jsonb
);
CREATE TABLE IF NOT EXISTS approval_events (
 event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 approval_id uuid NOT NULL REFERENCES approval_ledger(id),
 state text NOT NULL,
 actor_id uuid NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS approval_owner_state ON approval_ledger(owner_id,state);
