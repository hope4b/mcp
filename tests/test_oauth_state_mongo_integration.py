"""Opt-in tests against a disposable, authenticated MongoDB 6 with verified TLS.

Never point these at PREPROD: the harness requires an explicit disposable opt-in
and creates only a random mcp_test_* database, dropping it after execution.
"""

import os
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from pymongo import MongoClient
from pymongo.errors import OperationFailure

from onto_mcp.oauth import OAuthError
from onto_mcp.oauth_state import PURGE_AGE, OAuthStateStore, configured_store, utc

pytestmark = pytest.mark.integration


@pytest.fixture
def mongo():
    uri = os.environ.get("MCP_TEST_DISPOSABLE_MONGO_URI")
    if not uri or os.environ.get("MCP_TEST_DISPOSABLE_MONGO") != "yes":
        pytest.skip("Explicit disposable MongoDB TLS harness not configured")
    root = MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=10000)
    assert root.server_info()["version"].startswith("6.")
    name = "mcp_test_" + secrets.token_hex(8)
    db = root[name]
    properties = {
        "_id": {"bsonType": "string", "pattern": "^[A-Za-z0-9_-]{43}$"},
        "owner_key": {"bsonType": "string", "pattern": "^[0-9a-f]{64}$"},
        "initialized_at": {"bsonType": "date"},
        "expires_at": {"bsonType": "date"},
        "purge_at": {"bsonType": "date"},
        "thread_external_id": {"bsonType": ["string", "null"]},
        "created_at": {"bsonType": ["date", "null"]},
        "revision": {"bsonType": ["int", "long"], "minimum": 0},
    }
    password = secrets.token_urlsafe(24)
    try:
        collection = db.create_collection(
            "oauth_sessions",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "additionalProperties": False,
                    "required": list(properties),
                    "properties": properties,
                }
            },
            validationLevel="strict",
            validationAction="error",
        )
        collection.create_index("owner_key", name="oauth_sessions_owner")
        collection.create_index(
            "purge_at", name="oauth_sessions_purge_ttl", expireAfterSeconds=0
        )
        db.command(
            "createRole",
            "sessions",
            privileges=[
                {
                    "resource": {"db": name, "collection": "oauth_sessions"},
                    "actions": ["find", "insert", "update", "remove", "listIndexes"],
                }
            ],
            roles=[],
        )
        db.command(
            "createUser",
            "runtime",
            pwd=password,
            roles=[{"role": "sessions", "db": name}],
            mechanisms=["SCRAM-SHA-256"],
        )
        parsed = urlsplit(uri)
        options = dict(parse_qsl(parsed.query))
        options.update(authSource=name, authMechanism="SCRAM-SHA-256")
        runtime_uri = urlunsplit(
            (
                parsed.scheme,
                "runtime:" + password + "@" + parsed.netloc.split("@")[-1],
                "/" + name,
                urlencode(options),
                "",
            )
        )
        evicted = []
        service = SimpleNamespace(evict=evicted.append, cache_owners=lambda: ())
        store = configured_store(
            service,
            {
                "ONTO_OAUTH_STATE_MONGO_URI": runtime_uri,
                "ONTO_OAUTH_STATE_MONGO_DB": name,
            },
        )
        store.sweep()
        yield store, collection, evicted
        store.collection.database.client.close()
    finally:
        # Users/roles are separate system metadata and are explicitly removed.
        db.command("dropAllUsersFromDatabase", 1)
        db.command("dropAllRolesFromDatabase", 1)
        root.drop_database(name)
        root.close()


def test_real_atomic_updates_validator_and_collection_only_role(mongo):
    store, admin, _ = mongo
    owner = "a" * 64
    sid = store.initialize(owner)
    original = admin.find_one({"_id": sid})
    with ThreadPoolExecutor(8) as pool:
        results = list(
            pool.map(
                lambda n: store.helper(sid, owner, "$literal-" + str(n)), range(20)
            )
        )
    row = admin.find_one({"_id": sid})
    assert row["revision"] == 20
    assert len({result["createdAt"] for result in results}) == 1
    assert row["expires_at"] == original["expires_at"]
    assert row["initialized_at"] == original["initialized_at"]
    assert row["purge_at"] == original["purge_at"]
    assert row["thread_external_id"].startswith("$literal-")
    reconstructed = OAuthStateStore(store.collection)
    reconstructed.sweep()
    assert (
        reconstructed.helper(sid, owner)["threadExternalId"]
        == row["thread_external_id"]
    )
    with pytest.raises(OAuthError):
        store.helper(sid, "b" * 64, "foreign")
    with pytest.raises(OperationFailure) as invalid:
        store.collection.update_one({"_id": sid}, {"$set": {"unrecognized": "denied"}})
    assert invalid.value.code == 121
    with pytest.raises(OperationFailure) as forbidden:
        store.collection.create_index("revision")
    assert forbidden.value.code == 13
    store.remove(sid, owner)
    assert admin.find_one({"_id": sid}) is None


def test_real_retention_expiry_and_connection_invalidation(mongo):
    store, admin, evicted = mongo
    owner, other = "a" * 64, "b" * 64
    sid = store.initialize(owner)
    keep = store.initialize(other)
    admin.update_one({"_id": sid}, {"$set": {"expires_at": utc(time.time() - 1)}})
    with pytest.raises(OAuthError):
        store.helper(sid, owner, "cannot-recreate")
    store.invalidate(owner)
    assert admin.find_one({"_id": sid}) is None
    assert store.helper(keep, other)["threadExternalId"] is None
    admin.update_one(
        {"_id": keep},
        {
            "$set": {
                "initialized_at": utc(time.time() - PURGE_AGE - 1),
                "purge_at": utc(time.time() - 1),
            }
        },
    )
    store.sweep()
    assert other in evicted and admin.count_documents({}) == 0
