"""MCP-owned MongoDB bindings; API-key helper backing is never used."""

from __future__ import annotations

import secrets
import threading
import time
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlsplit

from pymongo import MongoClient, ReturnDocument
from pymongo.read_preferences import ReadPreference
from pymongo.write_concern import WriteConcern

from .oauth import OAuthError, dependency_error

LIFETIME = 86400
PURGE_AGE = 86340
SWEEP_INTERVAL = 30


def utc(seconds):
    return datetime.fromtimestamp(seconds, UTC)


class OAuthStateStore:
    def __init__(
        self,
        collection,
        *,
        clock=time.time,
        evict=lambda key: None,
        cache_owners=lambda: (),
    ):
        self.collection, self.clock, self.evict = collection, clock, evict
        self.cache_owners = cache_owners
        self.last_sweep = None
        self.maintenance_ok = False
        self._pending_invalidations = set()
        self._maintenance_lock = threading.RLock()

    def ready(self):
        return (
            self.maintenance_ok
            and not self._pending_invalidations
            and self.last_sweep is not None
            and 0 <= self.clock() - self.last_sweep <= 60
        )

    def sweep(self):
        with self._maintenance_lock:
            started = self.clock()
            missed = self.last_sweep is not None and started - self.last_sweep > 60
            self.maintenance_ok = False
            try:
                for owner in self._pending_invalidations:
                    self.collection.delete_many({"owner_key": owner})
                    self.evict(owner)
                # Evict before deleting: a partial/uncertain delete is retried,
                # and cannot strand credentials whose rows have disappeared.
                expired = {"purge_at": {"$lte": utc(started)}}
                for row in self.collection.find(expired, {"owner_key": 1}):
                    self.evict(row["owner_key"])
                self.collection.delete_many(expired)
                # TTL can remove a document before our sweep sees its owner.
                # Reconcile only cached owner hashes, never provider credentials.
                cached = set(self.cache_owners())
                if cached:
                    live = {
                        row["owner_key"]
                        for row in self.collection.find(
                            {
                                "owner_key": {"$in": list(cached)},
                                "purge_at": {"$gt": utc(started)},
                            },
                            {"owner_key": 1},
                        )
                    }
                    for owner in cached - live:
                        self.evict(owner)
                self._pending_invalidations.clear()
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
            self.collection.insert_one(
                {
                    "_id": session_id,
                    "owner_key": owner,
                    "initialized_at": utc(now),
                    "expires_at": utc(now + LIFETIME),
                    "purge_at": utc(now + PURGE_AGE),
                    "thread_external_id": None,
                    "created_at": None,
                    "revision": 0,
                }
            )
            return session_id
        except Exception:  # noqa: BLE001, S110
            pass
        self.maintenance_ok = False
        raise dependency_error()

    def _filter(self, session_id, owner):
        if not self.ready():
            raise dependency_error()
        return {
            "_id": session_id,
            "owner_key": owner,
            "expires_at": {"$gt": utc(self.clock())},
            "$expr": {
                "$and": [
                    {"$gt": ["$expires_at", "$$NOW"]},
                    {"$lte": ["$$NOW", utc(self.last_sweep + 60)]},
                ]
            },
        }

    def _check(self, row):
        if not self.ready():
            raise dependency_error()
        if row is None or row["expires_at"] <= utc(self.clock()):
            raise OAuthError()
        return row

    def require(self, session_id, owner):
        self.helper(session_id, owner)

    def helper(self, session_id, owner, value=None):
        try:
            query = self._filter(session_id, owner)
            if value is None:
                row = self.collection.find_one(query)
            else:
                # One atomic server operation: no read/modify/write or upsert.
                # Literal protects values such as "$field" from expression use.
                valid = {
                    "$and": [
                        {"$gt": ["$expires_at", "$$NOW"]},
                        {"$lte": ["$$NOW", utc(self.last_sweep + 60)]},
                    ]
                }
                row = self.collection.find_one_and_update(
                    query,
                    [
                        {
                            "$set": {
                                "thread_external_id": {
                                    "$cond": [
                                        valid,
                                        {"$literal": value},
                                        "$thread_external_id",
                                    ]
                                },
                                "created_at": {
                                    "$cond": [
                                        valid,
                                        {"$ifNull": ["$created_at", "$$NOW"]},
                                        "$created_at",
                                    ]
                                },
                                "revision": {
                                    "$cond": [
                                        valid,
                                        {"$add": ["$revision", 1]},
                                        "$revision",
                                    ]
                                },
                            }
                        }
                    ],
                    upsert=False,
                    return_document=ReturnDocument.AFTER,
                )
            row = self._check(row)
            thread_id = row["thread_external_id"]
            result = {"contextId": session_id, "threadExternalId": thread_id}
            if thread_id is None:
                result["message"] = "No session state stored for this context."
            else:
                result["createdAt"] = row["created_at"].astimezone(UTC).isoformat()
            return result
        except OAuthError:
            raise
        except Exception:  # noqa: BLE001, S110
            pass
        self.maintenance_ok = False
        raise dependency_error()

    def remove(self, session_id, owner):
        try:
            query = self._filter(session_id, owner)
            row = self.collection.find_one_and_delete(query)
            self._check(row)
            self.evict(owner)
        except OAuthError:
            raise
        except Exception:  # noqa: BLE001
            self.maintenance_ok = False
            raise dependency_error() from None

    def invalidate(self, owner):
        with self._maintenance_lock:
            self._pending_invalidations.add(owner)
            self.evict(owner)
            try:
                self.collection.delete_many({"owner_key": owner})
                self._pending_invalidations.discard(owner)
            except Exception:  # noqa: BLE001
                self.maintenance_ok = False
                raise dependency_error() from None


def _verify_indexes(collection):
    indexes = {index["name"]: index for index in collection.list_indexes()}
    expected = {
        "_id_": ({"_id": 1}, None),
        "oauth_sessions_owner": ({"owner_key": 1}, None),
        "oauth_sessions_purge_ttl": ({"purge_at": 1}, 0),
    }
    for name, (keys, ttl) in expected.items():
        index = indexes.get(name, {})
        if (
            dict(index.get("key", {})) != keys
            or index.get("expireAfterSeconds") != ttl
            or index.get("partialFilterExpression")
            or index.get("sparse", False)
            or (name != "_id_" and index.get("unique", False))
        ):
            raise ValueError("Missing or conflicting provisioned OAuth state index")


def configured_store(service, env):
    client = None
    try:
        uri = env.get("ONTO_OAUTH_STATE_MONGO_URI", "")
        database = env.get("ONTO_OAUTH_STATE_MONGO_DB", "onto_mcp")
        collection_name = env.get("ONTO_OAUTH_STATE_MONGO_COLLECTION", "oauth_sessions")
        parsed = urlsplit(uri)
        options = parse_qsl(parsed.query, keep_blank_values=True)
        lowered = [key.lower() for key, _ in options]
        if (
            parsed.scheme not in {"mongodb", "mongodb+srv"}
            or not parsed.hostname
            or not parsed.username
            or not parsed.password
            or not database.strip()
            or not collection_name.strip()
            or len(lowered) != len(set(lowered))
        ):
            raise ValueError()
        # Constructor options override URI options; reject contradictory or
        # insecure requests as configuration errors rather than silently fixing them.
        for key, value in options:
            name = key.lower()
            if name in {"tls", "ssl"} and value.lower() != "true":
                raise ValueError()
            if (
                name
                in {
                    "tlsinsecure",
                    "tlsallowinvalidcertificates",
                    "tlsallowinvalidhostnames",
                }
                and value.lower() != "false"
            ):
                raise ValueError()
        client = MongoClient(
            uri,
            tls=True,
            tlsAllowInvalidCertificates=False,
            tlsAllowInvalidHostnames=False,
            retryWrites=False,
            connect=False,
            tz_aware=True,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
        )
        collection = client[database].get_collection(
            collection_name,
            read_preference=ReadPreference.PRIMARY,
            write_concern=WriteConcern(w=1, j=True, wtimeout=10000),
        )
        _verify_indexes(collection)
        store = OAuthStateStore(
            collection, evict=service.evict, cache_owners=service.cache_owners
        )
        service.invalidate_connection = store.invalidate
        return store
    except Exception:  # noqa: BLE001
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110
                pass
    raise OSError(
        "OAuth state requires authenticated MongoDB with verified TLS and provisioned indexes."
    ) from None
