# Architecture Map

## Top-Level Layout
- `onto_mcp/`: core MCP server package, settings, tool/resource implementations,
  agent guidance and optional session-state client.
- `dev-scripts/`: local development helpers and one-off support scripts.
- `scripts/`: repository scripts for setup or operational tasks.
- `README.md`: operator-facing usage and setup documentation.
- `pyproject.toml`: package metadata and pytest configuration.
- `docker-compose.yml` and `Dockerfile`: containerized runtime entrypoints.

## Feature Areas
- Authentication: configured API key for stdio and client-key passthrough for
  HTTP; optional session-state helper API.
- MCP surface: tool/resource registration and user-facing integration entrypoints.
- Onto search and mutation flows: realms, templates, objects, entities, and template creation.
- Runtime configuration: environment-driven settings for transport, endpoints, and secrets.

## Risk Zones
- `onto_mcp/api_resources.py`: broad tool registration and backend-contract
  mapping surface.
- `onto_mcp/agent_contract.json` and `agent_contract.py`: runtime guidance
  consistency and safe routing.
- `onto_mcp/realm_agent_admission.py` and `realm_agents.py`: high-risk resident
  governance/admission wrappers.
- `onto_mcp/session_state_client.py`: HTTP transport session persistence and external API coupling.
- `onto_mcp/settings.py`: misconfiguration can break auth, routing, or environment compatibility.

## Ownership Hints
- Tool/runtime: `onto_mcp/api_resources.py`, `onto_mcp/server.py`, `README.md`
- Guidance/governance wrappers: `onto_mcp/agent_contract.*`,
  `onto_mcp/realm_agent_admission.py`, `onto_mcp/realm_agents.py`
- API/session helper: `onto_mcp/session_state_client.py`
- Runtime configuration: `pyproject.toml`, `requirements.txt`, `Dockerfile`,
  `docker-compose.yml`, `onto_mcp/settings.py`
