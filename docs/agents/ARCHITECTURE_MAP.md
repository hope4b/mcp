# Architecture Map

## Top-Level Layout
- `onto_mcp/`: core MCP server package, auth/session logic, settings, and tool/resource implementations.
- `dev-scripts/`: local development helpers and one-off support scripts.
- `scripts/`: repository scripts for setup or operational tasks.
- `README.md`: operator-facing usage and setup documentation.
- `pyproject.toml`: package metadata and pytest configuration.
- `docker-compose.yml` and `Dockerfile`: containerized runtime entrypoints.

## Feature Areas
- Authentication and session persistence: Keycloak login, token refresh, token storage, HTTP session-state support.
- MCP surface: tool/resource registration and user-facing integration entrypoints.
- Onto search and mutation flows: realms, templates, objects, entities, and template creation.
- Runtime configuration: environment-driven settings for transport, endpoints, and secrets.

## Risk Zones
- `onto_mcp/token_storage.py`: persistent credential handling and migration risk.
- `onto_mcp/keycloak_auth.py`: auth flow correctness and token lifecycle edge cases.
- `onto_mcp/resources.py`: large multi-responsibility module with broad behavioral blast radius.
- `onto_mcp/session_state_client.py`: HTTP transport session persistence and external API coupling.
- `onto_mcp/settings.py`: misconfiguration can break auth, routing, or environment compatibility.

## Ownership Hints
- Feature: `onto_mcp/resources.py`, `onto_mcp/server.py`, `README.md`
- Data/API: `onto_mcp/auth.py`, `onto_mcp/keycloak_auth.py`, `onto_mcp/session_state_client.py`, `onto_mcp/token_storage.py`
- Platform: `pyproject.toml`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `onto_mcp/settings.py`
