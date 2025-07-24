from __future__ import annotations

import os
from fastmcp import FastMCP
import requests
from .auth import get_token, set_token
from .keycloak_auth import KeycloakAuth

mcp = FastMCP(name="Onto MCP Server")

ONTO_API_BASE = os.getenv("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

# Global Keycloak auth instance
keycloak_auth = KeycloakAuth()

@mcp.tool
def login_via_token(token: str) -> str:
    """Store user's personal Onto access-token."""
    set_token(token)
    return "Token stored successfully"

@mcp.tool
def login_with_credentials(username: str, password: str) -> str:
    """
    Authenticate with Keycloak using username and password.
    
    Args:
        username: User's username or email
        password: User's password
    
    Returns:
        Success message or error details
    """
    try:
        if keycloak_auth.authenticate_with_password(username, password):
            # Get the access token and store it in the old auth system for compatibility
            access_token = keycloak_auth.get_valid_access_token()
            if access_token:
                set_token(access_token)
                return "Successfully authenticated with Keycloak"
            else:
                return "Authentication succeeded but failed to get access token"
        else:
            return "Authentication failed - invalid credentials"
    except Exception as e:
        return f"Authentication error: {str(e)}"

@mcp.tool
def get_keycloak_auth_url(redirect_uri: str = "http://localhost:8080/callback") -> str:
    """
    Get Keycloak authorization URL for OAuth 2.0 flow.
    
    Args:
        redirect_uri: Callback URL (default: http://localhost:8080/callback)
    
    Returns:
        Authorization URL for browser-based authentication
    """
    try:
        auth_url = keycloak_auth.get_authorization_url(redirect_uri)
        return f"Open this URL in browser to authenticate:\n{auth_url}"
    except Exception as e:
        return f"Error generating auth URL: {str(e)}"

@mcp.tool
def exchange_auth_code(code: str, redirect_uri: str = "http://localhost:8080/callback") -> str:
    """
    Exchange authorization code for access token.
    
    Args:
        code: Authorization code from callback
        redirect_uri: Same redirect URI used in auth URL
    
    Returns:
        Success message or error details
    """
    try:
        if keycloak_auth.exchange_code_for_token(code, redirect_uri):
            # Store token for compatibility
            access_token = keycloak_auth.get_valid_access_token()
            if access_token:
                set_token(access_token)
                return "Successfully exchanged code for tokens"
            else:
                return "Token exchange succeeded but failed to get access token"
        else:
            return "Failed to exchange authorization code for tokens"
    except Exception as e:
        return f"Token exchange error: {str(e)}"

@mcp.tool
def refresh_token() -> str:
    """
    Refresh the current access token.
    
    Returns:
        Success message or error details
    """
    try:
        if keycloak_auth.refresh_access_token():
            # Update stored token
            access_token = keycloak_auth.get_valid_access_token()
            if access_token:
                set_token(access_token)
                return "Token refreshed successfully"
            else:
                return "Token refresh succeeded but failed to get new access token"
        else:
            return "Failed to refresh token - may need to re-authenticate"
    except Exception as e:
        return f"Token refresh error: {str(e)}"

@mcp.tool
def get_auth_status() -> str:
    """
    Get current authentication status.
    
    Returns:
        Authentication status information
    """
    try:
        is_authenticated = keycloak_auth.is_authenticated()
        if is_authenticated:
            user_info = keycloak_auth.get_user_info()
            if user_info:
                username = user_info.get('preferred_username', 'Unknown')
                email = user_info.get('email', 'Unknown')
                return f"✅ Authenticated as: {username} ({email})"
            else:
                return "✅ Authenticated (token valid but couldn't get user info)"
        else:
            return "❌ Not authenticated - use login_with_credentials or get_keycloak_auth_url"
    except Exception as e:
        return f"Error checking auth status: {str(e)}"

@mcp.tool
def logout() -> str:
    """
    Logout and clear all authentication tokens.
    
    Returns:
        Logout status message
    """
    try:
        success = keycloak_auth.logout()
        # Clear old auth system token too
        try:
            set_token("")
        except:
            pass
        
        if success:
            return "Logged out successfully"
        else:
            return "Logged out locally (remote logout may have failed)"
    except Exception as e:
        return f"Logout error: {str(e)}"

def _get_valid_token() -> str:
    """Get a valid token, trying both auth systems."""
    # Try Keycloak auth first
    keycloak_token = keycloak_auth.get_valid_access_token()
    if keycloak_token:
        return keycloak_token
    
    # Fall back to manual token
    try:
        return get_token()
    except RuntimeError:
        raise RuntimeError("No valid token available. Please authenticate first.")

@mcp.resource("onto://spaces")
def get_user_spaces() -> list[dict]:
    """Return the list of Onto realms (spaces) visible to the authorised user."""
    url = f"{ONTO_API_BASE}/user/v2/current"
    token = _get_valid_token()
    
    # Ensure token is clean ASCII
    if isinstance(token, str):
        token = token.encode('ascii', errors='ignore').decode('ascii')
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    roles = data.get("userRealmsRoles", [])
    return [{"id": r["realmId"], "name": r["realmName"]} for r in roles]

@mcp.resource("onto://user/info")
def get_user_info() -> dict:
    """Get current user information from Keycloak."""
    try:
        user_info = keycloak_auth.get_user_info()
        if user_info:
            return user_info
        else:
            raise RuntimeError("Failed to get user info - not authenticated or token invalid")
    except Exception as e:
        raise RuntimeError(f"Error getting user info: {str(e)}")
