from __future__ import annotations

import os, sys

# Set required environment variables for testing
os.environ.setdefault("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
os.environ.setdefault("KEYCLOAK_REALM", "onto")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "frontend-prod")
os.environ.setdefault("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest

from onto_mcp.resources import get_user_spaces, login_via_token


@pytest.mark.unit
def test_spaces_returns_list(monkeypatch):
    login_via_token("fake-token")

    import requests

    monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResp())

    spaces = get_user_spaces()
    assert isinstance(spaces, list)


class FakeResp:
    def raise_for_status(self) -> None:
        ...

    def json(self) -> dict:
        return {
            "userRealmsRoles": [
                {"realmId": "123", "realmName": "Demo", "roleName": "admin"}
            ]
        }
