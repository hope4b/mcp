from __future__ import annotations

import os  # Still used for sys.path adjustments in tests; keep for now
from fastmcp import FastMCP
import requests
from .auth import get_token, set_token
from .keycloak_auth import KeycloakAuth
from .settings import ONTO_API_BASE
from .utils import safe_print

mcp = FastMCP(name="Onto MCP Server")

# ONTO_API_BASE now comes from settings (with env/default handling)

# Global Keycloak auth instance
keycloak_auth = KeycloakAuth()

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

🔧 **To authenticate, use:**
• `login_with_credentials("email", "password")` - Username/password authentication
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
• `login_with_credentials("email", "password")` - Username/password authentication
""")
        else:
            # No tokens at all
            raise RuntimeError("""
❌ No authentication tokens found.

🔧 Please authenticate first using:
• `login_with_credentials("email", "password")` - Username/password authentication

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
            
            return [{"error": "❌ Authentication failed. Please re-authenticate with login_with_credentials()"}]
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
                "_help": "Use login_with_credentials() to authenticate"
            }
    except Exception as e:
        return {
            "error": f"❌ Error getting user info: {str(e)}",
            "_help": "Use get_auth_status() to check authentication status"
        }

@mcp.tool
def search_templates(name_part: str, realm_id: str = None, include_children: bool = False, include_parents: bool = False) -> str:
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
        spaces = get_user_spaces()
        if not spaces or 'error' in spaces[0]:
            return "❌ Failed to get user realms. Please check authentication."
        
        realm_id = spaces[0]['id']
        realm_name = spaces[0]['name']
        safe_print(f"🔍 Using realm: {realm_name} ({realm_id})")
    
    # Prepare API request
    url = f"{ONTO_API_BASE}/realm/{realm_id}/meta/find"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "namePart": name_part,
        "children": include_children,
        "parents": include_parents
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
        if isinstance(response_data, dict) and 'result' in response_data:
            templates = response_data['result']
        elif isinstance(response_data, list):
            templates = response_data
        else:
            return f"❌ Unexpected response format: {type(response_data)}\nResponse: {response_data}"
        
        if not isinstance(templates, list):
            return f"❌ Expected list in result field, got: {type(templates)}\nTemplates: {templates}"
        
        if not templates:
            return f"🔍 No templates found matching '{name_part}' in realm {realm_id}"
        
        # Format results nicely
        result_lines = [f"🔍 Found {len(templates)} template(s) matching '{name_part}':\n"]
        
        for i, template in enumerate(templates, 1):
            # Handle both dict and other formats
            if isinstance(template, dict):
                uuid = template.get('uuid', 'N/A')
                name = template.get('name', 'N/A')
                comment = template.get('comment', '')
            else:
                # Fallback for non-dict items
                uuid = str(template)
                name = str(template)
                comment = ''
            
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
                    if isinstance(response_data, dict) and 'result' in response_data:
                        templates = response_data['result']
                    elif isinstance(response_data, list):
                        templates = response_data
                    else:
                        return f"❌ Unexpected response format after retry: {type(response_data)}\nResponse: {response_data}"
                    
                    if not isinstance(templates, list):
                        return f"❌ Expected list in result field after retry, got: {type(templates)}\nTemplates: {templates}"
                    
                    if not templates:
                        return f"🔍 No templates found matching '{name_part}' in realm {realm_id}"
                    
                    result_lines = [f"🔍 Found {len(templates)} template(s) matching '{name_part}':\n"]
                    for i, template in enumerate(templates, 1):
                        if isinstance(template, dict):
                            uuid = template.get('uuid', 'N/A')
                            name = template.get('name', 'N/A')
                            comment = template.get('comment', '')
                        else:
                            uuid = str(template)
                            name = str(template)
                            comment = ''
                        
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
            return f"❌ Realm {realm_id} not found or meta search endpoint not available."
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
    spaces = get_user_spaces()
    
    if not spaces:
        return "❌ No realms found. Please check authentication."
    
    if 'error' in spaces[0]:
        return spaces[0]['error']
    
    result_lines = [f"📁 Available realms ({len(spaces)}):\n"]
    
    for i, space in enumerate(spaces, 1):
        realm_id = space.get('id', 'N/A')
        realm_name = space.get('name', 'N/A')
        result_lines.append(f"{i}. **{realm_name}**")
        result_lines.append(f"   ID: {realm_id}")
        result_lines.append("")
    
    result_lines.append("💡 Use the realm ID with search_templates() to search in a specific realm.")
    
    return "\n".join(result_lines)
