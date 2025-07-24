from __future__ import annotations

import os
from fastmcp import FastMCP
import requests
from .auth import get_token

mcp = FastMCP(name="Onto MCP Server")

ONTO_API_BASE = os.getenv("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

@mcp.tool
def login_via_token(token: str) -> str:
    """Store user's personal Onto access-token."""
    from .auth import set_token
    set_token(token)
    return "Token stored successfully"

@mcp.resource("onto://spaces")
def get_user_spaces() -> list[dict]:
    """Return the list of Onto realms (spaces) visible to the authorised user."""
    url = f"{ONTO_API_BASE}/user/v2/current"
    token = get_token()
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
