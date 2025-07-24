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
    # Use new storage system for manual tokens
    if keycloak_auth.store_manual_token(token):
        # Also store in old system for backward compatibility
        set_token(token)
        return "✅ Token stored successfully in persistent storage"
    else:
        return "❌ Invalid token format"

@mcp.tool
def login_with_credentials(username: str, password: str) -> str:
    """
    Authenticate with Keycloak using username and password.
    This method saves tokens persistently for future sessions.
    
    Args:
        username: User's username or email
        password: User's password
    
    Returns:
        Success message or error details
    """
    try:
        if keycloak_auth.authenticate_with_password(username, password):
            # Store token in old system for compatibility
            access_token = keycloak_auth.get_valid_access_token()
            if access_token:
                set_token(access_token)
                user_info = keycloak_auth.get_user_info()
                if user_info:
                    email = user_info.get('email', 'Unknown')
                    return f"✅ Successfully authenticated as {email}. Session saved persistently."
                else:
                    return "✅ Authentication successful. Session saved persistently."
            else:
                return "❌ Authentication succeeded but failed to get access token"
        else:
            return "❌ Authentication failed - invalid credentials"
    except Exception as e:
        return f"❌ Authentication error: {str(e)}"

@mcp.tool
def setup_auth_interactive() -> str:
    """
    Get step-by-step instructions for setting up authentication.
    Provides multiple authentication options.
    
    Returns:
        Instructions for authentication setup
    """
    status = keycloak_auth.token_storage.get_session_status()
    
    instructions = f"""
🔐 **Onto Authentication Setup**

**Current Status:** {status}

**Option 1: Username/Password (Recommended)**
Call: `login_with_credentials("your_email@example.com", "your_password")`

**Option 2: Browser-based OAuth (More Secure)**
1. Call: `get_keycloak_auth_url()`
2. Open the returned URL in browser
3. Login with your Onto credentials  
4. Copy the 'code' parameter from callback URL
5. Call: `exchange_auth_code("your_code_here")`

**Option 3: Manual Token**
Call: `login_via_token("your_jwt_token_here")`

**Check Status:**
Call: `get_session_info()` to see detailed authentication status

✨ **Once authenticated, your session will be saved and persist across MCP restarts!**
"""
    
    return instructions

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
        return f"""
🌐 **OAuth Authorization URL:**
{auth_url}

📝 **Instructions:**
1. Open this URL in your browser
2. Login with your Onto credentials
3. You'll be redirected to: {redirect_uri}?code=...
4. Copy the 'code' parameter value
5. Use `exchange_auth_code("code_value")` to complete authentication
"""
    except Exception as e:
        return f"❌ Error generating auth URL: {str(e)}"

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
                user_info = keycloak_auth.get_user_info()
                if user_info:
                    email = user_info.get('email', 'Unknown')
                    return f"✅ OAuth authentication successful! Logged in as {email}. Session saved persistently."
                else:
                    return "✅ OAuth authentication successful! Session saved persistently."
            else:
                return "❌ Token exchange succeeded but failed to get access token"
        else:
            return "❌ Failed to exchange authorization code for tokens"
    except Exception as e:
        return f"❌ Token exchange error: {str(e)}"

@mcp.tool
def refresh_token() -> str:
    """
    Refresh the current access token.
    This happens automatically when needed, but you can call it manually.
    
    Returns:
        Success message or error details
    """
    try:
        if keycloak_auth.refresh_access_token():
            # Update stored token
            access_token = keycloak_auth.get_valid_access_token()
            if access_token:
                set_token(access_token)
                return "🔄 Token refreshed successfully"
            else:
                return "❌ Token refresh succeeded but failed to get new access token"
        else:
            return "❌ Failed to refresh token - may need to re-authenticate"
    except Exception as e:
        return f"❌ Token refresh error: {str(e)}"

@mcp.tool
def get_auth_status() -> str:
    """
    Get current authentication status with helpful guidance.
    
    Returns:
        Authentication status information
    """
    try:
        is_authenticated = keycloak_auth.is_authenticated()
        status = keycloak_auth.token_storage.get_session_status()
        
        if is_authenticated:
            user_info = keycloak_auth.get_user_info()
            if user_info:
                username = user_info.get('preferred_username', 'Unknown')
                email = user_info.get('email', 'Unknown')
                result = f"✅ **Authenticated** as: {username} ({email})\n"
                result += f"📊 Status: {status}"
                
                # Add token info
                token_info = keycloak_auth.token_storage.get_token_info()
                if token_info.get('access_token_expired'):
                    result += "\n🔄 Access token expired but refresh available"
                else:
                    result += "\n🟢 Access token valid"
                
                return result
            else:
                return f"✅ Authenticated (token valid)\n📊 Status: {status}"
        else:
            return f"""
❌ **Not authenticated**
📊 Status: {status}

🔧 **To authenticate, use one of these methods:**
• `login_with_credentials("email", "password")` - Username/password
• `setup_auth_interactive()` - Get step-by-step instructions
• `get_keycloak_auth_url()` - Browser-based OAuth
"""
    except Exception as e:
        return f"❌ Error checking auth status: {str(e)}"

@mcp.tool
def get_session_info() -> str:
    """
    Get detailed session information including token status.
    
    Returns:
        Detailed session information
    """
    try:
        session_info = keycloak_auth.get_session_info()
        
        result = f"""
📊 **Detailed Session Information**

**Status:** {session_info.get('session_status', 'Unknown')}

**Token Information:**
• Has Access Token: {'✅' if session_info.get('has_access_token') else '❌'}
• Has Refresh Token: {'✅' if session_info.get('has_refresh_token') else '❌'}
• Access Token Expired: {'⏰' if session_info.get('access_token_expired') else '🟢'}
• Refresh Token Expired: {'⏰' if session_info.get('refresh_token_expired') else '🟢'}
"""
        
        if 'last_updated' in session_info and session_info['last_updated']:
            import datetime
            last_updated = datetime.datetime.fromtimestamp(session_info['last_updated'])
            result += f"• Last Updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if 'user' in session_info:
            user = session_info['user']
            result += f"""
**User Information:**
• Email: {user.get('email', 'Unknown')}
• Name: {user.get('name', 'Unknown')}
• Username: {user.get('username', 'Unknown')}
"""
        
        # Add storage location
        storage_path = keycloak_auth.token_storage.token_file
        result += f"\n**Storage:** {storage_path}"
        
        return result
    except Exception as e:
        return f"❌ Error getting session info: {str(e)}"

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
            return "🚪 Logged out successfully. All tokens cleared from persistent storage."
        else:
            return "🚪 Logged out locally (remote logout may have failed). All local tokens cleared."
    except Exception as e:
        return f"❌ Logout error: {str(e)}"

def _get_valid_token() -> str:
    """Get a valid token, with automatic refresh and helpful error messages."""
    # Try Keycloak auth first (with automatic refresh)
    keycloak_token = keycloak_auth.get_valid_access_token()
    if keycloak_token:
        return keycloak_token
    
    # Fall back to manual token
    try:
        return get_token()
    except RuntimeError:
        # Provide helpful guidance
        if keycloak_auth.token_storage.get_access_token():
            # We have tokens but they're expired and refresh failed
            raise RuntimeError("""
❌ Authentication expired and refresh failed.

🔧 Please re-authenticate using:
• `login_with_credentials("email", "password")` - If you have credentials
• `get_keycloak_auth_url()` - For browser-based OAuth
• `setup_auth_interactive()` - For step-by-step instructions
""")
        else:
            # No tokens at all
            raise RuntimeError("""
❌ No authentication tokens found.

🔧 Please authenticate first using:
• `login_with_credentials("email", "password")` - Username/password
• `setup_auth_interactive()` - Get step-by-step instructions
• `get_keycloak_auth_url()` - Browser-based OAuth

ℹ️ Your session will be saved persistently after authentication.
""")

@mcp.resource("onto://spaces")
def get_user_spaces() -> list[dict]:
    """Return the list of Onto realms (spaces) visible to the authorised user."""
    url = f"{ONTO_API_BASE}/user/v2/current"
    
    try:
        token = _get_valid_token()
    except RuntimeError as e:
        # Return helpful error as part of the resource data
        return [{"error": str(e)}]
    
    # Ensure token is clean ASCII
    if isinstance(token, str):
        token = token.encode('ascii', errors='ignore').decode('ascii')
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        roles = data.get("userRealmsRoles", [])
        spaces = [{"id": r["realmId"], "name": r["realmName"]} for r in roles]
        
        # Add session info to the first space entry if available
        if spaces:
            session_status = keycloak_auth.token_storage.get_session_status()
            spaces[0]["_session_info"] = f"✅ Authenticated - {session_status}"
        
        return spaces
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            # Token might be invalid, try to refresh
            try:
                keycloak_auth.refresh_access_token()
                # Retry with refreshed token
                token = keycloak_auth.get_valid_access_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                    resp = requests.get(url, headers=headers, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    roles = data.get("userRealmsRoles", [])
                    return [{"id": r["realmId"], "name": r["realmName"]} for r in roles]
            except:
                pass
            
            return [{"error": "❌ Authentication failed. Please re-authenticate with login_with_credentials() or get_keycloak_auth_url()"}]
        else:
            return [{"error": f"❌ API Error: {e.response.status_code} - {e.response.text}"}]
    except Exception as e:
        return [{"error": f"❌ Unexpected error: {str(e)}"}]

@mcp.resource("onto://user/info")
def get_user_info() -> dict:
    """Get current user information from Keycloak."""
    try:
        user_info = keycloak_auth.get_user_info()
        if user_info:
            # Add session status
            user_info["_session_status"] = keycloak_auth.token_storage.get_session_status()
            return user_info
        else:
            return {
                "error": "❌ Failed to get user info - not authenticated or token invalid",
                "_help": "Use login_with_credentials() or get_keycloak_auth_url() to authenticate"
            }
    except Exception as e:
        return {
            "error": f"❌ Error getting user info: {str(e)}",
            "_help": "Use get_auth_status() to check authentication status"
        }
