from __future__ import annotations

import datetime

import os  # Still used for sys.path adjustments in tests; keep for now

import time

import uuid

from typing import Any, Dict, Optional, TYPE_CHECKING

import requests

from fastmcp import FastMCP

from fastmcp.server.context import Context

from .auth import get_token, set_token

from .keycloak_auth import KeycloakAuth

from .session_state_client import (
    SessionStateError,
    get_session_state,
    is_session_state_configured,
    merge_session_state,
)

from .settings import (
    IS_HTTP_TRANSPORT,
    KEYCLOAK_AUTH_ENDPOINT,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
    KEYCLOAK_ISSUER,
    KEYCLOAK_JWKS_URI,
    KEYCLOAK_REVOCATION_ENDPOINT,
    KEYCLOAK_SCOPES,
    KEYCLOAK_TOKEN_ENDPOINT,
    KEYCLOAK_USERINFO_ENDPOINT,
    MCP_PUBLIC_BASE_URL,
    OAUTH_ALLOWED_REDIRECT_URIS,
    OAUTH_REDIRECT_PATH,
    ONTO_API_BASE,
)

from .utils import safe_print

if TYPE_CHECKING:

    from fastmcp.server.auth import AccessToken as MCPAccessToken


def _build_oauth_provider():

    if not IS_HTTP_TRANSPORT:

        return None

    try:

        from fastmcp.server.auth import OAuthProxy

        from fastmcp.server.auth.providers.jwt import JWTVerifier

    except ImportError as exc:  # pragma: no cover - defensive guard

        raise RuntimeError(
            "FastMCP OAuth components are not available in the current environment."
        ) from exc

    scopes = KEYCLOAK_SCOPES or ["openid", "profile", "email"]

    allowed_redirects = OAUTH_ALLOWED_REDIRECT_URIS or None

    verifier = JWTVerifier(
        jwks_uri=KEYCLOAK_JWKS_URI,
        issuer=KEYCLOAK_ISSUER,
        audience=KEYCLOAK_CLIENT_ID,
        required_scopes=scopes,
        base_url=MCP_PUBLIC_BASE_URL,
    )

    return OAuthProxy(
        upstream_authorization_endpoint=KEYCLOAK_AUTH_ENDPOINT,
        upstream_token_endpoint=KEYCLOAK_TOKEN_ENDPOINT,
        upstream_client_id=KEYCLOAK_CLIENT_ID,
        upstream_client_secret=KEYCLOAK_CLIENT_SECRET,
        upstream_revocation_endpoint=KEYCLOAK_REVOCATION_ENDPOINT,
        token_verifier=verifier,
        base_url=MCP_PUBLIC_BASE_URL,
        redirect_path=OAUTH_REDIRECT_PATH,
        allowed_client_redirect_uris=allowed_redirects,
        valid_scopes=scopes,
    )


AUTH_PROVIDER = _build_oauth_provider()

mcp = FastMCP(name="Onto MCP Server", auth=AUTH_PROVIDER)

# ONTO_API_BASE now comes from settings (with env/default handling)

# Global Keycloak auth instance

keycloak_auth = KeycloakAuth()


def _legacy_token_storage_enabled() -> bool:

    storage = getattr(keycloak_auth, "token_storage", None)

    return bool(getattr(storage, "supports_legacy_token", True))


def _get_fastmcp_access_token() -> Optional["MCPAccessToken"]:

    if not IS_HTTP_TRANSPORT:

        return None

    try:

        from fastmcp.server.dependencies import (
            get_access_token as get_context_access_token,
        )

    except ImportError:

        return None

    try:

        return get_context_access_token()

    except RuntimeError:

        return None


def _cache_access_token_for_legacy(access_token: "MCPAccessToken") -> None:

    if not keycloak_auth:

        return

    token_value = getattr(access_token, "token", None)

    if not token_value:

        return

    token_data: Dict[str, Any] = {"access_token": token_value, "token_type": "Bearer"}

    expires_at = getattr(access_token, "expires_at", None)

    if isinstance(expires_at, (int, float)):

        token_data["expires_in"] = max(0, int(expires_at - time.time()))

    claims = getattr(access_token, "claims", None)

    if isinstance(claims, dict):

        refresh_token = claims.get("refresh_token")

        if refresh_token:

            token_data["refresh_token"] = refresh_token

    try:

        keycloak_auth.token_storage.store_tokens(token_data)

    except Exception:

        pass


def _fetch_userinfo(access_token: str) -> Dict[str, Any]:

    if not KEYCLOAK_USERINFO_ENDPOINT:

        return {}

    try:

        response = requests.get(
            KEYCLOAK_USERINFO_ENDPOINT,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict):

            return data

    except Exception as exc:

        safe_print(f"[auth] Failed to fetch userinfo: {exc}")

    return {}


def _format_http_auth_status() -> str:

    access_token = _get_fastmcp_access_token()

    if not access_token or not getattr(access_token, "token", None):

        return (
            "❌ **Not authenticated**\n"
            "🔁 OAuth login is managed by your MCP client. Trigger the authorization flow from the client UI."
        )

    _cache_access_token_for_legacy(access_token)

    user_info = _fetch_userinfo(access_token.token)

    lines = ["✅ **Authenticated via OAuth**"]

    username = user_info.get("preferred_username") if user_info else None

    email = user_info.get("email") if user_info else None

    if username or email:

        if username and email and username != email:

            lines.append(f"👤 {username} ({email})")

        else:

            lines.append(f"👤 {username or email}")

    elif getattr(access_token, "resource_owner", None):

        lines.append(f"👤 {access_token.resource_owner}")

    client_id = getattr(access_token, "client_id", None) or KEYCLOAK_CLIENT_ID

    lines.append(f"🔑 Client: {client_id}")

    scopes = list(getattr(access_token, "scopes", []) or [])

    if scopes:

        lines.append(f"🔒 Scopes: {', '.join(scopes)}")

    expires_at = getattr(access_token, "expires_at", None)

    if isinstance(expires_at, (int, float)):

        expires_dt = datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)

        lines.append(f"⌛ Expires: {expires_dt.isoformat()}")

    else:

        lines.append("⌛ Expires: not provided")

    lines.append("🔁 Use your MCP client to re-authorize or sign out.")

    return "\n".join(lines)


def _format_http_session_info() -> str:

    access_token = _get_fastmcp_access_token()

    if not access_token or not getattr(access_token, "token", None):

        return (
            "❌ **No active OAuth session**\n"
            "🔁 Launch the OAuth sign-in flow from your MCP client to authenticate."
        )

    _cache_access_token_for_legacy(access_token)

    user_info = _fetch_userinfo(access_token.token)

    lines = ["ℹ️ **OAuth Session Details**"]

    client_id = getattr(access_token, "client_id", None) or KEYCLOAK_CLIENT_ID

    lines.append(f"Client ID: {client_id}")

    scopes = list(getattr(access_token, "scopes", []) or [])

    if scopes:

        lines.append(f"Scopes: {', '.join(scopes)}")

    expires_at = getattr(access_token, "expires_at", None)

    if isinstance(expires_at, (int, float)):

        expires_dt = datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)

        lines.append(f"Expires: {expires_dt.isoformat()}")

    issued_at = getattr(access_token, "issued_at", None)

    if isinstance(issued_at, (int, float)):

        issued_dt = datetime.datetime.fromtimestamp(issued_at, datetime.timezone.utc)

        lines.append(f"Issued: {issued_dt.isoformat()}")

    if user_info:

        lines.append("")

        lines.append("**User Information:**")

        for key in ("preferred_username", "email", "name", "sub"):

            if key in user_info:

                lines.append(f"- {key}: {user_info[key]}")

    lines.append("Use your MCP client to refresh, disconnect, or switch accounts.")

    return "\n".join(lines)


@mcp.tool
def login_with_credentials(username: str, password: str) -> str:
    """Authenticate with Keycloak using username and password.

    Disabled when the server runs in HTTP transport (OAuth) mode; the MCP client

    drives the browser-based login flow in that scenario.

    """

    if IS_HTTP_TRANSPORT:

        return (
            "OAuth authentication is managed by your MCP client in HTTP mode. "
            "Trigger the sign-in flow from the client UI to connect this server."
        )

    try:

        if keycloak_auth.authenticate_with_password(username, password):

            access_token = keycloak_auth.get_valid_access_token()

            if access_token:

                if _legacy_token_storage_enabled():

                    set_token(access_token)

                user_info = keycloak_auth.get_user_info()

                if user_info:

                    email = user_info.get("email", "Unknown")

                    return f"✅ Successfully authenticated as {email}. Session saved persistently."

                return "✅ Authentication successful. Session saved persistently."

            return "❌ Authentication succeeded but failed to get access token"

        return "❌ Authentication failed - invalid credentials"

    except Exception as exc:

        return f"❌ Authentication error: {exc}"


@mcp.tool
def refresh_token() -> str:
    """Refresh the current access token.

    This remains available for stdio usage; in HTTP/OAuth mode tokens are

    refreshed automatically by the MCP runtime.

    """

    if IS_HTTP_TRANSPORT:

        return (
            "OAuth-managed tokens refresh automatically while this server runs in HTTP mode. "
            "If the session expires, re-run the sign-in flow from your MCP client."
        )

    try:

        if keycloak_auth.refresh_access_token():

            access_token = keycloak_auth.get_valid_access_token()

            if access_token:

                if _legacy_token_storage_enabled():

                    set_token(access_token)

                return "✅ Token refreshed successfully"

            return "❌ Token refresh succeeded but failed to get new access token"

        return "❌ Failed to refresh token - may need to re-authenticate"

    except Exception as exc:

        return f"❌ Token refresh error: {exc}"


@mcp.tool
def get_auth_status() -> str:
    """Get current authentication status with helpful guidance.

    Returns:

        Authentication status information

    """

    if IS_HTTP_TRANSPORT:

        return _format_http_auth_status()

    try:

        is_authenticated = keycloak_auth.is_authenticated()

        status = keycloak_auth.token_storage.get_session_status()

        if is_authenticated:

            user_info = keycloak_auth.get_user_info()

            if user_info:

                username = user_info.get("preferred_username", "Unknown")

                email = user_info.get("email", "Unknown")

                result = f"✅ **Authenticated** as: {username} ({email})\n"

                result += f"ℹ️ Status: {status}"

                token_info = keycloak_auth.token_storage.get_token_info()

                if token_info.get("access_token_expired"):

                    result += "\n⌛ Access token expired but refresh available"

                else:

                    result += "\n🟢 Access token valid"

                return result

            return f"✅ Authenticated (token valid)\nℹ️ Status: {status}"

        return (
            "❌ **Not authenticated**\n"
            f"ℹ️ Status: {status}\n\n"
            "👉 **To authenticate, use:**\n"
            '• `login_with_credentials("email", "password")` - Username/password authentication'
        )

    except Exception as exc:

        return f"❌ Error checking auth status: {exc}"


@mcp.tool
def get_session_info() -> str:
    """Get detailed session information including token status."""
    if IS_HTTP_TRANSPORT:
        return _format_http_session_info()

    try:
        session_info = keycloak_auth.get_session_info()

        lines = [
            "Detailed Session Information",
            "",
            f"Status: {session_info.get('session_status', 'Unknown')}",
            "",
            "Token Information:",
            f"- Has Access Token: {'yes' if session_info.get('has_access_token') else 'no'}",
            f"- Has Refresh Token: {'yes' if session_info.get('has_refresh_token') else 'no'}",
            f"- Access Token Expired: {'yes' if session_info.get('access_token_expired') else 'no'}",
            f"- Refresh Token Expired: {'yes' if session_info.get('refresh_token_expired') else 'no'}",
        ]

        if session_info.get("last_updated"):
            import datetime

            last_updated = datetime.datetime.fromtimestamp(session_info["last_updated"])
            lines.append(
                f"- Last Updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        user = session_info.get("user")
        if isinstance(user, dict):
            lines.extend(
                [
                    "",
                    "User Information:",
                    f"- Email: {user.get('email', 'Unknown')}",
                    f"- Name: {user.get('name', 'Unknown')}",
                    f"- Username: {user.get('username', 'Unknown')}",
                ]
            )

        storage_path = keycloak_auth.token_storage.token_file
        lines.append(f"Storage: {storage_path}")

        return "\n".join(lines)
    except Exception as exc:
        return f"Error getting session info: {exc}"


@mcp.tool
def logout() -> str:
    """Logout and clear all authentication tokens."""

    if IS_HTTP_TRANSPORT:

        return (
            "OAuth sessions are managed by your MCP client in HTTP mode. "
            "Use the client UI to disconnect or switch accounts."
        )

    try:

        success = keycloak_auth.logout()

        if _legacy_token_storage_enabled():

            try:

                set_token("")

            except Exception:

                pass

        if success:

            return (
                "Logged out successfully. All tokens cleared from persistent storage."
            )

        return "Logged out locally (remote logout may have failed). All local tokens cleared."

    except Exception as exc:

        return f"Logout error: {exc}"


@mcp.tool
def saveOntoAIThreadID(thread_external_id: str, ctx: Context) -> Dict[str, Any]:
    """Persist the threadExternalId for the active MCP session."""

    context_id = ctx.session_id

    thread_id = (thread_external_id or "").strip()

    if not thread_id:

        return {
            "contextId": context_id,
            "threadExternalId": None,
            "message": "thread_external_id is required.",
        }

    if not is_session_state_configured():

        return {
            "contextId": context_id,
            "threadExternalId": None,
            "message": "Session-state service is not configured for this server.",
        }

    try:

        result = merge_session_state(
            context_id,
            lambda payload: {**payload, "threadExternalId": thread_id},
        )

    except SessionStateError as exc:

        safe_print(f"[session-state] save failed: {exc}")

        return {
            "contextId": context_id,
            "threadExternalId": None,
            "message": str(exc),
        }

    payload = {}

    if isinstance(result, dict):

        payload = result.get("payload") or {}

        if not isinstance(payload, dict):

            payload = {}

    return {
        "contextId": (
            result.get("contextId", context_id)
            if isinstance(result, dict)
            else context_id
        ),
        "threadExternalId": payload.get("threadExternalId", thread_id),
        "createdAt": result.get("createdAt") if isinstance(result, dict) else None,
    }


@mcp.tool
def getOntoAIThreadID(ctx: Context) -> Dict[str, Any]:
    """Return the stored threadExternalId for the active MCP session."""

    context_id = ctx.session_id

    if not is_session_state_configured():

        return {
            "contextId": context_id,
            "threadExternalId": None,
            "message": "Session-state service is not configured for this server.",
        }

    try:

        payload, meta = get_session_state(context_id)

    except SessionStateError as exc:

        safe_print(f"[session-state] get failed: {exc}")

        return {
            "contextId": context_id,
            "threadExternalId": None,
            "message": str(exc),
        }

    thread_id = payload.get("threadExternalId") if isinstance(payload, dict) else None

    if thread_id is None:

        return {
            "contextId": meta.get("contextId", context_id),
            "threadExternalId": None,
            "message": "No session state stored for this context.",
        }

    return {
        "contextId": meta.get("contextId", context_id),
        "threadExternalId": thread_id,
        "createdAt": meta.get("createdAt"),
    }


def _get_valid_token() -> str:
    """Get a valid token, with automatic refresh and helpful error messages."""
    if IS_HTTP_TRANSPORT:
        access_token = _get_fastmcp_access_token()
        if access_token and getattr(access_token, "token", None):
            _cache_access_token_for_legacy(access_token)
            return access_token.token
        raise RuntimeError(
            "OAuth session not found. Start the authorization flow from your MCP client to sign in."
        )

    keycloak_token = keycloak_auth.get_valid_access_token()
    if keycloak_token:
        return keycloak_token

    try:
        return get_token()
    except RuntimeError:
        if keycloak_auth.token_storage.get_access_token():
            raise RuntimeError(
                "Authentication expired and refresh failed. Please re-authenticate with login_with_credentials()."
            )
        raise RuntimeError(
            "No authentication tokens found. Please authenticate with login_with_credentials() first."
        )


def _get_user_spaces_data() -> list[dict]:
    """Internal function to get user spaces data. Used by both resource and tool."""
    url = f"{ONTO_API_BASE}/user/v2/current"

    try:
        token = _get_valid_token()
    except RuntimeError as exc:
        return [{"error": str(exc)}]

    if isinstance(token, str):
        token = token.encode("ascii", errors="ignore").decode("ascii")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        roles = data.get("userRealmsRoles", [])
        spaces = [{"id": r["realmId"], "name": r["realmName"]} for r in roles]

        if spaces:
            if IS_HTTP_TRANSPORT:
                spaces[0]["_session_info"] = _format_http_auth_status()
            else:
                session_status = keycloak_auth.token_storage.get_session_status()
                spaces[0]["_session_info"] = f"Authenticated - {session_status}"

        return spaces
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response else None
        if status_code == 401:
            if IS_HTTP_TRANSPORT:
                return [
                    {
                        "error": "OAuth session is not valid. Use your MCP client to re-authorize this server.",
                    }
                ]
            try:
                keycloak_auth.refresh_access_token()
                token = keycloak_auth.get_valid_access_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                    resp = requests.get(url, headers=headers, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    roles = data.get("userRealmsRoles", [])
                    return [{"id": r["realmId"], "name": r["realmName"]} for r in roles]
            except Exception:
                pass
            return [
                {
                    "error": "Authentication failed. Please re-authenticate with login_with_credentials().",
                }
            ]
        error_text = exc.response.text if exc.response is not None else str(exc)
        return [{"error": f"API Error: {status_code} - {error_text}"}]
    except Exception as exc:
        return [{"error": f"Unexpected error: {exc}"}]


@mcp.resource("onto://spaces")
def get_user_spaces() -> list[dict]:
    """Return the list of Onto realms (spaces) visible to the authorised user."""

    return _get_user_spaces_data()


@mcp.resource("onto://user/info")
def get_user_info() -> dict:
    """Get current user information from Keycloak."""
    if IS_HTTP_TRANSPORT:
        access_token = _get_fastmcp_access_token()
        if access_token and getattr(access_token, "token", None):
            _cache_access_token_for_legacy(access_token)
            user_info = _fetch_userinfo(access_token.token)
            if user_info:
                user_info["_session_status"] = _format_http_auth_status()
                return user_info
            return {
                "error": "Failed to retrieve user information from the identity provider.",
                "_help": "Use get_auth_status() to verify the current OAuth session.",
            }
        return {
            "error": "OAuth session is not available. Run the sign-in flow from your MCP client.",
        }

    try:
        user_info = keycloak_auth.get_user_info()
        if user_info:
            user_info["_session_status"] = (
                keycloak_auth.token_storage.get_session_status()
            )
            return user_info
        return {
            "error": "Failed to get user info - not authenticated or token invalid",
            "_help": "Use login_with_credentials() to authenticate",
        }
    except Exception as exc:
        return {
            "error": f"Error getting user info: {exc}",
            "_help": "Use get_auth_status() to check authentication status",
        }


def get_user_info() -> dict:
    """Get current user information from Keycloak."""

    try:

        user_info = keycloak_auth.get_user_info()

        if user_info:

            # Add session status

            user_info["_session_status"] = (
                keycloak_auth.token_storage.get_session_status()
            )

            return user_info

        else:

            return {
                "error": "❌ Failed to get user info - not authenticated or token invalid",
                "_help": "Use login_with_credentials() to authenticate",
            }

    except Exception as e:

        return {
            "error": f"❌ Error getting user info: {str(e)}",
            "_help": "Use get_auth_status() to check authentication status",
        }


@mcp.tool
def search_templates(
    name_part: str,
    realm_id: str = None,
    include_children: bool = False,
    include_parents: bool = False,
) -> str:
    """

    Search for templates (meta entities) in Onto by name.

    Args:

        name_part: Partial name to search for (required)

        realm_id: Realm ID to search in (optional - uses first available realm if not specified)

        include_children: Include children in search results

        include_parents: Include parents in search results

    Returns:

        JSON string with list of found templates or error message

    """

    try:

        token = _get_valid_token()

    except RuntimeError as e:

        return str(e)

    # Get realm_id if not provided

    if not realm_id:

        spaces = _get_user_spaces_data()

        if not spaces or "error" in spaces[0]:

            return "❌ Failed to get user realms. Please check authentication."

        realm_id = spaces[0]["id"]

        realm_name = spaces[0]["name"]

        safe_print(f"🔍 Using realm: {realm_name} ({realm_id})")

    # Prepare API request

    url = f"{ONTO_API_BASE}/realm/{realm_id}/meta/find"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "namePart": name_part,
        "children": include_children,
        "parents": include_parents,
    }

    try:

        resp = requests.post(url, json=payload, headers=headers, timeout=15)

        resp.raise_for_status()

        # Debug: check response content

        try:

            response_data = resp.json()

        except Exception as json_err:

            return f"❌ Invalid JSON response: {json_err}\nResponse: {resp.text[:500]}"

        # Handle API response format (expecting {result: [...]} structure)

        if isinstance(response_data, dict) and "result" in response_data:

            templates = response_data["result"]

        elif isinstance(response_data, list):

            templates = response_data

        else:

            return f"❌ Unexpected response format: {type(response_data)}\nResponse: {response_data}"

        if not isinstance(templates, list):

            return f"❌ Expected list in result field, got: {type(templates)}\nTemplates: {templates}"

        if not templates:

            return f"🔍 No templates found matching '{name_part}' in realm {realm_id}"

        # Format results nicely

        result_lines = [
            f"🔍 Found {len(templates)} template(s) matching '{name_part}':\n"
        ]

        for i, template in enumerate(templates, 1):

            # Handle both dict and other formats

            if isinstance(template, dict):

                uuid = template.get("uuid", "N/A")

                name = template.get("name", "N/A")

                comment = template.get("comment", "")

            else:

                # Fallback for non-dict items

                uuid = str(template)

                name = str(template)

                comment = ""

            result_lines.append(f"{i}. **{name}**")

            result_lines.append(f"   UUID: {uuid}")

            if comment:

                result_lines.append(f"   Comment: {comment}")

            result_lines.append("")  # Empty line between templates

        return "\n".join(result_lines)

    except requests.exceptions.HTTPError as e:

        if e.response.status_code == 401:

            # Try to refresh token and retry

            try:

                keycloak_auth.refresh_access_token()

                token = keycloak_auth.get_valid_access_token()

                if token:

                    headers["Authorization"] = f"Bearer {token}"

                    resp = requests.post(url, json=payload, headers=headers, timeout=15)

                    resp.raise_for_status()

                    try:

                        response_data = resp.json()

                    except Exception as json_err:

                        return f"❌ Invalid JSON response after retry: {json_err}\nResponse: {resp.text[:500]}"

                    # Handle API response format

                    if isinstance(response_data, dict) and "result" in response_data:

                        templates = response_data["result"]

                    elif isinstance(response_data, list):

                        templates = response_data

                    else:

                        return f"❌ Unexpected response format after retry: {type(response_data)}\nResponse: {response_data}"

                    if not isinstance(templates, list):

                        return f"❌ Expected list in result field after retry, got: {type(templates)}\nTemplates: {templates}"

                    if not templates:

                        return f"🔍 No templates found matching '{name_part}' in realm {realm_id}"

                    result_lines = [
                        f"🔍 Found {len(templates)} template(s) matching '{name_part}':\n"
                    ]

                    for i, template in enumerate(templates, 1):

                        if isinstance(template, dict):

                            uuid = template.get("uuid", "N/A")

                            name = template.get("name", "N/A")

                            comment = template.get("comment", "")

                        else:

                            uuid = str(template)

                            name = str(template)

                            comment = ""

                        result_lines.append(f"{i}. **{name}**")

                        result_lines.append(f"   UUID: {uuid}")

                        if comment:

                            result_lines.append(f"   Comment: {comment}")

                        result_lines.append("")

                    return "\n".join(result_lines)

            except Exception:

                pass

            return "❌ Authentication failed. Please re-authenticate with login_with_credentials()"

        elif e.response.status_code == 403:

            return f"❌ Access denied to realm {realm_id}. You may not have permission to search templates in this realm."

        elif e.response.status_code == 404:

            return (
                f"❌ Realm {realm_id} not found or meta search endpoint not available."
            )

        else:

            return f"❌ API Error: {e.response.status_code} - {e.response.text}"

    except Exception as e:

        return f"❌ Unexpected error: {str(e)}"


@mcp.tool
def list_available_realms() -> str:
    """

    Get list of available realms (spaces) that the user can access.

    Useful for getting realm IDs for template searches.

    Returns:

        Formatted list of realms with IDs and names

    """

    spaces = _get_user_spaces_data()

    if not spaces:

        return "❌ No realms found. Please check authentication."

    if "error" in spaces[0]:

        return spaces[0]["error"]

    result_lines = [f"📁 Available realms ({len(spaces)}):\n"]

    for i, space in enumerate(spaces, 1):

        realm_id = space.get("id", "N/A")

        realm_name = space.get("name", "N/A")

        result_lines.append(f"{i}. **{realm_name}**")

        result_lines.append(f"   ID: {realm_id}")

        result_lines.append("")

    result_lines.append(
        "💡 Use the realm ID with search_templates() to search in a specific realm."
    )

    return "\n".join(result_lines)


@mcp.tool
def search_objects(
    realm_id: str = None,
    name_filter: str = "",
    template_uuid: str = "",
    comment_filter: str = "",
    load_all: bool = False,
    page_size: int = 20,
) -> str:
    """

    Search for objects in Onto by name, template, or comment with pagination support.

    Args:

        realm_id: Realm ID to search in (optional - uses first available realm if not specified)

        name_filter: Partial name to search for

        template_uuid: UUID of template to filter by

        comment_filter: Partial comment to search for

        load_all: If True, loads ALL matching objects using pagination (may be slow for large datasets)

        page_size: Number of items per page (default: 20, will be reduced automatically if payload too large)

    Returns:

        JSON-formatted string with list of found objects or error message

    """

    try:

        token = _get_valid_token()

    except RuntimeError as e:

        return str(e)

    # Get realm_id if not provided

    if not realm_id:

        spaces = _get_user_spaces_data()

        if not spaces or "error" in spaces[0]:

            return "❌ Failed to get user realms. Please check authentication."

        realm_id = spaces[0]["id"]

        realm_name = spaces[0]["name"]

        safe_print(f"🔍 Using realm: {realm_name} ({realm_id})")

    # Prepare API request

    url = f"{ONTO_API_BASE}/realm/{realm_id}/entity/find/v2"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    def make_request(first: int, offset: int) -> tuple[list, bool]:
        """Make API request and return (results, has_more_data)"""

        payload = {
            "name": name_filter,
            "comment": comment_filter,
            "metaFieldFilters": [],
            "pagination": {"first": first, "offset": offset},
        }

        # Add template filter if provided

        if template_uuid:

            payload["metaEntityRequest"] = {"uuid": template_uuid}

        try:

            resp = requests.post(url, json=payload, headers=headers, timeout=30)

            resp.raise_for_status()

            try:

                response_data = resp.json()

            except Exception as json_err:

                raise Exception(
                    f"Invalid JSON response: {json_err}\nResponse: {resp.text[:500]}"
                )

            # Response should be a list (may contain group wrappers with "entities")

            if not isinstance(response_data, list):

                raise Exception(
                    f"Expected list response, got: {type(response_data)}\nResponse: {response_data}"
                )

            # Flatten results – each item may be either an entity dict OR a wrapper with "entities" list

            flat_results: list = []

            for item in response_data:

                if (
                    isinstance(item, dict)
                    and "entities" in item
                    and isinstance(item["entities"], list)
                ):

                    # Wrapper object – extend with its entities

                    flat_results.extend(item["entities"])

                else:

                    flat_results.append(item)

            # Determine if more data likely exists based on original items count OR flattened count

            has_more = len(response_data) == offset or len(flat_results) == offset

            return flat_results, has_more

        except requests.exceptions.HTTPError as e:

            if e.response.status_code == 413 or "payload too large" in str(e).lower():

                # Payload too large - reduce page size

                if offset > 5:

                    safe_print(
                        f"⚠️ Payload too large, reducing page size from {offset} to {offset//2}"
                    )

                    return make_request(first, offset // 2)

                else:

                    raise Exception(
                        f"❌ Payload too large even with minimum page size (5). Try more specific filters."
                    )

            elif e.response.status_code == 401:

                # Try to refresh token and retry

                try:

                    keycloak_auth.refresh_access_token()

                    new_token = keycloak_auth.get_valid_access_token()

                    if new_token:

                        headers["Authorization"] = f"Bearer {new_token}"

                        resp = requests.post(
                            url, json=payload, headers=headers, timeout=30
                        )

                        resp.raise_for_status()

                        response_data = resp.json()

                        has_more = len(response_data) == offset

                        return response_data, has_more

                except Exception:

                    pass

                raise Exception(
                    "❌ Authentication failed. Please re-authenticate with login_with_credentials()"
                )

            elif e.response.status_code == 403:

                raise Exception(
                    f"❌ Access denied to realm {realm_id}. You may not have permission to search objects in this realm."
                )

            elif e.response.status_code == 404:

                raise Exception(
                    f"❌ Realm {realm_id} not found or entity search endpoint not available."
                )

            else:

                raise Exception(
                    f"❌ API Error: {e.response.status_code} - {e.response.text}"
                )

    # Execute search with pagination

    all_objects = []

    current_first = 0

    current_page_size = page_size

    total_requests = 0

    max_requests = 100  # Safety limit

    try:

        while total_requests < max_requests:

            total_requests += 1

            # Make request

            objects, has_more = make_request(current_first, current_page_size)

            all_objects.extend(objects)

            safe_print(
                f"📄 Loaded page: first={current_first}, count={len(objects)}, total_so_far={len(all_objects)}"
            )

            # If not loading all, or no more data, break

            if not load_all or not has_more:

                break

            # Prepare for next page

            current_first += len(objects)

        if total_requests >= max_requests:

            safe_print(f"⚠️ Hit safety limit of {max_requests} requests")

    except Exception as e:

        return str(e)

    # Format results

    if not all_objects:

        filters_desc = []

        if name_filter:

            filters_desc.append(f"name containing '{name_filter}'")

        if template_uuid:

            filters_desc.append(f"template '{template_uuid}'")

        if comment_filter:

            filters_desc.append(f"comment containing '{comment_filter}'")

        filters_text = " and ".join(filters_desc) if filters_desc else "any criteria"

        return f"🔍 No objects found matching {filters_text} in realm {realm_id}"

    # Build result summary

    result_lines = []

    # Header with search info

    search_info = []

    if name_filter:

        search_info.append(f"name: '{name_filter}'")

    if template_uuid:

        search_info.append(f"template: '{template_uuid}'")

    if comment_filter:

        search_info.append(f"comment: '{comment_filter}'")

    search_desc = ", ".join(search_info) if search_info else "all objects"

    if load_all:

        result_lines.append(
            f"🔍 **Found {len(all_objects)} objects** (complete dataset) matching {search_desc}:"
        )

    else:

        result_lines.append(
            f"🔍 **Found {len(all_objects)} objects** (first page) matching {search_desc}:"
        )

    result_lines.append("")

    # Show objects (limit display to first 50 for readability)

    display_limit = 50

    displayed_count = min(len(all_objects), display_limit)

    for i, obj in enumerate(all_objects[:display_limit], 1):

        if isinstance(obj, dict):

            uuid = obj.get("id", "N/X")

            name = obj.get("name", "N/X")

            comment = obj.get("comment", "")

            # Get template info if available

            meta_entity = obj.get("metaEntity", {})

            template_name = meta_entity.get("name", "") if meta_entity else ""

            template_id = meta_entity.get("id", "") if meta_entity else ""

            result_lines.append(f"{i}. **{name}**")

            result_lines.append(f"   UUID: {uuid}")

            if template_name:

                result_lines.append(f"   Template: {template_name} ({template_id})")

            if comment:

                # Truncate long comments

                display_comment = (
                    comment[:100] + "..." if len(comment) > 100 else comment
                )

                result_lines.append(f"   Comment: {display_comment}")

            result_lines.append("")

        else:

            result_lines.append(f"{i}. {str(obj)}")

            result_lines.append("")

    # Add truncation notice if needed

    if len(all_objects) > display_limit:

        result_lines.append(
            f"... and {len(all_objects) - display_limit} more objects (truncated for display)"
        )

        result_lines.append("")

    # Add usage tips

    if not load_all and len(all_objects) == page_size:

        result_lines.append(
            "💡 **Tip:** There might be more results. Use `load_all=True` to get the complete dataset."
        )

    if load_all and len(all_objects) > 100:

        result_lines.append(
            "📊 **Large Dataset:** Consider using more specific filters for better performance."
        )

    return "\n".join(result_lines)


# ---------------------------------------------------------------------------

# Realm (workspace) management

# ---------------------------------------------------------------------------


@mcp.tool
def create_realm(name: str, comment: str = "") -> str:
    """Create a new workspace (realm).

    Args:

        name: Unique name of the workspace.

        comment: Optional comment (can be empty).

    Returns:

        Formatted string with info about newly created realm or error message.

    """

    if not name or not name.strip():

        return "❌ Parameter 'name' is required and cannot be empty."

    try:

        token = _get_valid_token()

    except RuntimeError as e:

        return str(e)

    url = f"{ONTO_API_BASE}/realm/"  # According to API: POST /api/v2/core/realm/

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {"name": name.strip(), "comment": comment or ""}

    try:

        resp = requests.post(url, json=payload, headers=headers, timeout=30)

        resp.raise_for_status()

        data = resp.json()

        realm_id = data.get("id", "N/A")

        realm_name = data.get("name", "N/A")

        realm_comment = data.get("comment", "")

        result = [
            "🎉 **Workspace (realm) created successfully!**",
            f"ID: {realm_id}",
            f"Name: {realm_name}",
        ]

        if realm_comment:

            result.append(f"Comment: {realm_comment}")

        return "\n".join(result)

    except requests.exceptions.HTTPError as e:

        status = e.response.status_code

        if status == 400:

            return "❌ Bad request – please check the input data (maybe the name is missing or invalid)."

        if status == 401:

            return "❌ Authentication failed – please login again."

        if status == 403:

            return "❌ Access denied – you don't have permission to create a workspace."

        if status == 409:

            return (
                f"❌ Workspace with name '{name}' already exists. Choose another name."
            )

        return f"❌ API Error: {status} - {e.response.text[:200]}"

    except Exception as e:

        return f"❌ Unexpected error: {e}"


# ---------------------------------------------------------------------------

# Template (meta entity) management

# ---------------------------------------------------------------------------


@mcp.tool
def create_template(realm_id: str, name: str, comment: str = "") -> str:
    """Create a new template (meta entity) in a specified realm.

    Before creating, searches for an existing template with the same

    name to avoid duplicates.

    Args:

        realm_id: Target realm ID where the template will be created.

        name: Template name (must be unique).

        comment: Optional comment.

    Returns:

        Success message with template info or error details.

    """

    # Validate inputs

    if not realm_id or not realm_id.strip():

        return "❌ Parameter 'realm_id' is required and cannot be empty."

    if not name or not name.strip():

        return "❌ Parameter 'name' is required and cannot be empty."

    try:

        token = _get_valid_token()

    except RuntimeError as e:

        return str(e)

    # Step 1: Search existing templates

    search_url = f"{ONTO_API_BASE}/realm/{realm_id}/meta/find"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    search_payload = {"namePart": name.strip(), "children": False, "parents": False}

    try:

        resp = requests.post(
            search_url, json=search_payload, headers=headers, timeout=15
        )

        resp.raise_for_status()

        data = resp.json()

        templates = data.get("result") if isinstance(data, dict) else data

        if isinstance(templates, list):

            for tpl in templates:

                if (
                    isinstance(tpl, dict)
                    and tpl.get("name", "").lower() == name.strip().lower()
                ):

                    existing_id = tpl.get("uuid") or tpl.get("id", "N/A")

                    return f"❌ Template with name '{name}' already exists (UUID: {existing_id})."

    except requests.exceptions.HTTPError as e:

        if e.response.status_code not in (404, 400):

            return f"❌ Error searching templates: {e.response.text[:200]}"

    except Exception as e:

        return f"❌ Error searching templates: {e}"

    # Step 2: Create new template

    create_url = f"{ONTO_API_BASE}/realm/{realm_id}/meta"

    template_id = str(uuid.uuid4())

    create_payload = {
        "id": template_id,
        "name": name.strip(),
        "comment": comment or "",
    }

    try:

        resp = requests.post(
            create_url, json=create_payload, headers=headers, timeout=30
        )

        resp.raise_for_status()

        created = resp.json() if resp.content else {}

        created_id = created.get("id", template_id)

        result = [
            "🎉 **Template created successfully!**",
            f"ID: {created_id}",
            f"Name: {name.strip()}",
        ]

        if comment:

            result.append(f"Comment: {comment}")

        return "\n".join(result)

    except requests.exceptions.HTTPError as e:

        status = e.response.status_code

        if status == 400:

            return "❌ Bad request – please check input data."

        if status == 401:

            return "❌ Authentication failed – please login again."

        if status == 403:

            return "❌ Access denied – you don't have permission to create templates in this realm."

        if status == 409:

            return f"❌ Template with name '{name}' already exists."

        return f"❌ API Error: {status} - {e.response.text[:200]}"

    except Exception as e:

        return f"❌ Unexpected error: {e}"


# ---------------------------------------------------------------------------

# Batch entity creation

# ---------------------------------------------------------------------------


@mcp.tool
def create_entities_batch(realm_id: str, entities: list[dict]) -> str:
    """Create multiple entities in a realm in one batch.

    Args:

        realm_id: Target realm ID.

        entities: List of entity dicts with keys: name (required), id, comment, metaEntityId.

    Returns:

        Formatted success message or detailed error message.

    """

    # Validate inputs

    if not realm_id or not realm_id.strip():

        return "❌ Parameter 'realm_id' is required and cannot be empty."

    if not entities or not isinstance(entities, list):

        return "❌ Parameter 'entities' must be a non-empty list."

    # Ensure all have name

    for i, ent in enumerate(entities, 1):

        if not isinstance(ent, dict):

            return f"❌ Entity #{i} is not a dict."

        if not ent.get("name") or not ent["name"].strip():

            return f"❌ Entity #{i} is missing required 'name'."

    try:

        token = _get_valid_token()

    except RuntimeError as e:

        return str(e)

    # Duplicate check using direct API call (avoid calling mcp tool functions)

    duplicate_names: list[str] = []

    headers_basic = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    for ent in entities:

        name = ent["name"].strip()

        # Build minimal payload to search by name

        search_url = f"{ONTO_API_BASE}/realm/{realm_id}/entity/find/v2"

        search_payload = {
            "name": name,
            "comment": "",
            "metaFieldFilters": [],
            "pagination": {"first": 0, "offset": 5},
        }

        try:

            resp = requests.post(
                search_url, json=search_payload, headers=headers_basic, timeout=15
            )

            resp.raise_for_status()

            data = resp.json()

            if isinstance(data, list) and data:

                # Any result means duplicate

                duplicate_names.append(name)

        except Exception:

            # If search fails, skip duplicate detection for this name

            pass

    if duplicate_names:

        dup_list = ", ".join(duplicate_names)

        return f"❌ Duplicate entity names detected in realm {realm_id}: {dup_list}. Aborting creation."

    # Build payload

    payload_entities = []

    for ent in entities:

        item = {
            "id": ent.get("id") or None,
            "name": ent["name"].strip(),
            "comment": ent.get("comment", ""),
            "metaEntityId": ent.get("metaEntityId"),
        }

        payload_entities.append(item)

    payload = {"entities": payload_entities}

    url = f"{ONTO_API_BASE}/realm/{realm_id}/entity/batch"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:

        resp = requests.post(url, json=payload, headers=headers, timeout=60)

        resp.raise_for_status()

        data = resp.json() if resp.content else {}

        created = data.get("createdEntities", [])

        result_lines = [
            f"🎉 **Successfully created {len(created)} entities in realm {realm_id}.**",
            "",
        ]

        for i, ent in enumerate(created, 1):

            uuid_ = ent.get("uuid") or ent.get("id", "N/A")

            name = ent.get("name", "N/A")

            comment = ent.get("comment", "")

            result_lines.append(f"{i}. **{name}**")

            result_lines.append(f"   UUID: {uuid_}")

            if comment:

                result_lines.append(f"   Comment: {comment}")

            # Meta entity info

            meta = ent.get("metaEntity") or {}

            if meta:

                meta_name = meta.get("name", "")

                meta_uuid = meta.get("uuid") or meta.get("id", "")

                result_lines.append(f"   Template: {meta_name} ({meta_uuid})")

            result_lines.append("")

        return "\n".join(result_lines)

    except requests.exceptions.HTTPError as e:

        status = e.response.status_code

        if status == 400:

            try:

                err_msg = e.response.json().get("message", "Bad Request")

            except Exception:

                err_msg = e.response.text[:200]

            return f"❌ Bad request – {err_msg}"

        if status == 401:

            return "❌ Authentication failed – please login again."

        if status == 403:

            return "❌ Access denied – you don't have permission to create entities in this realm."

        return f"❌ API Error: {status} - {e.response.text[:200]}"

    except Exception as e:

        return f"❌ Unexpected error: {e}"
