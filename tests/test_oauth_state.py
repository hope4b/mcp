"""Mongo operation double for ownership, expiry and concurrency contracts."""

import copy
import operator
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from onto_mcp.oauth import OAuthError
from onto_mcp.oauth_state import LIFETIME, OAuthStateStore, utc


class Database:
    def __init__(self, clock=lambda: 1700000000):
        self.rows = {}
        self.clock = clock
        self.lock = threading.RLock()
        self.fail = False
        self.commits = []

    def expression(self, value, row):
        if value == "$$NOW":
            return utc(self.clock())
        if isinstance(value, str) and value.startswith("$"):
            return row.get(value[1:])
        if not isinstance(value, dict):
            return value
        op, args = next(iter(value.items()))
        if op == "$literal":
            return args
        if op == "$cond":
            return self.expression(
                args[1] if self.expression(args[0], row) else args[2], row
            )
        args = [self.expression(v, row) for v in args]
        return {
            "$and": lambda: all(args),
            "$gt": lambda: args[0] > args[1],
            "$lte": lambda: args[0] <= args[1],
            "$ifNull": lambda: args[0] if args[0] is not None else args[1],
            "$add": lambda: sum(args),
        }[op]()

    def matches(self, row, query):
        if self.fail:
            raise RuntimeError("private database diagnostics")
        for key, condition in query.items():
            if key == "$expr":
                if not self.expression(condition, row):
                    return False
            elif isinstance(condition, dict):
                for op, value in condition.items():
                    actual = row.get(key)
                    if not {
                        "$gt": operator.gt,
                        "$lte": operator.le,
                        "$in": lambda a, b: a in b,
                    }[op](actual, value):
                        return False
            elif row.get(key) != condition:
                return False
        return True

    def find(self, query, projection=None):
        with self.lock:
            if self.fail:
                raise RuntimeError("private database diagnostics")
            return [
                copy.deepcopy(r) for r in self.rows.values() if self.matches(r, query)
            ]

    def find_one(self, query):
        return next(iter(self.find(query)), None)

    def insert_one(self, row):
        with self.lock:
            if self.fail:
                raise RuntimeError("private database diagnostics")
            assert row["_id"] not in self.rows
            self.rows[row["_id"]] = copy.deepcopy(row)

    def find_one_and_update(self, query, pipeline, *, upsert, return_document):
        assert upsert is False
        with self.lock:
            for row in self.rows.values():
                if self.matches(row, query):
                    changes = {
                        k: self.expression(v, row)
                        for k, v in pipeline[0]["$set"].items()
                    }
                    row.update(changes)
                    self.commits.append(copy.deepcopy(self.rows))
                    return copy.deepcopy(row)
        return None

    def find_one_and_delete(self, query):
        with self.lock:
            for sid, row in self.rows.items():
                if self.matches(row, query):
                    return self.rows.pop(sid)
        return None

    def delete_many(self, query):
        with self.lock:
            if self.fail:
                raise RuntimeError("private database diagnostics")
            for sid, row in list(self.rows.items()):
                if self.matches(row, query):
                    del self.rows[sid]


@pytest.fixture
def state():
    db = Database()
    clock = [1700000000]
    db.clock = lambda: clock[0]
    evicted = []
    store = OAuthStateStore(db, clock=lambda: clock[0], evict=evicted.append)
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
    second = OAuthStateStore(db, clock=lambda: clock[0])
    second.sweep()
    assert second.helper(sid, "owner-p") == last
    assert db.rows[sid]["revision"] == 2
    assert db.rows[sid]["expires_at"] == utc(1700000000 + LIFETIME)


def test_serialized_last_committed_save_wins(state):
    store, db, _, _ = state
    sid = store.initialize("owner")
    other = OAuthStateStore(db, clock=store.clock)
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
    assert (
        store.helper(sid, "owner")["threadExternalId"]
        == writes[-1]["thread_external_id"]
    )
    assert writes[0]["created_at"] == writes[-1]["created_at"]


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
        db.rows[sid]["initialized_at"] = utc(clock[0] - age)
        db.rows[sid]["purge_at"] = utc(clock[0] - age + 86340)
        db.rows[sid]["expires_at"] = utc(clock[0] - age + LIFETIME)
    store.sweep()
    assert sorted(evicted) == ["B", "O", "X"]
    assert {r["owner_key"] for r in db.rows.values()} == {"L", "N"}
    clock[0] += 30
    store.sweep()
    assert set(evicted) == {"B", "N", "X", "O"}
    store.invalidate("L")
    assert not db.rows


def test_storage_and_missed_maintenance_fail_closed_until_complete_catchup(state):
    store, db, clock, evicted = state
    sid = store.initialize("F")
    db.rows[sid]["initialized_at"] = utc(clock[0] - 86280)
    db.rows[sid]["purge_at"] = utc(clock[0] + 60)
    db.rows[sid]["expires_at"] = utc(clock[0] + 120)
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


def test_failed_inactive_invalidation_is_completed_before_recovery(state, monkeypatch):
    store, db, _, evicted = state
    inactive = store.initialize("inactive")
    live = store.initialize("live")
    db.fail = True
    with pytest.raises(OAuthError):
        store.invalidate("inactive")
    assert not store.ready() and inactive in db.rows
    db.fail = False
    delete = db.delete_many

    def fail_pending_delete(query):
        if query == {"owner_key": "inactive"}:
            raise RuntimeError("invalidation still unavailable")
        return delete(query)

    with monkeypatch.context() as patch:
        patch.setattr(db, "delete_many", fail_pending_delete)
        with pytest.raises(OAuthError):
            store.sweep()
    assert not store.ready() and inactive in db.rows
    with pytest.raises(OAuthError):
        store.helper(live, "live")
    store.sweep()
    assert store.ready() and inactive not in db.rows and live in db.rows
    assert "inactive" in evicted
    with pytest.raises(OAuthError):
        store.helper(inactive, "inactive", "cannot restore")


@pytest.mark.parametrize("value", [None, "replacement"])
@pytest.mark.parametrize("bound", ["expiry", "maintenance"])
def test_row_lock_wait_rechecks_validity_before_read_or_write(
    state, monkeypatch, value, bound
):
    store, db, clock, _ = state
    sid = store.initialize("owner")
    store.helper(sid, "owner", "original")
    if bound == "expiry":
        db.rows[sid]["expires_at"] = utc(clock[0] + 10)
    before = copy.deepcopy(db.rows[sid])
    waiting, release = threading.Event(), threading.Event()
    match = db.matches

    def queued_match(row, query):
        if "_id" in query:
            waiting.set()
            assert release.wait(5)
        return match(row, query)

    monkeypatch.setattr(db, "matches", queued_match)
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(store.helper, sid, "owner", value)
        try:
            assert waiting.wait(5)
            clock[0] += 10 if bound == "expiry" else 61
        finally:
            release.set()
        with pytest.raises(OAuthError) as error:
            future.result(timeout=5)
    assert error.value.status == (401 if bound == "expiry" else 503)
    assert db.rows[sid] == before


def test_literal_value_and_ttl_deleted_owner_cache_reconciliation(state):
    store, db, _, evicted = state
    sid = store.initialize("owner")
    assert store.helper(sid, "owner", "$revision")["threadExternalId"] == "$revision"
    store.cache_owners = lambda: ("owner", "ttl-already-deleted")
    store.sweep()
    assert evicted == ["ttl-already-deleted"]
    del db.rows[sid]  # TTL deletion happened before the application's sweep.
    store.sweep()
    assert "owner" in evicted


def test_partial_purge_failure_evicts_before_unknown_delete_outcome(state, monkeypatch):
    store, db, clock, evicted = state
    sid = store.initialize("owner")
    db.rows[sid]["purge_at"] = utc(clock[0])
    delete = db.delete_many

    def unknown_delete(query):
        delete(query)
        raise RuntimeError("acknowledgement lost after deletion")

    monkeypatch.setattr(db, "delete_many", unknown_delete)
    with pytest.raises(OAuthError):
        store.sweep()
    assert sid not in db.rows and "owner" in evicted
    assert not store.ready()
    monkeypatch.setattr(db, "delete_many", delete)
    store.sweep()
    assert store.ready()
