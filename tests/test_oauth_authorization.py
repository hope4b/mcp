"""Synthetic producer/consumer oracle; no external provider or Core traffic."""

import asyncio
import base64
import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from onto_mcp import api_resources
from onto_mcp.http_auth import InvalidHttpCredentials, classify_http_credentials
from onto_mcp.oauth import (
    ACCESS_TOKEN,
    MARKERS,
    READ,
    READ_TOOLS,
    RESOURCES,
    WRITE,
    WRITE_TOOLS,
    OAuthConfig,
    OAuthError,
    OAuthService,
    audiences,
    current_authority,
    provider_session,
    scopes,
)
from onto_mcp.oauth_policy import represented_policy

# Fixed approved AC-03 oracle, independent of runtime classification constants.
SCOPE_INVENTORY = json.loads(
    (Path(__file__).parent / "fixtures" / "oauth_scope_inventory.json").read_text()
)
EXPECTED_READ = frozenset(SCOPE_INVENTORY["read"])
EXPECTED_WRITE = frozenset(SCOPE_INVENTORY["read_write"])
EXPECTED_RESOURCES = frozenset(SCOPE_INVENTORY["resources"])

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
NOW = 1700000000
CONFIG = OAuthConfig(
    True,
    "https://issuer.test/realm/demo",
    "https://mcp.test/mcp",
    "ingress-a",
    ("client-p", "client-q"),
    "exchange-r",
    "synthetic-secret",
    "core-s",
)
BASE = {
    "iss": CONFIG.issuer,
    "sub": "user-u",
    "azp": "client-p",
    "jti": "access-1",
    "typ": "Bearer",
    "aud": ["ingress-a", "aux"],
    "exp": NOW + 300,
    "nbf": 0,
    "sid": "session-1",
    "scope": "openid " + READ,
}


def token(data=None, key=KEY):
    return jwt.encode(
        BASE if data is None else data,
        key,
        algorithm="RS256",
        headers={"kid": "test-key", "typ": "JWT"},
    )


def introspection(data=None):
    return dict(
        active=True,
        client_id=(data or BASE)["azp"],
        token_type="Bearer",
        **(BASE if data is None else data),
    )


class Provider:
    def __init__(self):
        self.response = introspection()
        self.posts = []
        self.gets = []
        self.exchange = None
        self.post_hook = None
        self.status = 200
        self.config = CONFIG

    def get(self, url, **kwargs):
        self.gets.append(url)
        if url.endswith("openid-configuration"):
            data = {
                "issuer": self.config.issuer,
                "jwks_uri": self.config.issuer + "/certs",
            }
        else:
            key = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key()))
            key.update(kid="test-key", alg="RS256", use="sig")
            data = {"keys": [key]}
        return SimpleNamespace(status_code=200, content=json.dumps(data).encode())

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        if self.post_hook:
            self.post_hook(url)
        data = self.response if url.endswith("introspect") else self.exchange
        if isinstance(data, Exception):
            raise data
        if isinstance(data, bytes):
            return SimpleNamespace(status_code=self.status, content=data)
        return SimpleNamespace(
            status_code=self.status, content=json.dumps(data).encode()
        )


@pytest.fixture
def setup():
    provider = Provider()
    clock = [NOW]
    service = OAuthService(CONFIG, http=provider, clock=lambda: clock[0])
    return service, provider, clock


def assert_error(status, call):
    with pytest.raises(OAuthError) as error:
        call()
    assert error.value.status == status
    assert "synthetic-secret" not in str(error.value)
    return error.value


def test_configuration_and_represented_provider_contract():
    env = {
        "ONTO_OAUTH_ENABLED": "true",
        "ONTO_OAUTH_ISSUER": CONFIG.issuer,
        "ONTO_OAUTH_RESOURCE": CONFIG.resource,
        "ONTO_OAUTH_AUDIENCE": CONFIG.audience,
        "ONTO_OAUTH_ALLOWED_CLIENT_IDS": json.dumps(CONFIG.allowed_clients),
        "ONTO_OAUTH_EXCHANGE_CLIENT_ID": CONFIG.exchange_client,
        "ONTO_OAUTH_EXCHANGE_CLIENT_SECRET": CONFIG.exchange_secret,
        "ONTO_OAUTH_CORE_AUDIENCE": CONFIG.core_audience,
    }
    assert OAuthConfig.from_env(env) == CONFIG
    for key in env:
        if key != "ONTO_OAUTH_ENABLED":
            bad = dict(env)
            del bad[key]
            with pytest.raises(EnvironmentError, match="Invalid OAuth configuration"):
                OAuthConfig.from_env(bad)
    for value in ("{}", "[]", '["a","a"]', "[1]", '[""]', "null", "not json"):
        with pytest.raises(EnvironmentError):
            OAuthConfig.from_env(dict(env, ONTO_OAUTH_ALLOWED_CLIENT_IDS=value))
    for key, value in [
        ("ONTO_OAUTH_ISSUER", "http://issuer.test"),
        ("ONTO_OAUTH_RESOURCE", "https://mcp.test/other"),
        ("ONTO_OAUTH_EXCHANGE_CLIENT_ID", "client-p"),
    ]:
        with pytest.raises(EnvironmentError):
            OAuthConfig.from_env(dict(env, **{key: value}))
    assert not OAuthConfig.from_env({"ONTO_OAUTH_ENABLED": "false"}).enabled
    assert "synthetic-secret" not in repr(CONFIG)
    for config in (
        CONFIG,
        replace(CONFIG, core_audience="different-core", audience=CONFIG.resource),
    ):
        policy = represented_policy(config)
        clients = {c["clientId"]: c for c in policy["clients"]}
        assert clients[config.core_audience]["consentRequired"] is False
        for name in config.allowed_clients:
            client = clients[name]
            assert client["consentRequired"] is True
            assert client["serviceAccountsEnabled"] is False
            assert client["directAccessGrantsEnabled"] is False
            assert client["implicitFlowEnabled"] is False
            assert client["attributes"]["pkce.code.challenge.method"] == "S256"
            assert len(client["protocolMappers"]) == 3
            for mapper in client["protocolMappers"]:
                assert mapper["config"]["introspection.token.claim"] == "true"
                assert mapper["config"]["access.token.claim"] == "true"
                assert mapper["config"]["user.session.note"].startswith("IMPERSONATOR_")
        assert policy["storage_policy"]["backup_retention_seconds"] == 604800
        assert "synthetic-secret" not in json.dumps(policy)


@pytest.mark.parametrize(
    "name", ["iss", "sub", "azp", "jti", "typ", "exp", "aud", "sid"]
)
@pytest.mark.parametrize("bad", [None, "", False, {}, []])
def test_signed_required_types_deny_before_provider(setup, name, bad):
    service, provider, _ = setup
    data = dict(BASE)
    data[name] = bad
    assert_error(401, lambda: service.authenticate(token(data)))
    assert provider.posts == []


@pytest.mark.parametrize(
    "name", ["iss", "sub", "azp", "jti", "typ", "exp", "aud", "sid"]
)
def test_signed_omissions(setup, name):
    service, provider, _ = setup
    data = dict(BASE)
    del data[name]
    assert_error(401, lambda: service.authenticate(token(data)))
    assert not provider.posts


@pytest.mark.parametrize(
    "name",
    ["iss", "sub", "jti", "azp", "client_id", "typ", "token_type", "exp", "aud", "sid"],
)
@pytest.mark.parametrize("bad", [None, "", False, {}, []])
def test_malformed_active_provider_is_dependency_failure(setup, name, bad):
    service, provider, _ = setup
    provider.response[name] = bad
    assert_error(503, lambda: service.authenticate(token()))


@pytest.mark.parametrize(
    "name",
    ["iss", "sub", "jti", "azp", "client_id", "typ", "token_type", "exp", "aud", "sid"],
)
def test_active_provider_omissions_are_dependency_failures(setup, name):
    service, provider, _ = setup
    del provider.response[name]
    assert_error(503, lambda: service.authenticate(token()))


@pytest.mark.parametrize(
    "name,value",
    [
        ("iss", "https://other.test"),
        ("sub", "other-user"),
        ("jti", "other-jti"),
        ("azp", "client-q"),
        ("client_id", "client-q"),
        ("typ", "ID"),
        ("token_type", "ID"),
        ("exp", NOW + 299),
        ("aud", ["ingress-a"]),
        ("sid", "other-session"),
        ("scope", READ),
        ("nbf", 1),
    ],
)
def test_well_formed_provider_conflicts_are_denials(setup, name, value):
    service, provider, _ = setup
    provider.response[name] = value
    assert_error(401, lambda: service.authenticate(token()))


@pytest.mark.parametrize("marker", sorted(MARKERS))
@pytest.mark.parametrize("value", [None, "", False, 0, {}, "impersonator"])
@pytest.mark.parametrize("representation", ["signed", "introspected"])
def test_any_marker_occurrence_denies(setup, marker, value, representation):
    service, provider, _ = setup
    data = dict(BASE)
    if representation == "signed":
        data[marker] = value
    else:
        provider.response[marker] = value
    assert_error(401, lambda: service.authenticate(token(data)))
    if representation == "signed":
        assert not provider.posts


@pytest.mark.parametrize(
    "typ", ["ID", "Refresh", "Offline", "Serialized-ID", "Logout", "DPoP"]
)
def test_credential_classes(setup, typ):
    service, provider, _ = setup
    assert_error(401, lambda: service.authenticate(token(dict(BASE, typ=typ))))
    assert not provider.posts


@pytest.mark.parametrize("value", [-1, 2**63, True, "1700000300", 1700000300.0, 1.5])
@pytest.mark.parametrize("field", ["exp", "nbf"])
def test_numeric_date_representation_and_range(setup, value, field):
    service, provider, _ = setup
    assert_error(401, lambda: service.authenticate(token(dict(BASE, **{field: value}))))
    assert not provider.posts


def test_time_no_skew_and_expiry_during_introspection(setup):
    service, provider, clock = setup
    for fields in (
        {"exp": NOW},
        {"exp": NOW - 1},
        {"nbf": NOW + 1},
        {"nbf": NOW + 300},
    ):
        assert_error(
            401, lambda fields=fields: service.authenticate(token(dict(BASE, **fields)))
        )
    provider.post_hook = lambda url: clock.__setitem__(0, NOW + 300)
    assert_error(401, lambda: service.authenticate(token()))


def test_normalization_and_missing_scope(setup):
    service, provider, _ = setup
    provider.response.update(
        aud=["aux", "ingress-a"],
        session_state="session-1",
        scope=READ + "  openid " + READ,
    )
    del provider.response["nbf"]
    authority = service.authenticate(token())
    service.authorize(authority)
    for a in ("one", ["one"]):
        assert audiences(a) == {"one"}
    for data in (
        {"sid": "s"},
        {"session_state": "s"},
        {"sid": "s", "session_state": "s"},
    ):
        assert provider_session(data) == "s"
    for data in (
        {"sid": "s", "session_state": None},
        {"sid": "s", "session_state": "q"},
        {},
    ):
        with pytest.raises(ValueError):
            provider_session(data)
    for value in (["a", "a"], [], ["a", None], ""):
        with pytest.raises(ValueError):
            audiences(value)
    for value in (None, [], "a\tb", "a\nb", "ö", 'a"b', "a\\b"):
        with pytest.raises(ValueError):
            scopes(value)
    empty = dict(BASE)
    del empty["scope"]
    provider.response = introspection(empty)
    provider.response["scope"] = ""
    authority = service.authenticate(token(empty))
    assert assert_error(403, lambda: service.authorize(authority)).payload == {
        "error": "insufficient_scope",
        "scope": READ,
    }
    provider.response = introspection(dict(BASE, scope=READ + " offline_access"))
    assert_error(401, lambda: service.authenticate(token()))


@pytest.mark.parametrize(
    "response,status",
    [
        ({"active": False}, 401),
        ({}, 503),
        ({"active": None}, 503),
        ({"active": "true"}, 503),
        ({"active": 1}, 503),
        (b'{"active":true,"active":true}', 503),
        (b"[]", 503),
        (b"not JSON", 503),
        (RuntimeError("secret diagnostics"), 503),
    ],
)
def test_provider_response_classification(setup, response, status):
    service, provider, _ = setup
    provider.response = response
    error = assert_error(status, lambda: service.authenticate(token()))
    assert "diagnostics" not in str(error)


def test_signature_and_duplicate_json_fail_before_introspection(setup):
    service, provider, _ = setup
    wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert_error(401, lambda: service.authenticate(token(key=wrong)))
    parts = token().split(".")
    raw = json.dumps(BASE)[:-1] + ',"sub":"other"}'
    parts[1] = base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()
    signing_input = ".".join(parts[:2]).encode()
    signature = jwt.algorithms.RSAAlgorithm(jwt.algorithms.hashes.SHA256).sign(
        signing_input, KEY
    )
    parts[2] = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    # Prove the duplicate-member fixture has a valid signature independently.
    assert jwt.algorithms.RSAAlgorithm(jwt.algorithms.hashes.SHA256).verify(
        signing_input, KEY.public_key(), signature
    )
    assert_error(401, lambda: service.authenticate(".".join(parts)))
    assert not provider.posts


def test_fresh_introspection_and_request_contract(setup):
    service, provider, _ = setup
    original = token()
    authority = service.authenticate(original)
    for _ in range(3):
        service.authorize(authority)
    assert len(provider.posts) == 4
    for url, kwargs in provider.posts:
        assert url == CONFIG.issuer + "/protocol/openid-connect/token/introspect"
        assert kwargs["data"] == {"token": original, "token_type_hint": "access_token"}
        assert kwargs["auth"] == (CONFIG.exchange_client, CONFIG.exchange_secret)
        assert kwargs["allow_redirects"] is False
    provider.response = {"active": False}
    assert_error(401, lambda: service.authorize(authority))


def test_scope_inventory_and_direct_boundaries(setup):
    from onto_mcp.agent_contract import load_agent_contract

    assert len(EXPECTED_READ) == 28 and len(EXPECTED_WRITE) == 42
    assert not EXPECTED_READ & EXPECTED_WRITE
    assert READ_TOOLS == EXPECTED_READ
    assert WRITE_TOOLS == EXPECTED_WRITE
    assert RESOURCES == EXPECTED_RESOURCES
    assert READ_TOOLS | WRITE_TOOLS == set(load_agent_contract()["tool_contract"])
    service, provider, _ = setup
    for granted in ("", READ, WRITE, READ + " " + WRITE):
        data = dict(BASE, scope=granted)
        provider.response = introspection(data)
        authority = service.authenticate(token(data))
        context = current_authority.set(authority)
        try:
            for name in sorted(EXPECTED_READ | EXPECTED_WRITE | {"unclassified"}):
                called = []

                def handler(called=called):
                    called.append(True)

                handler.__name__ = name
                boundary = api_resources._wrap_tool_with_timeout(handler)
                allowed = READ in granted.split() and (
                    name in EXPECTED_READ
                    or name in EXPECTED_WRITE
                    and WRITE in granted.split()
                )
                if allowed:
                    boundary()
                    assert called == [True]
                else:
                    with pytest.raises(Exception, match="insufficient_scope"):
                        boundary()
                    assert not called
        finally:
            current_authority.reset(context)


@pytest.mark.parametrize("granted", ["", READ, WRITE, READ + " " + WRITE])
@pytest.mark.parametrize(
    "uri,helper,direct",
    [
        ("onto://spaces", "_get_user_spaces_data", "get_user_spaces"),
        ("onto://user/info", "_get_current_user_data", "get_user_info"),
    ],
)
@pytest.mark.parametrize("registered", [False, True], ids=["direct", "registered"])
def test_resource_scope_matrix(setup, granted, uri, helper, direct, registered):
    service, provider, _ = setup
    data = dict(BASE, scope=granted)
    provider.response = introspection(data)
    authority = service.authenticate(token(data))
    context = current_authority.set(authority)
    try:
        with patch.object(
            api_resources, helper, return_value={"inert": True}
        ) as handler:

            def invoke():
                if registered:
                    return asyncio.run(api_resources.mcp.read_resource(uri))
                return getattr(api_resources, direct)()

            if READ in granted.split():
                invoke()
                handler.assert_called_once_with()
            else:
                with pytest.raises(Exception, match="insufficient_scope"):
                    invoke()
                handler.assert_not_called()
    finally:
        current_authority.reset(context)


def inspect_represented_consent(policy, config):
    """Test-only formal inspection, never a deployed-provider/runtime validator."""
    findings = []
    if policy.get("bindings", {}).get("core_target") != "ONTO_OAUTH_CORE_AUDIENCE":
        findings.append("Core setting binding missing or contradictory")
    if policy.get("exchange", {}).get("target") != config.core_audience:
        findings.append("Exchange target differs from configured Core audience")
    expected = [(config.core_audience, False)] + [
        (client, True) for client in config.allowed_clients
    ]
    for client_id, required in expected:
        records = [
            c for c in policy.get("clients", []) if c.get("clientId") == client_id
        ]
        if len(records) != 1:
            findings.append(f"{client_id}: missing or ambiguous client binding")
        elif records[0].get("consentRequired") is not required:
            findings.append(
                f"{client_id}: consentRequired must explicitly be {required}"
            )
    return findings


@pytest.mark.parametrize("core", ["core-s", "changed-configured-core"])
@pytest.mark.parametrize(
    "fault",
    [
        "core_consent_enabled",
        "core_consent_omitted",
        "core_missing",
        "core_misbound",
        "external_p_consent_disabled",
        "external_q_consent_disabled",
        "core_setting_misbound",
        "exchange_target_misbound",
    ],
)
def test_represented_consent_inspection_detects_contradictions(core, fault):
    config = replace(CONFIG, core_audience=core)
    delivered = represented_policy(config)
    assert inspect_represented_consent(delivered, config) == []
    sample = copy.deepcopy(delivered)
    clients = {client["clientId"]: client for client in sample["clients"]}
    expected_client = core
    if fault == "core_consent_enabled":
        clients[core]["consentRequired"] = True
    elif fault == "core_consent_omitted":
        del clients[core]["consentRequired"]
    elif fault == "core_missing":
        sample["clients"].remove(clients[core])
    elif fault == "core_misbound":
        clients[core]["clientId"] = "unrelated-client"
    elif fault.startswith("external_"):
        expected_client = config.allowed_clients[
            0 if fault.startswith("external_p") else 1
        ]
        clients[expected_client]["consentRequired"] = False
    elif fault == "core_setting_misbound":
        sample["bindings"]["core_target"] = "ONTO_OAUTH_AUDIENCE"
        expected_client = "Core setting"
    else:
        sample["exchange"]["target"] = "unrelated-client"
        expected_client = "Exchange target"
    findings = inspect_represented_consent(sample, config)
    assert len(findings) == 1
    assert expected_client in findings[0]
    assert inspect_represented_consent(delivered, config) == []


def exchanged(data=None):
    claims = dict(
        BASE, azp=CONFIG.exchange_client, aud=[CONFIG.core_audience], **(data or {})
    )
    return {
        "access_token": token(claims),
        "token_type": "Bearer",
        "issued_token_type": ACCESS_TOKEN,
        "refresh_token": "unexpected-never-retained",
    }


def test_exchange_cache_and_final_revocation_prevents_send(setup):
    service, provider, _clock = setup
    provider.exchange = exchanged()
    authority = service.authenticate(token())
    first = service.exchange(authority)
    assert service.exchange(authority) == first
    exchange_posts = [(u, k) for u, k in provider.posts if u.endswith("/token")]
    assert len(exchange_posts) == 1
    assert exchange_posts[0][1]["data"] == {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": authority.original,
        "subject_token_type": ACCESS_TOKEN,
        "requested_token_type": ACCESS_TOKEN,
        "audience": CONFIG.core_audience,
    }
    assert "unexpected-never-retained" not in repr(service._cache)
    context = current_authority.set(authority)
    try:
        provider.response = {"active": False}
        with (
            patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
            patch.object(api_resources.requests, "request") as send,
        ):
            assert_error(
                401,
                lambda: api_resources._request_with_canonical_auth(
                    "POST", "https://core.test/entity"
                ),
            )
            send.assert_not_called()
    finally:
        current_authority.reset(context)
    assert not service._cache


@pytest.mark.parametrize(
    "change",
    [
        {"sub": "other"},
        {"iss": "https://other.test"},
        {"azp": "wrong"},
        {"sid": "other-session"},
        {"aud": ["wrong"]},
        {"exp": NOW},
    ],
)
def test_bad_exchange_cannot_supply_core_credential(setup, change):
    service, provider, _ = setup
    data = dict(BASE, azp=CONFIG.exchange_client, aud=[CONFIG.core_audience])
    data.update(change)
    provider.exchange = {
        "access_token": token(data),
        "token_type": "Bearer",
        "issued_token_type": ACCESS_TOKEN,
    }
    authority = service.authenticate(token())
    assert_error(503, lambda: service.exchange(authority))
    assert not service._cache


def test_delegated_headers_origin_and_cancellation(setup):
    service, provider, _ = setup
    provider.exchange = exchanged()
    authority = service.authenticate(token())
    context = current_authority.set(authority)
    try:
        with (
            patch.object(api_resources, "ONTO_API_BASE", "https://core.test/api"),
            patch.object(api_resources.requests, "request") as send,
        ):
            api_resources._request_with_canonical_auth(
                "POST",
                "https://core.test/api/entity",
                headers={
                    "X-API-Key": "wrong",
                    "X-Onto-Api-Key": "wrong",
                    "Authorization": "caller",
                },
            )
            headers = send.call_args.kwargs["headers"]
            assert set(headers) == {"Authorization", "Content-Type", "Accept"}
            assert headers["Authorization"].startswith("Bearer ")
            assert send.call_args.kwargs["allow_redirects"] is False
            send.reset_mock()
            assert_error(
                503,
                lambda: api_resources._request_with_canonical_auth(
                    "POST", "https://evil.test/entity"
                ),
            )
            send.assert_not_called()
            authority.cancelled.set()
            assert_error(
                401,
                lambda: api_resources._request_with_canonical_auth(
                    "POST", "https://core.test/api/entity"
                ),
            )
            send.assert_not_called()
    finally:
        current_authority.reset(context)


@pytest.mark.parametrize(
    "headers",
    [
        [(b"authorization", b"Bearer")],
        [(b"authorization", b"Bearer a,b")],
        [(b"authorization", b"Bearer a"), (b"authorization", b"Bearer a")],
        [(b"authorization", b"Bearer a"), (b"x-api-key", b"key")],
        [(b"x-api-key", b"")],
        [(b"x-api-key", b"k"), (b"x-api-key", b"k")],
    ],
)
def test_malformed_transport(headers):
    with pytest.raises(InvalidHttpCredentials):
        classify_http_credentials(headers)


def test_complete_connection_tuple_and_cache_lifetime(setup):
    import hashlib

    service, provider, clock = setup
    original = service.authenticate(token())
    expected = hashlib.sha256(
        json.dumps(
            [CONFIG.issuer, "user-u", "client-p", "session-1"],
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    assert original.claims.connection_key == expected
    for field, value in [
        ("issuer", "https://other.test"),
        ("subject", "user-v"),
        ("client", "client-q"),
        ("session", "other"),
    ]:
        assert replace(original.claims, **{field: value}).connection_key != expected
    assert replace(original.claims, jti="new-jti").connection_key == expected
    provider.exchange = exchanged({"exp": NOW + 100})
    service.exchange(original)
    assert service._cache[expected][1] == NOW + 100
    clock[0] += 100
    provider.exchange = exchanged({"exp": NOW + 250})
    service.exchange(original)
    assert len([u for u, _ in provider.posts if u.endswith("/token")]) == 2
    assert service._cache[expected][1] == NOW + 250


def test_final_authorization_after_exchange_can_deny(setup):
    service, provider, _ = setup
    provider.exchange = exchanged()
    authority = service.authenticate(token())

    def hook(url):
        if url.endswith("/token"):
            provider.response = {"active": False}

    provider.post_hook = hook
    context = current_authority.set(authority)
    try:
        with (
            patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
            patch.object(api_resources.requests, "request") as send,
        ):
            assert_error(
                401,
                lambda: api_resources._request_with_canonical_auth(
                    "POST", "https://core.test/entity"
                ),
            )
            send.assert_not_called()
    finally:
        current_authority.reset(context)


def test_concurrent_users_and_clients_keep_delegation_and_resource_authority_separate():
    import threading
    from concurrent.futures import ThreadPoolExecutor

    class RoutingProvider(Provider):
        def post(self, url, **kwargs):
            original = kwargs["data"].get("token") or kwargs["data"].get(
                "subject_token"
            )
            data = jwt.decode(original, options={"verify_signature": False})
            if url.endswith("/introspect"):
                result = introspection(data)
            else:
                delegated = dict(
                    data, azp=CONFIG.exchange_client, aud=[CONFIG.core_audience]
                )
                result = {
                    "access_token": token(delegated),
                    "token_type": "Bearer",
                    "issued_token_type": ACCESS_TOKEN,
                }
            return SimpleNamespace(status_code=200, content=json.dumps(result).encode())

    service = OAuthService(CONFIG, http=RoutingProvider(), clock=lambda: NOW)
    start = threading.Barrier(3)
    sent = []

    def send(method, url, **kwargs):
        authority = current_authority.get()
        claim = jwt.decode(
            kwargs["headers"]["Authorization"][7:], options={"verify_signature": False}
        )
        sent.append(
            (
                authority.claims.subject,
                authority.claims.client,
                claim["sub"],
                claim["azp"],
            )
        )
        return SimpleNamespace(status_code=200)

    def run(subject, client):
        data = dict(BASE, sub=subject, azp=client)
        authority = service.authenticate(token(data))
        context = current_authority.set(authority)
        try:
            start.wait(timeout=3)
            # Exercise the resource guard with an inert projection, then the
            # common final outbound boundary used by all specialized helpers.
            result = api_resources.get_user_spaces()
            assert result == [{"id": subject, "client": client}]
            api_resources._request_with_canonical_auth("GET", "https://core.test/user")
            return authority.claims.connection_key
        finally:
            current_authority.reset(context)

    def projection():
        c = current_authority.get().claims
        return [{"id": c.subject, "client": c.client}]

    with (
        patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
        patch.object(api_resources.requests, "request", side_effect=send),
        patch.object(api_resources, "_get_user_spaces_data", side_effect=projection),
        ThreadPoolExecutor(3) as executor,
    ):
        pending = [
            executor.submit(run, *pair)
            for pair in [
                ("user-u", "client-p"),
                ("user-u", "client-q"),
                ("user-v", "client-p"),
            ]
        ]
        keys = [future.result(timeout=5) for future in pending]
    assert len(set(keys)) == 3 and set(keys) == set(service._cache)
    assert sorted(sent) == sorted(
        [
            (u, c, u, CONFIG.exchange_client)
            for u, c in [
                ("user-u", "client-p"),
                ("user-u", "client-q"),
                ("user-v", "client-p"),
            ]
        ]
    )


def test_delegated_credential_redaction_survives_cache_eviction(setup):
    service, provider, _ = setup
    provider.exchange = exchanged()
    authority = service.authenticate(token())
    context = current_authority.set(authority)
    try:
        with (
            patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
            patch.object(api_resources.requests, "request"),
        ):
            api_resources._request_with_canonical_auth("GET", "https://core.test/user")
        delegated = authority.delegated_tokens[0]
        service.evict(authority.claims.connection_key)
        assert delegated not in api_resources._credential_safe_text(
            "upstream " + delegated
        )
        assert delegated not in repr(authority)
    finally:
        current_authority.reset(context)


def test_expiry_during_state_wait_prevents_final_send(setup):
    service, provider, clock = setup
    provider.exchange = exchanged()
    authority = service.authenticate(token())

    class SlowStore:
        def require(self, *_):
            clock[0] = NOW + 300

    authority.state_store = SlowStore()
    authority.session_id = "synthetic-session"
    context = current_authority.set(authority)
    try:
        with (
            patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
            patch.object(api_resources.requests, "request") as send,
        ):
            assert_error(
                401,
                lambda: api_resources._request_with_canonical_auth(
                    "POST", "https://core.test/entity"
                ),
            )
            send.assert_not_called()
    finally:
        current_authority.reset(context)


def test_inactive_denial_is_not_overridden_by_cleanup_failure(setup):
    service, provider, _ = setup
    authority = service.authenticate(token())
    provider.response = {"active": False}

    def unavailable(_):
        raise OAuthError("dependency_unavailable", 503)

    service.invalidate_connection = unavailable
    assert_error(401, lambda: service.authorize(authority))


@pytest.mark.parametrize("wait", ["storage", "introspection"])
@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("bound", ["token", "cache"])
def test_selected_delegated_deadline_rechecked_before_mutation(
    setup, wait, cached, bound
):
    service, provider, clock = setup
    # Original authorization remains valid throughout the delegated expiry wait.
    original = dict(BASE, exp=NOW + 1000)
    provider.response = dict(
        original, active=True, client_id=CONFIG.allowed_clients[0], token_type="Bearer"
    )
    authority = service.authenticate(token(original))
    provider.exchange = exchanged({"exp": NOW + (10 if bound == "token" else 900)})
    deadline = NOW + (10 if bound == "token" else 300)
    if cached:
        service.exchange(authority)
    calls = []

    class SlowStore:
        def require(self, *_):
            calls.append("storage")
            if wait == "storage":
                clock[0] = deadline

    authority.state_store = SlowStore()
    authority.session_id = "synthetic-session"

    def introspection_wait(url):
        if url.endswith("introspect"):
            calls.append("introspection")
            if wait == "introspection" and "storage" in calls:
                clock[0] = deadline

    provider.post_hook = introspection_wait
    context = current_authority.set(authority)
    try:
        with (
            patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
            patch.object(api_resources.requests, "request") as send,
        ):
            assert_error(
                503,
                lambda: api_resources._request_with_canonical_auth(
                    "POST", "https://core.test/entity", json={"name": "mutation"}
                ),
            )
            send.assert_not_called()
        assert calls == ["introspection", "storage", "introspection"]
        assert sum(url.endswith("/token") for url, _ in provider.posts) == 1
    finally:
        current_authority.reset(context)


@pytest.mark.parametrize("status", [400, 401, 403, 500, 503])
def test_non_200_introspection_is_dependency_failure(setup, status):
    service, provider, _ = setup
    provider.status = status
    error = assert_error(503, lambda: service.authenticate(token()))
    assert error.payload == {"error": "dependency_unavailable"}
    assert len(provider.posts) == 1
    assert not service._cache


@pytest.mark.parametrize("field", ["iss", "sub", "azp", "jti"])
@pytest.mark.parametrize("value", ["   ", "\t", "user\x00u", "user\nu"])
@pytest.mark.parametrize("boundary", ["signed", "provider"])
def test_identity_whitespace_controls_at_each_boundary(setup, field, value, boundary):
    service, provider, _ = setup
    claims = dict(BASE)
    if boundary == "signed":
        claims[field] = value
    else:
        provider.response[field] = value
    assert_error(
        401 if boundary == "signed" else 503,
        lambda: service.authenticate(token(claims)),
    )
    assert len(provider.posts) == (0 if boundary == "signed" else 1)


@pytest.mark.parametrize("alias", ["sid", "session_state"])
@pytest.mark.parametrize("value", [None, "", "  ", False, 1, {}, "s\x00"])
@pytest.mark.parametrize("boundary", ["signed", "provider"])
def test_malformed_present_session_alias_with_other_valid_alias(
    setup, alias, value, boundary
):
    service, provider, _ = setup
    claims = dict(BASE, session_state="session-1")
    provider.response = introspection(claims)
    (claims if boundary == "signed" else provider.response)[alias] = value
    assert_error(
        401 if boundary == "signed" else 503,
        lambda: service.authenticate(token(claims)),
    )
    assert len(provider.posts) == (0 if boundary == "signed" else 1)


@pytest.mark.parametrize(
    "fault", ["signature", "empty", "token_type", "issued_token_type"]
)
def test_exchange_response_faults_block_actual_outbound_boundary(setup, fault):
    service, provider, _ = setup
    provider.exchange = exchanged()
    if fault == "signature":
        wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        claims = dict(BASE, azp=CONFIG.exchange_client, aud=[CONFIG.core_audience])
        provider.exchange["access_token"] = token(claims, key=wrong)
    else:
        field, value = {
            "empty": ("access_token", ""),
            "token_type": ("token_type", "DPoP"),
            "issued_token_type": ("issued_token_type", "urn:wrong"),
        }[fault]
        provider.exchange[field] = value
    authority = service.authenticate(token())
    context = current_authority.set(authority)
    try:
        with (
            patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
            patch.object(api_resources.requests, "request") as send,
        ):
            error = assert_error(
                503,
                lambda: api_resources._request_with_canonical_auth(
                    "POST", "https://core.test/entity"
                ),
            )
            assert error.payload == {"error": "dependency_unavailable"}
            send.assert_not_called()
            assert not service._cache
    finally:
        current_authority.reset(context)


@pytest.mark.parametrize("prior_grant", [False, True])
@pytest.mark.parametrize("acknowledged", [False, True])
@pytest.mark.parametrize("active", [False, True])
def test_revocation_status_and_grant_history_do_not_authorize_dispatch(
    setup, prior_grant, acknowledged, active
):
    service, provider, _ = setup
    provider.exchange = exchanged()
    authority = service.authenticate(token())
    service.exchange(authority)  # retain an otherwise usable cached credential
    # These independent synthetic provider-history facts do not enter MCP trust.
    history = {
        "prior_grant": prior_grant,
        "revoke_http_status": 200 if acknowledged else 503,
    }
    assert history["prior_grant"] is prior_grant
    assert (history["revoke_http_status"] == 200) is acknowledged
    provider.response = introspection() if active else {"active": False}
    before = len(provider.posts)
    context = current_authority.set(authority)
    try:
        with (
            patch.object(api_resources, "ONTO_API_BASE", "https://core.test"),
            patch.object(api_resources.requests, "request") as send,
        ):
            invoke = lambda: api_resources._request_with_canonical_auth(
                "GET", "https://core.test/user"
            )
            if active:
                invoke()
                send.assert_called_once()
            else:
                assert_error(401, invoke)
                send.assert_not_called()
            assert (
                len(provider.posts) > before
            )  # fresh token observation, not acknowledgement
    finally:
        current_authority.reset(context)
