"""Mongo configuration rejects insecure settings without leaking credentials."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from onto_mcp import oauth_state

URI = "mongodb://runtime:synthetic-password@mongo.test/onto_mcp?authSource=onto_mcp"
INDEXES = [
    {"name": "_id_", "key": {"_id": 1}},
    {"name": "oauth_sessions_owner", "key": {"owner_key": 1}},
    {
        "name": "oauth_sessions_purge_ttl",
        "key": {"purge_at": 1},
        "expireAfterSeconds": 0,
    },
]


def configured(monkeypatch, indexes=INDEXES):
    collection = Mock()
    collection.list_indexes.return_value = indexes
    database = Mock()
    database.get_collection.return_value = collection
    client = Mock()
    client.__getitem__ = Mock(return_value=database)
    factory = Mock(return_value=client)
    monkeypatch.setattr(oauth_state, "MongoClient", factory)
    service = SimpleNamespace(evict=Mock(), cache_owners=lambda: ())
    return service, factory, client, database


def test_verified_tls_primary_journal_and_no_schema_writes(monkeypatch):
    service, factory, client, database = configured(monkeypatch)
    store = oauth_state.configured_store(service, {"ONTO_OAUTH_STATE_MONGO_URI": URI})
    assert service.invalidate_connection == store.invalidate
    opts = factory.call_args.kwargs
    assert opts["tls"] and not opts["tlsAllowInvalidCertificates"]
    assert not opts["tlsAllowInvalidHostnames"] and not opts["retryWrites"]
    assert opts["serverSelectionTimeoutMS"] == opts["socketTimeoutMS"] == 10000
    client.__getitem__.assert_called_once_with("onto_mcp")
    database.get_collection.assert_called_once()
    opts = database.get_collection.call_args.kwargs
    assert opts["read_preference"] == oauth_state.ReadPreference.PRIMARY
    assert opts["write_concern"].document == {"w": 1, "j": True, "wtimeout": 10000}
    assert [call[0] for call in store.collection.mock_calls] == ["list_indexes"]


@pytest.mark.parametrize(
    "uri",
    [
        "",
        "postgresql://runtime:synthetic-password@mongo.test/db",
        "mongodb://mongo.test/db",
        URI + "&tls=false",
        URI + "&ssl=false",
        URI + "&tlsInsecure=true",
        URI + "&tlsAllowInvalidCertificates=true",
        URI + "&tlsAllowInvalidHostnames=true",
        URI + "&TLS=true&tls=true",
    ],
)
def test_bad_uri_fails_closed_and_secret_free(monkeypatch, uri):
    service, factory, _, _ = configured(monkeypatch)
    with pytest.raises(OSError) as error:
        oauth_state.configured_store(service, {"ONTO_OAUTH_STATE_MONGO_URI": uri})
    assert "synthetic-password" not in str(error.value)
    factory.assert_not_called()


@pytest.mark.parametrize(
    "indexes", [INDEXES[:2], INDEXES[:2] + [dict(INDEXES[2], expireAfterSeconds=60)]]
)
def test_missing_or_conflicting_indexes_close_client(monkeypatch, indexes):
    service, _, client, _ = configured(monkeypatch, indexes)
    with pytest.raises(OSError):
        oauth_state.configured_store(service, {"ONTO_OAUTH_STATE_MONGO_URI": URI})
    client.close.assert_called_once()


def test_connection_exception_is_redacted(monkeypatch):
    service, factory, _, _ = configured(monkeypatch)
    factory.side_effect = RuntimeError(URI)
    with pytest.raises(OSError) as error:
        oauth_state.configured_store(service, {"ONTO_OAUTH_STATE_MONGO_URI": URI})
    assert error.value.__context__ is None
    assert "synthetic-password" not in str(error.value)
