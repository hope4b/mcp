-- Apply using the separately authorized provisioning principal, never at runtime.
-- The runtime principal needs SELECT/INSERT/UPDATE/DELETE only on this table.
CREATE TABLE onto_mcp_oauth_sessions (
    session_id text PRIMARY KEY,
    owner_key text NOT NULL,
    initialized_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    thread_external_id text,
    created_at timestamptz,
    revision bigint NOT NULL DEFAULT 0,
    CHECK (expires_at > initialized_at AND expires_at <= initialized_at + interval '24 hours')
);
CREATE INDEX onto_mcp_oauth_sessions_retention ON onto_mcp_oauth_sessions (initialized_at);
CREATE INDEX onto_mcp_oauth_sessions_owner ON onto_mcp_oauth_sessions (owner_key);
