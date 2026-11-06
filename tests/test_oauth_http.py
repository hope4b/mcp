"""HTTP authority/session isolation with inert provider and storage dependencies."""

import asyncio
import json
import threading
from unittest.mock import patch

import pytest
from test_oauth_authorization import (
    BASE,
    CONFIG,
    EXPECTED_READ,
    EXPECTED_WRITE,
    NOW,
    Provider,
    introspection,
    token,
)
from test_oauth_state import Database

from onto_mcp import api_resources, server
from onto_mcp.http_auth import get_http_api_key
from onto_mcp.oauth import READ, WRITE, OAuthService, current_authority
from onto_mcp.oauth_http import DualAuthASGIApp
from onto_mcp.oauth_state import OAuthStateStore


async def request(app, headers=(), payload=None, method="POST", path="/mcp"):
    output = []
    body = json.dumps(payload or {}).encode()
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        output.append(message)

    await app(
        {"type": "http", "path": path, "method": method, "headers": list(headers)},
        receive,
        send,
    )
    return output


def test_dual_http_boundary_sessions_discovery_and_no_fallback():
    provider = Provider()
    service = OAuthService(CONFIG, http=provider, clock=lambda: NOW)
    db = Database()
    store = OAuthStateStore(db, clock=lambda: NOW)
    store.sweep()
    calls = []

    async def key_app(scope, receive, send):
        calls.append(("key", get_http_api_key(), current_authority.get()))
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def oauth_app(scope, receive, send):
        a = current_authority.get()
        calls.append(("oauth", a.claims.client, a.session_id))
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    app = DualAuthASGIApp(
        server.HttpApiKeyASGIApp(key_app), oauth_app, service=service, store=store
    )

    async def exercise():
        info = await request(
            app,
            path="/.well-known/oauth-protected-resource/mcp",
            method="GET",
            headers=[(b"host", b"evil.test")],
        )
        assert json.loads(info[-1]["body"]) == CONFIG.metadata()
        original = token()
        headers = [(b"authorization", ("Bearer " + original).encode())]
        init = await request(app, headers, {"method": "initialize"})
        assert init[0]["status"] == 200
        sid = dict(init[0]["headers"])[b"mcp-session-id"]
        assert len(sid) == 43
        assert calls[-1][1] == "client-p"
        assert (await request(app, headers + [(b"mcp-session-id", sid)]))[0][
            "status"
        ] == 200
        # A new jti alone preserves the full tuple binding; client change does not.
        renewed = dict(BASE, jti="access-2")
        provider.response = introspection(renewed)
        renewed_headers = [
            (b"authorization", ("Bearer " + token(renewed)).encode()),
            (b"mcp-session-id", sid),
        ]
        assert (await request(app, renewed_headers))[0]["status"] == 200
        other = dict(BASE, azp="client-q")
        provider.response = introspection(other)
        qheaders = [(b"authorization", ("Bearer " + token(other)).encode())]
        assert (await request(app, qheaders + [(b"mcp-session-id", sid)]))[0][
            "status"
        ] == 401
        qinit = await request(app, qheaders, {"method": "initialize"})
        assert qinit[0]["status"] == 200
        assert dict(qinit[0]["headers"])[b"mcp-session-id"] != sid
        assert (await request(app, [(b"x-api-key", b" key bytes ")]))[0][
            "status"
        ] == 204
        assert calls[-1] == ("key", " key bytes ", None)
        # A key cannot borrow OAuth state; failed OAuth never dispatches a key app.
        assert (await request(app, [(b"x-api-key", b"k"), (b"mcp-session-id", sid)]))[
            0
        ]["status"] == 401
        provider.response = {"active": False}
        count = len(calls)
        denied = await request(app, headers + [(b"mcp-session-id", sid)])
        assert denied[0]["status"] == 401 and len(calls) == count
        assert (
            CONFIG.metadata_url
            in dict(denied[0]["headers"])[b"www-authenticate"].decode()
        )
        assert (await request(app))[0]["status"] == 401
        before = len(provider.posts)
        assert (await request(app, [(b"authorization", b"Bearer bad,token")]))[0][
            "status"
        ] == 400
        assert (await request(app, headers + [(b"x-api-key", b"key")]))[0][
            "status"
        ] == 400
        assert len(provider.posts) == before

    asyncio.run(exercise())


def test_local_helpers_do_not_exchange_and_preserve_contract():
    provider = Provider()
    service = OAuthService(CONFIG, http=provider, clock=lambda: NOW)
    db = Database()
    store = OAuthStateStore(db, clock=lambda: NOW)
    store.sweep()
    data = dict(BASE, scope=READ + " " + WRITE)
    provider.response = introspection(data)
    authority = service.authenticate(token(data))
    authority.state_store = store
    authority.session_id = store.initialize(authority.claims.connection_key)
    context = current_authority.set(authority)
    try:
        empty = api_resources.saveOntoAIThreadID("  ", None)
        assert empty == {
            "contextId": authority.session_id,
            "threadExternalId": None,
            "message": "thread_external_id is required.",
        }
        assert (
            api_resources.getOntoAIThreadID(None)["message"]
            == "No session state stored for this context."
        )
        saved = api_resources.saveOntoAIThreadID("  thread-one  ", None)
        assert saved["threadExternalId"] == "thread-one"
        assert api_resources.getOntoAIThreadID(None) == saved
        replaced = api_resources.saveOntoAIThreadID("thread-two", None)
        assert replaced["createdAt"] == saved["createdAt"]
        assert all(u.endswith("/introspect") for u, _ in provider.posts)
    finally:
        current_authority.reset(context)


def test_timed_out_worker_cannot_start_late_send():
    provider = Provider()
    service = OAuthService(CONFIG, http=provider, clock=lambda: NOW)
    authority = service.authenticate(token())
    entered = threading.Event()
    release = threading.Event()
    done = threading.Event()

    def handler():
        entered.set()
        try:
            release.wait(2)
            api_resources._request_with_canonical_auth("GET", "https://core.test/user")
        finally:
            done.set()

    handler.__name__ = "list_available_realms"
    context = current_authority.set(authority)
    try:
        with (
            patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
            patch.object(api_resources, "_HTTP_MCP_TOOL_TIMEOUT_SECONDS", 0.02),
            patch.object(api_resources.requests, "request") as send,
        ):
            result = api_resources._wrap_tool_with_timeout(handler)()
            assert entered.is_set() and authority.cancelled.is_set()
            release.set()
            assert done.wait(2)
            send.assert_not_called()
            assert "timeout" in result.lower()
    finally:
        release.set()
        current_authority.reset(context)


def test_established_dependency_errors_survive_specialized_error_catching():
    provider = Provider()
    service = OAuthService(CONFIG, http=provider, clock=lambda: NOW)
    authority = service.authenticate(token())

    def handler():
        provider.response = b"not JSON"
        try:
            api_resources._request_with_canonical_auth("GET", "https://core.test/user")
        except Exception:  # noqa: BLE001
            return {"specialized": "would otherwise hide auth dependency failure"}

    handler.__name__ = "list_available_realms"
    context = current_authority.set(authority)
    try:
        with (
            patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
            pytest.raises(Exception, match="dependency_unavailable"),
        ):
            api_resources._wrap_tool_with_timeout(handler)()
    finally:
        current_authority.reset(context)


def test_real_fastmcp_oauth_transport_metadata_helpers_and_resources():
    from starlette.testclient import TestClient

    from onto_mcp import oauth_http

    provider = Provider()
    service = OAuthService(CONFIG, http=provider, clock=lambda: NOW)
    db = Database()
    store = OAuthStateStore(db, clock=lambda: NOW)
    data = dict(BASE, scope=READ + " " + WRITE)
    provider.response = introspection(data)

    def decoded(response):
        if response.headers.get("content-type", "").startswith("text/event-stream"):
            return json.loads(
                next(
                    line[6:]
                    for line in response.text.splitlines()
                    if line.startswith("data: ")
                )
            )
        return response.json()

    with (
        patch.object(oauth_http.OAuthConfig, "from_env", return_value=CONFIG),
        patch.object(oauth_http, "OAuthService", return_value=service),
        patch.object(oauth_http, "configured_store", return_value=store),
    ):
        app = server._build_http_app()
        with TestClient(app) as client:
            headers = {
                "authorization": "Bearer " + token(data),
                "accept": "application/json, text/event-stream",
            }
            init = client.post(
                "/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "synthetic-test", "version": "1"},
                    },
                },
            )
            assert init.status_code == 200
            assert "MCP cannot prove" in decoded(init)["result"]["instructions"]
            headers["mcp-session-id"] = init.headers["mcp-session-id"]
            assert len(headers["mcp-session-id"]) == 43

            def rpc(method, params):
                response = client.post(
                    "/mcp",
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": method,
                        "params": params,
                    },
                )
                assert response.status_code == 200
                return decoded(response)["result"]

            tools = rpc("tools/list", {})["tools"]
            assert len(tools) == 70
            read = [t for t in tools if t["annotations"]["readOnlyHint"]]
            assert {t["name"] for t in read} == EXPECTED_READ
            assert {t["name"] for t in tools} == EXPECTED_READ | EXPECTED_WRITE
            for tool in tools:
                expected = [READ] if tool["name"] in EXPECTED_READ else [READ, WRITE]
                assert tool["_meta"]["onto:requiredScopes"] == expected
            assert all(t["_meta"]["onto:requiredScopes"] == [READ] for t in read)
            saved = rpc(
                "tools/call",
                {
                    "name": "saveOntoAIThreadID",
                    "arguments": {"thread_external_id": " thread-id "},
                },
            )
            assert not saved.get("isError")
            assert saved["structuredContent"]["threadExternalId"] == "thread-id"
            fetched = rpc("tools/call", {"name": "getOntoAIThreadID", "arguments": {}})
            assert (
                fetched["structuredContent"]["contextId"] == headers["mcp-session-id"]
            )
            with patch.object(
                api_resources,
                "_get_user_spaces_data",
                return_value=[{"id": "r", "name": "Realm"}],
            ):
                result = rpc("resources/read", {"uri": "onto://spaces"})
                assert "Realm" in json.dumps(result)
            provider.response = {"active": False}
            refused = client.post(
                "/mcp",
                headers=headers,
                json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
            )
            assert refused.status_code == 401
            assert refused.json() == {"error": "invalid_token"}


@pytest.mark.parametrize("replace_identities", [False, True])
@pytest.mark.parametrize("audience_is_resource", [False, True])
def test_overlapping_dual_http_identities_and_configured_trust(
    replace_identities, audience_is_resource
):
    from dataclasses import replace
    from types import SimpleNamespace

    import jwt

    from onto_mcp.oauth import ACCESS_TOKEN

    config = (
        replace(
            CONFIG,
            issuer="https://other-issuer.test/realm/new",
            resource="https://other-mcp.test/mcp",
            audience="other-ingress",
            allowed_clients=("other-p", "other-q"),
            exchange_client="other-exchange",
            core_audience="other-core",
        )
        if replace_identities
        else CONFIG
    )
    if audience_is_resource:
        config = replace(config, audience=config.resource)
    from onto_mcp.oauth import OAuthConfig

    assert (
        OAuthConfig.from_env(
            {
                "ONTO_OAUTH_ENABLED": "true",
                "ONTO_OAUTH_ISSUER": config.issuer,
                "ONTO_OAUTH_RESOURCE": config.resource,
                "ONTO_OAUTH_AUDIENCE": config.audience,
                "ONTO_OAUTH_ALLOWED_CLIENT_IDS": json.dumps(config.allowed_clients),
                "ONTO_OAUTH_EXCHANGE_CLIENT_ID": config.exchange_client,
                "ONTO_OAUTH_EXCHANGE_CLIENT_SECRET": config.exchange_secret,
                "ONTO_OAUTH_CORE_AUDIENCE": config.core_audience,
            }
        )
        == config
    )

    class RoutingProvider(Provider):
        def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            data = jwt.decode(
                kwargs["data"].get("token") or kwargs["data"].get("subject_token"),
                options={"verify_signature": False},
            )
            if url.endswith("/introspect"):
                result = introspection(data)
            else:
                result = {
                    "access_token": token(
                        dict(
                            data, azp=config.exchange_client, aud=[config.core_audience]
                        )
                    ),
                    "token_type": "Bearer",
                    "issued_token_type": ACCESS_TOKEN,
                }
            return SimpleNamespace(status_code=200, content=json.dumps(result).encode())

    provider = RoutingProvider()
    provider.config = config
    service = OAuthService(config, http=provider, clock=lambda: NOW)
    store = OAuthStateStore(Database(), clock=lambda: NOW)
    store.sweep()
    observed, sends = [], []
    worker_barrier = threading.Barrier(3)

    def outbound(method, url, **kwargs):
        authority = current_authority.get()
        headers = kwargs["headers"]
        if authority is None:
            assert headers["X-API-Key"] == "request-key"
            assert "Authorization" not in headers
            identity = "key"
        else:
            assert get_http_api_key() is None
            assert "X-API-Key" not in headers
            delegated = jwt.decode(
                headers["Authorization"][7:], options={"verify_signature": False}
            )
            assert delegated["azp"] == config.exchange_client
            assert delegated["aud"] == [config.core_audience]
            assert delegated["sub"] == authority.claims.subject
            identity = authority.claims.client
        sends.append(identity)
        return SimpleNamespace(status_code=200)

    def worker():
        authority = current_authority.get()
        identity = authority.claims.client if authority else "key"
        observed.append(
            (
                identity,
                get_http_api_key(),
                authority.claims.connection_key if authority else None,
            )
        )
        worker_barrier.wait(timeout=5)
        api_resources._request_with_canonical_auth("GET", "https://core.test/user")
        assert (
            current_authority.get().claims.client if authority else "key"
        ) == identity
        return identity

    async def exercise():
        entered = []
        all_entered = asyncio.Event()

        async def handler(scope, receive, send):
            a = current_authority.get()
            identity = a.claims.client if a else "key"
            entered.append(identity)
            if len(entered) == 3:
                all_entered.set()
            await asyncio.wait_for(all_entered.wait(), timeout=5)
            assert await asyncio.to_thread(worker) == identity
            assert (current_authority.get().claims.client if a else "key") == identity
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"{}"})

        app = DualAuthASGIApp(
            server.HttpApiKeyASGIApp(handler), handler, service=service, store=store
        )
        hostile = [
            (b"host", b"evil.test"),
            (b"forwarded", b"host=evil.test;proto=http"),
            (b"x-forwarded-host", b"evil.test"),
            (b"x-forwarded-proto", b"http"),
        ]
        discovery = await request(
            app, hostile, method="GET", path="/.well-known/oauth-protected-resource/mcp"
        )
        assert json.loads(discovery[-1]["body"]) == {
            "resource": config.resource,
            "authorization_servers": [config.issuer],
            "scopes_supported": [READ, WRITE],
        }
        headers = [[(b"x-api-key", b"request-key")]]
        for client in config.allowed_clients:
            claims = dict(BASE, iss=config.issuer, azp=client, aud=[config.audience])
            headers.append([(b"authorization", ("Bearer " + token(claims)).encode())])
        results = await asyncio.gather(
            *(
                request(
                    app,
                    h + hostile,
                    {
                        "method": "initialize",
                        "params": {
                            "issuer": "https://evil.test",
                            "audience": "evil",
                            "client_id": "evil",
                        },
                    },
                )
                for h in headers
            )
        )
        assert all(r[0]["status"] == 200 for r in results)
        assert sorted(entered) == sorted(["key", *config.allowed_clients])
        # A hostile supplied MCP ID cannot become a provider identity/trust source.
        rejected = await request(
            app, headers[1] + [(b"mcp-session-id", b"evil-session")]
        )
        assert rejected[0]["status"] == 401
        assert current_authority.get() is None
        assert get_http_api_key() is None

    with (
        patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
        patch.object(api_resources, "IS_HTTP_TRANSPORT", True),
        patch.object(api_resources, "ONTO_API_KEY", "configured-key"),
        patch.object(api_resources.requests, "request", side_effect=outbound),
    ):
        asyncio.run(exercise())
    assert sorted(sends) == sorted(["key", *config.allowed_clients])
    assert len({row[2] for row in observed if row[0] != "key"}) == 2
    assert [row[1] for row in observed if row[0] == "key"] == ["request-key"]
    assert all(row[1] is None for row in observed if row[0] != "key")
    assert set(provider.gets) == {
        config.issuer + "/.well-known/openid-configuration",
        config.issuer + "/certs",
    }
    assert all(
        u
        in {
            config.issuer + "/protocol/openid-connect/token/introspect",
            config.issuer + "/protocol/openid-connect/token",
        }
        for u, _ in provider.posts
    )
    assert all(
        k["auth"] == (config.exchange_client, config.exchange_secret)
        for _, k in provider.posts
    )
    assert all(
        k["data"]["audience"] == config.core_audience
        for u, k in provider.posts
        if u.endswith("/token")
    )


@pytest.mark.parametrize(
    "fault,status", [("validation", 401), ("introspection", 503), ("exchange", 503)]
)
def test_dual_http_oauth_faults_never_dispatch_available_key_or_core(fault, status):
    from test_oauth_authorization import exchanged

    provider = Provider()
    provider.exchange = exchanged()
    service = OAuthService(CONFIG, http=provider, clock=lambda: NOW)
    store = OAuthStateStore(Database(), clock=lambda: NOW)
    store.sweep()
    key_calls = []

    async def key_app(scope, receive, send):
        key_calls.append(True)

    async def oauth_app(scope, receive, send):
        # Inject a fault within a protected final worker boundary while the
        # configured key remains available. The dual app must sanitize it.
        await asyncio.to_thread(
            api_resources._request_with_canonical_auth, "GET", "https://core.test/user"
        )
        raise AssertionError("fault dispatched")

    app = DualAuthASGIApp(
        server.HttpApiKeyASGIApp(key_app), oauth_app, service=service, store=store
    )
    if fault == "introspection":
        provider.status = 500
    elif fault == "exchange":
        provider.exchange["access_token"] = ""
    carried = "invalid.jwt.token" if fault == "validation" else token()
    with (
        patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
        patch.object(api_resources, "IS_HTTP_TRANSPORT", True),
        patch.object(api_resources, "ONTO_API_KEY", "configured-key"),
        patch.object(api_resources.requests, "request") as send,
    ):
        from onto_mcp.http_auth import reset_http_api_key, set_http_api_key

        stale_key = set_http_api_key(b"stale-request-session-key")
        try:
            result = asyncio.run(
                request(
                    app,
                    [(b"authorization", ("Bearer " + carried).encode())],
                    {"method": "initialize"},
                )
            )
        finally:
            reset_http_api_key(stale_key)
        assert result[0]["status"] == status
        assert json.loads(result[-1]["body"]) == {
            "error": "invalid_token" if status == 401 else "dependency_unavailable"
        }
        assert key_calls == []
        send.assert_not_called()
        assert not service._cache
