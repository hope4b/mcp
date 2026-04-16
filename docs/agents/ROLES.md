# Roles

## Coordinator
- Purpose: planning, sequencing, conflict prevention.
- Owns: `AGENTS.md`, `docs/agents/**`.

## Feature Agent
- Purpose: MCP tool behavior, tool descriptions, user-visible auth/search flows.
- Owns: `onto_mcp/resources.py`, `onto_mcp/server.py`, `README.md`.

## Data/API Agent
- Purpose: Onto API contracts, Keycloak flows, data retrieval and mutation semantics.
- Owns: `onto_mcp/auth.py`, `onto_mcp/keycloak_auth.py`, `onto_mcp/session_state_client.py`, `onto_mcp/token_storage.py`.

## Platform/Infra Agent
- Purpose: configuration, packaging, runtime settings, Docker and environment integration.
- Owns: `pyproject.toml`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `onto_mcp/settings.py`, `sitecustomize.py`.

## QA/Reviewer Agent
- Purpose: regression/risk checks.
- Owns: tests, validation commands, release confidence, and review gates.
