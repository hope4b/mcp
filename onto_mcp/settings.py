from __future__ import annotations

"""Central configuration for Onto MCP Server.
Environment variables are provided by MCP client configuration (mcp.json).

Having a single place for configuration simplifies maintenance and eliminates 
scattered hard-coded values.
"""

import os

# ---------------------------------------------------------------------------
# Onto API configuration
# ---------------------------------------------------------------------------

ONTO_API_BASE: str = os.getenv("ONTO_API_BASE")
ONTO_API_KEY: str = os.getenv("ONTO_API_KEY", "").strip()
ONTO_API_KEY_HEADER: str = os.getenv("ONTO_API_KEY_HEADER", "X-API-Key").strip() or "X-API-Key"
ONTO_API_KEY_PASSTHROUGH_HEADER: str = (
    os.getenv("ONTO_API_KEY_PASSTHROUGH_HEADER", "X-Onto-Api-Key").strip() or "X-Onto-Api-Key"
)
SESSION_STATE_API_BASE: str = os.getenv("SESSION_STATE_API_BASE", ONTO_API_BASE)
SESSION_STATE_API_KEY: str = os.getenv("SESSION_STATE_API_KEY", "").strip()


# ---------------------------------------------------------------------------
# MCP server runtime configuration
# ---------------------------------------------------------------------------

MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio")  # Keep default for transport
PORT: int = int(os.getenv("PORT", "8080"))  # Keep default for port

# Convenience flag
IS_HTTP_TRANSPORT: bool = MCP_TRANSPORT == "http"

def get_missing_required_settings() -> list[str]:
    """Return missing base settings required for authenticated Onto operations."""
    required_vars = [("ONTO_API_BASE", ONTO_API_BASE)]
    if not IS_HTTP_TRANSPORT:
        required_vars.append(("ONTO_API_KEY", ONTO_API_KEY))
    return [name for name, value in required_vars if not value]


def validate_runtime_settings() -> None:
    """Fail fast when the server is started with an invalid runtime configuration."""
    missing = get_missing_required_settings()
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Please set them in your mcp.json configuration."
        )

    if MCP_TRANSPORT not in {"stdio", "http"}:
        raise EnvironmentError("MCP_TRANSPORT must be 'stdio' or 'http'.")
