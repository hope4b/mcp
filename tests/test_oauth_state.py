"""Transactional storage doubles exercise the SQL contract without a database."""

import copy
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from onto_mcp.oauth import OAuthError
from onto_mcp.oauth_state import LIFETIME, OAuthStateStore, utc


class Database:
    def __init__(self):
        self.rows = {}
        self.lock = threading.RLock()
        self.fail = False
        self.commits = []

    def connect(self):
        return Transaction(self)


class Transaction:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.db.lock.acquire()
        self.before = copy.deepcopy(self.db.rows)
        return self

    def __exit__(self, typ, *_):
        if typ:
            self.db.rows = self.before
        else:
            self.db.commits.append(copy.deepcopy(self.db.rows))
        self.db.lock.release()

    def execute(self, sql, args):
        if self.db.fail:
            raise RuntimeError("private database diagnostics")
        self.result = []
        rows = self.db.rows
        if sql.startswith("INSERT"):
            sid, owner, initialized, expires = args
            assert sid not in rows
            rows[sid] = {
                "owner": owner,
                "initialized": initialized,
                "expires": expires,
                "thread": None,
                "created": None,
                "revision": 0,
            }
        elif sql.startswith("SELECT"):
            sid, owner, now = args
            r = rows.get(sid)
            if r and r["owner"] == owner and r["expires"] > now:
                self.result = [(r["thread"], r["created"], r["revision"])]
        elif sql.startswith("UPDATE"):
            value, now, sid, owner = args
            r = rows[sid]
            assert r["owner"] == owner
            r.update(
                thread=value, created=r["created"] or now, revision=r["revision"] + 1
            )
            self.result = [(r["thread"], r["created"], r["revision"])]
        elif "initialized_at <=" in sql:
            for sid, r in list(rows.items()):
                if r["initialized"] <= args[0]:
                    self.result.append((r["owner"],))
                    del rows[sid]
        elif "session_id=%s" in sql:
            sid, owner = args
            if rows.get(sid, {}).get("owner") == owner:
                del rows[sid]
        else:
            for sid, r in list(rows.items()):
                if r["owner"] == args[0]:
                    del rows[sid]
        return self

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
        return self.result


@pytest.fixture
def state():
    db = Database()
    clock = [1700000000]
    evicted = []
    store = OAuthStateStore(db.connect, clock=lambda: clock[0], evict=evicted.append)
    store.sweep()
    return store, db, clock, evicted


def test_owned_helpers_fixed_timestamp_and_reconstruction(state):
    store, db, clock, _ = state
    sid = store.initialize("owner-p")
    assert (
        len(sid) == 43
    )  # generation source additionally uses secrets.token_urlsafe(32)
    assert store.helper(sid, "owner-p") == {
        "contextId": sid,
        "threadExternalId": None,
        "message": "No session state stored for this context.",
    }
    first = store.helper(sid, "owner-p", "thread-1")
    clock[0] += 1
    last = store.helper(sid, "owner-p", "thread-2")
    assert last["createdAt"] == first["createdAt"]
    assert last["threadExternalId"] == "thread-2"
    for other in (
        "different-issuer",
        "different-user",
        "different-client",
        "different-session",
    ):
        with pytest.raises(OAuthError):
            store.helper(sid, other, "foreign")
    second = OAuthStateStore(db.connect, clock=lambda: clock[0])
    second.sweep()
    assert second.helper(sid, "owner-p") == last
    assert db.rows[sid]["revision"] == 2
    assert db.rows[sid]["expires"] == utc(1700000000 + LIFETIME)


def test_serialized_last_committed_save_wins(state):
    store, db, _, _ = state
    sid = store.initialize("owner")
    other = OAuthStateStore(db.connect, clock=store.clock)
    other.sweep()
    start = threading.Barrier(3)

    def save(s, value):
        start.wait()
        return s.helper(sid, "owner", value)

    with ThreadPoolExecutor(2) as executor:
        a = executor.submit(save, store, "first")
        b = executor.submit(save, other, "second")
        start.wait()
        a.result()
        b.result()
    writes = [
        snapshot[sid]
        for snapshot in db.commits
        if sid in snapshot and snapshot[sid]["revision"]
    ]
    assert [r["revision"] for r in writes] == [1, 2]
    assert store.helper(sid, "owner")["threadExternalId"] == writes[-1]["thread"]
    assert writes[0]["created"] == writes[-1]["created"]


def test_unconditional_purge_boundaries_unused_state_and_cache_eviction(state):
    store, db, clock, evicted = state
    for name, age in [
        ("L", 3600),
        ("N", 86339),
        ("B", 86340),
        ("X", 86400),
        ("O", 90000),
    ]:
        sid = store.initialize(name)
        db.rows[sid]["initialized"] = utc(clock[0] - age)
        db.rows[sid]["expires"] = utc(clock[0] - age + LIFETIME)
    store.sweep()
    assert sorted(evicted) == ["B", "O", "X"]
    assert {r["owner"] for r in db.rows.values()} == {"L", "N"}
    clock[0] += 30
    store.sweep()
    assert set(evicted) == {"B", "N", "X", "O"}
    store.invalidate("L")
    assert not db.rows


def test_storage_and_missed_maintenance_fail_closed_until_complete_catchup(state):
    store, db, clock, evicted = state
    sid = store.initialize("F")
    db.rows[sid]["initialized"] = utc(clock[0] - 86280)
    db.rows[sid]["expires"] = utc(clock[0] + 120)
    db.fail = True
    clock[0] += 180
    with pytest.raises(OAuthError):
        store.sweep()
    assert not store.ready()
    with pytest.raises(OAuthError):
        store.helper(sid, "F")
    with pytest.raises(OAuthError):
        store.initialize("new")
    assert sid in db.rows
    db.fail = False
    assert store.sweep() is True
    assert store.ready() and sid not in db.rows and "F" in evicted
    with pytest.raises(OAuthError):
        store.helper(sid, "F", "cannot recreate")
    assert sid not in db.rows


def test_expired_restore_cannot_reset_expiry_or_ownership(state):
    store, db, clock, _ = state
    sid = store.initialize("owner")
    saved = copy.deepcopy(db.rows)
    clock[0] += LIFETIME
    db.rows = saved
    with pytest.raises(OAuthError):
        store.helper(sid, "owner")
    store.sweep()
    assert sid not in db.rows
