# Onto MCP Server

This project provides a FastMCP server for integrating with Onto platform resources through Keycloak authentication.

## Features

- 🔐 **Multiple Authentication Methods**:
  - Direct token input (`login_via_token`)
  - Username/password authentication (`login_with_credentials`)
  - OAuth 2.0 Authorization Code flow (`get_keycloak_auth_url` + `exchange_auth_code`)
  - Automatic token refresh

- 📁 **Resources**:
  - `onto://spaces` - Get user's accessible Onto realms/spaces
  - `onto://user/info` - Get current user information from Keycloak

- 🛠️ **Tools**:
  - Authentication management (login, logout, refresh, status)
  - User information retrieval

## Quick Start

1. **Install dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   ```

2. **Configure environment** (optional):
   ```bash
   cp config.example .env
   # Edit .env with your Keycloak settings
   ```

3. **Run MCP server**:
   ```bash
   # For Cursor integration (stdio mode)
   python -m onto_mcp.server
   
   # For HTTP mode
   MCP_TRANSPORT=http python -m onto_mcp.server
   ```

4. **Test authentication**:
   ```bash
   python test_keycloak_auth.py
   ```

## Authentication Methods

### Method 1: Username/Password (Recommended)
```python
# In Cursor or MCP client
login_with_credentials("your_email@example.com", "your_password")
get_auth_status()  # Verify authentication
```

### Method 2: Manual Token
```python
# Get token from browser and use directly
login_via_token("eyJhbGciOiJSUzI1NiIs...")
```

### Method 3: OAuth 2.0 Flow
```python
# Step 1: Get authorization URL
get_keycloak_auth_url("http://localhost:8080/callback")

# Step 2: Open URL in browser, login, copy 'code' parameter
# Step 3: Exchange code for token
exchange_auth_code("authorization_code_here", "http://localhost:8080/callback")
```

## Configuration

Environment variables (see `config.example`):

```bash
# Keycloak Configuration
KEYCLOAK_BASE_URL=https://app.ontonet.ru
KEYCLOAK_REALM=onto
KEYCLOAK_CLIENT_ID=frontend-prod
KEYCLOAK_CLIENT_SECRET=

# Onto API Configuration  
ONTO_API_BASE=https://app.ontonet.ru/api/v2/core

# MCP Server Configuration
MCP_TRANSPORT=stdio
PORT=8080
```

## Docker

```bash
docker compose up --build
```

## Cursor Integration

Add to your Cursor MCP configuration (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "onto-mcp-server": {
      "command": "python",
      "args": ["-m", "onto_mcp.server"],
      "cwd": "/path/to/onto/mcp",
      "env": {}
    }
  }
}
```
