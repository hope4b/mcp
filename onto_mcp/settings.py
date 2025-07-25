from __future__ import annotations

"""Central configuration for Onto MCP Server.
This module loads environment variables (including support for .env + Ansible Vault)
and exposes typed constants that other modules can import.

Having a single place for defaults simplifies maintenance and eliminates scattered
hard-coded values.
"""

import os

# Simple .env file loading
def _load_env_file(env_file: str = '.env') -> None:
    """Load environment variables from .env file if it exists."""
    try:
        # Try different encodings to handle Windows files
        for encoding in ['utf-8-sig', 'utf-8', 'utf-16', 'cp1252']:
            try:
                with open(env_file, 'r', encoding=encoding) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key, value = key.strip(), value.strip()
                            # Only set if not already in environment
                            if key not in os.environ:
                                os.environ[key] = value
                break
            except UnicodeDecodeError:
                continue
        else:
            # If all encodings fail, try binary mode and decode manually
            with open(env_file, 'rb') as f:
                content = f.read().decode('utf-8', errors='ignore')
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key, value = key.strip(), value.strip()
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value
    except FileNotFoundError:
        pass  # .env file is optional

# Load .env file before reading environment variables
_load_env_file()

# ---------------------------------------------------------------------------
# Keycloak configuration
# ---------------------------------------------------------------------------

KEYCLOAK_BASE_URL: str = os.getenv("KEYCLOAK_BASE_URL")
KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM")
KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET: str = os.getenv("KEYCLOAK_CLIENT_SECRET", "")

# ---------------------------------------------------------------------------
# Onto API configuration
# ---------------------------------------------------------------------------

ONTO_API_BASE: str = os.getenv("ONTO_API_BASE")

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

# Validate required configuration variables
_required_vars = [
    ("KEYCLOAK_BASE_URL", KEYCLOAK_BASE_URL),
    ("KEYCLOAK_REALM", KEYCLOAK_REALM),
    ("KEYCLOAK_CLIENT_ID", KEYCLOAK_CLIENT_ID),
    ("ONTO_API_BASE", ONTO_API_BASE),
]

_missing = [name for name, value in _required_vars if not value]

if _missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(_missing)}. "
        f"Please set them in your .env file or mcp.json configuration."
    ) 