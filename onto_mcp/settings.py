from __future__ import annotations

"""Central configuration for Onto MCP Server.
Environment variables are provided by MCP client configuration (mcp.json).

Having a single place for configuration simplifies maintenance and eliminates 
scattered hard-coded values.
"""

import os


def _split_env_list(raw: str | None) -> list[str]:
    """Parse whitespace- or comma-delimited environment values into a list."""
    if not raw:
        return []
    items = []
    for chunk in raw.replace(",", " ").split():
        value = chunk.strip()
        if value:
            items.append(value)
    return items


# ---------------------------------------------------------------------------
# Keycloak configuration
# ---------------------------------------------------------------------------

KEYCLOAK_BASE_URL: str = os.getenv("KEYCLOAK_BASE_URL", "").rstrip("/") or ""
KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "").strip()
KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "").strip()
KEYCLOAK_CLIENT_SECRET: str = os.getenv("KEYCLOAK_CLIENT_SECRET", "").strip()

_realm_root = (
    f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}"
    if KEYCLOAK_BASE_URL and KEYCLOAK_REALM
    else None
)

KEYCLOAK_ISSUER: str | None = os.getenv("KEYCLOAK_ISSUER") or _realm_root
KEYCLOAK_AUTH_ENDPOINT: str | None = os.getenv("KEYCLOAK_AUTH_ENDPOINT") or (
    f"{_realm_root}/protocol/openid-connect/auth" if _realm_root else None
)
KEYCLOAK_TOKEN_ENDPOINT: str | None = os.getenv("KEYCLOAK_TOKEN_ENDPOINT") or (
    f"{_realm_root}/protocol/openid-connect/token" if _realm_root else None
)
KEYCLOAK_JWKS_URI: str | None = os.getenv("KEYCLOAK_JWKS_URI") or (
    f"{_realm_root}/protocol/openid-connect/certs" if _realm_root else None
)
KEYCLOAK_REVOCATION_ENDPOINT: str | None = os.getenv(
    "KEYCLOAK_REVOCATION_ENDPOINT"
) or (f"{_realm_root}/protocol/openid-connect/revoke" if _realm_root else None)
KEYCLOAK_USERINFO_ENDPOINT: str | None = os.getenv("KEYCLOAK_USERINFO_ENDPOINT") or (
    f"{_realm_root}/protocol/openid-connect/userinfo" if _realm_root else None
)
KEYCLOAK_SCOPES: list[str] = _split_env_list(
    os.getenv(
        "KEYCLOAK_SCOPES",
        "email profile",
    )
)

# ---------------------------------------------------------------------------
# OAuth proxy configuration
# ---------------------------------------------------------------------------

MCP_PUBLIC_BASE_URL: str = os.getenv("MCP_PUBLIC_BASE_URL", "").rstrip("/")
OAUTH_REDIRECT_PATH: str = os.getenv("OAUTH_REDIRECT_PATH", "/auth/callback")
OAUTH_ALLOWED_REDIRECT_URIS: list[str] = _split_env_list(
    os.getenv("OAUTH_ALLOWED_REDIRECT_URIS")
)

# Ensure redirect path always begins with a single slash for downstream joins
if OAUTH_REDIRECT_PATH:
    OAUTH_REDIRECT_PATH = f"/{OAUTH_REDIRECT_PATH.lstrip('/')}"

# ---------------------------------------------------------------------------
# Onto API configuration
# ---------------------------------------------------------------------------

ONTO_API_BASE: str = os.getenv("ONTO_API_BASE", "").rstrip("/")
SESSION_STATE_API_BASE: str = os.getenv("SESSION_STATE_API_BASE", ONTO_API_BASE)
SESSION_STATE_API_KEY: str = os.getenv("SESSION_STATE_API_KEY", "").strip()


# ---------------------------------------------------------------------------
# MCP server runtime configuration
# ---------------------------------------------------------------------------

MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio")  # Keep default for transport
PORT: int = int(os.getenv("PORT", "8080"))  # Keep default for port

# Convenience flag
IS_HTTP_TRANSPORT: bool = MCP_TRANSPORT == "http"

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_required_vars = [
    ("KEYCLOAK_BASE_URL", KEYCLOAK_BASE_URL),
    ("KEYCLOAK_REALM", KEYCLOAK_REALM),
    ("KEYCLOAK_CLIENT_ID", KEYCLOAK_CLIENT_ID),
    ("ONTO_API_BASE", ONTO_API_BASE),
]

_missing = [name for name, value in _required_vars if not value]

if IS_HTTP_TRANSPORT:
    _http_required = [
        ("KEYCLOAK_AUTH_ENDPOINT", KEYCLOAK_AUTH_ENDPOINT),
        ("KEYCLOAK_TOKEN_ENDPOINT", KEYCLOAK_TOKEN_ENDPOINT),
        ("KEYCLOAK_JWKS_URI", KEYCLOAK_JWKS_URI),
        ("KEYCLOAK_ISSUER", KEYCLOAK_ISSUER),
        ("MCP_PUBLIC_BASE_URL", MCP_PUBLIC_BASE_URL),
        ("SESSION_STATE_API_KEY", SESSION_STATE_API_KEY),
    ]
    _missing.extend(name for name, value in _http_required if not value)

if _missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(sorted(set(_missing)))}. "
        f"Please set them in your mcp.json configuration."
    )
