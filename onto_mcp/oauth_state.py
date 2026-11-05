"""MCP-owned PostgreSQL OAuth bindings; API-key helper backing is never used."""

from __future__ import annotations

import secrets
import time
from datetime import datetime, timezone

from .oauth import OAuthError, dependency_error

LIFETIME = 86400
PURGE_AGE = 86340
SWEEP_INTERVAL = 30


def utc(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc)


class OAuthStateStore:
    def __init__(self, connect, *, clock=time.time, evict=lambda key: None):
        self.connect, self.clock, self.evict = connect, clock, evict
        self.last_sweep = None
        self.maintenance_ok = False

    def ready(self):
        return (
            self.maintenance_ok
            and self.last_sweep is not None
            and 0 <= self.clock() - self.last_sweep <= 60
        )

    def sweep(self):
        started = self.clock()
        missed = self.last_sweep is not None and started - self.last_sweep > 60
        self.maintenance_ok = False
        try:
            with self.connect() as db:
                rows = db.execute(
                    "DELETE FROM onto_mcp_oauth_sessions WHERE initialized_at <= %s RETURNING owner_key",
                    (utc(started - PURGE_AGE),),
                ).fetchall()
            for row in rows:
                self.evict(row[0])
            self.last_sweep = started
            self.maintenance_ok = True
            return missed
        except Exception:  # noqa: BLE001, S110
            pass
        raise dependency_error()

    def initialize(self, owner):
        if not self.ready():
            raise dependency_error()
        session_id = secrets.token_urlsafe(32)
        now = self.clock()
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO onto_mcp_oauth_sessions (session_id, owner_key, initialized_at, expires_at) VALUES (%s,%s,%s,%s)",
                    (session_id, owner, utc(now), utc(now + LIFETIME)),
                )
            return session_id
        except Exception:  # noqa: BLE001, S110
            pass
        self.maintenance_ok = False
        raise dependency_error()

    def _row(self, db, session_id, owner):
        if not self.ready():
            raise dependency_error()
        row = db.execute(
            "SELECT thread_external_id, created_at, revision FROM onto_mcp_oauth_sessions WHERE session_id=%s AND owner_key=%s AND expires_at>%s FOR UPDATE",
            (session_id, owner, utc(self.clock())),
        ).fetchone()
        if row is None:
            # Never upsert an unknown/expired/foreign client-supplied session ID.
            raise OAuthError()
        return row

    def require(self, session_id, owner):
        self.helper(session_id, owner)

    def helper(self, session_id, owner, value=None):
        try:
            with self.connect() as db:
                row = self._row(db, session_id, owner)
                if value is not None:
                    row = db.execute(
                        "UPDATE onto_mcp_oauth_sessions SET thread_external_id=%s, created_at=COALESCE(created_at,%s), revision=revision+1 WHERE session_id=%s AND owner_key=%s RETURNING thread_external_id, created_at, revision",
                        (value, utc(self.clock()), session_id, owner),
                    ).fetchone()
            thread_id, created_at, _revision = row
            result = {"contextId": session_id, "threadExternalId": thread_id}
            if thread_id is None:
                result["message"] = "No session state stored for this context."
            else:
                result["createdAt"] = created_at.astimezone(timezone.utc).isoformat()
            return result
        except OAuthError:
            raise
        except Exception:  # noqa: BLE001, S110
            pass
        self.maintenance_ok = False
        raise dependency_error()

    def remove(self, session_id, owner):
        try:
            with self.connect() as db:
                self._row(db, session_id, owner)
                db.execute(
                    "DELETE FROM onto_mcp_oauth_sessions WHERE session_id=%s AND owner_key=%s",
                    (session_id, owner),
                )
            self.evict(owner)
        except OAuthError:
            raise
        except Exception:  # noqa: BLE001
            raise dependency_error() from None

    def invalidate(self, owner):
        self.evict(owner)
        try:
            with self.connect() as db:
                db.execute(
                    "DELETE FROM onto_mcp_oauth_sessions WHERE owner_key=%s", (owner,)
                )
        except Exception:  # noqa: BLE001
            self.maintenance_ok = False
            raise dependency_error() from None


def configured_store(service, env):
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    dsn = env.get("ONTO_OAUTH_STATE_DSN", "")
    try:
        options = conninfo_to_dict(dsn)
        if not dsn or options.get("sslmode") != "verify-full":
            raise ValueError()
    except Exception:  # noqa: BLE001
        raise OSError(
            "OAuth state requires PostgreSQL with sslmode=verify-full."
        ) from None
    store = OAuthStateStore(
        lambda: psycopg.connect(dsn, connect_timeout=10), evict=service.evict
    )
    service.invalidate_connection = store.invalidate
    return store
