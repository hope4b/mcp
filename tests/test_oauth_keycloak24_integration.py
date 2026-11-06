"""Opt-in regression for an isolated Keycloak 24.0.1 fixture, never live PREPROD.

The disposable realm/client/user are imported from the documented fixture. HTTP
and a password grant are test-only shortcuts; JWT signatures are verified with
real fixture JWKS. No production config or identities are modified.
"""

import os

import jwt
import pytest
import requests

from onto_mcp.oauth import OAuthConfig, OAuthService, RequestAuthority

pytestmark = pytest.mark.integration


def test_real_keycloak24_exchange_without_issued_type():
    base = os.environ.get("MCP_TEST_KEYCLOAK24_URL")
    if not base:
        pytest.skip("Disposable Keycloak 24 fixture not configured")
    assert (
        base
        == "http://mcp-keycloak24-response-fixture:8080/realms/mcp-response-fixture"
    )
    auth = ("fixture-client", "disposable-fixture-secret")
    response = requests.post(
        base + "/protocol/openid-connect/token",
        auth=auth,
        data={
            "grant_type": "password",
            "username": "fixture-user",
            "password": "disposable-fixture-password",
        },
        timeout=10,
    )
    assert response.status_code == 200
    original = response.json()["access_token"]
    jwks = requests.get(base + "/protocol/openid-connect/certs", timeout=5)
    jwks.raise_for_status()
    keys = jwt.PyJWKSet.from_dict(jwks.json())

    def verify(encoded):
        header = jwt.get_unverified_header(encoded)
        key = next(k.key for k in keys.keys if k.key_id == header["kid"])
        jwt.decode(
            encoded,
            key,
            algorithms=["RS256"],
            issuer=base,
            options={"verify_aud": False},
        )

    config = OAuthConfig(
        enabled=True,
        issuer=base,
        resource="https://fixture.invalid/mcp",
        audience="fixture-client",
        allowed_clients=("fixture-client",),
        exchange_client=auth[0],
        exchange_secret=auth[1],
        core_audience="fixture-client",
    )
    seen = []

    class Provider:
        def post(self, url, **kwargs):
            result = requests.post(url, **kwargs)
            if result.status_code == 200 and url.endswith("/token"):
                # Retain only field names, never credentials or token content.
                seen.append(set(result.json()))
            return result

    service = OAuthService(config, http=Provider(), verify=verify)
    claims = service.signed(original, ingress=False)
    delegated, deadline = service.exchange(RequestAuthority(service, original, claims))
    actual = service.signed(delegated, ingress=False)
    assert seen and "issued_token_type" not in seen[0]
    assert actual.subject == claims.subject and actual.session == claims.session
    assert actual.client == config.exchange_client
    assert config.core_audience in actual.audience
    assert deadline <= min(actual.expires, claims.expires)
