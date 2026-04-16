# Test Strategy

## Core Rules
- Run targeted tests for touched scope.
- Run full suite for cross-scope/high-risk changes.
- Record skipped checks and risks.

## Baseline Commands
- Lint: no dedicated lint command is defined in-repo; if introduced, document it here.
- Unit: `pytest`
- Build: `python -m compileall onto_mcp`

## Scope To Validation Matrix
- `onto_mcp/resources.py` -> `pytest`, targeted manual sanity of affected MCP tools if tests are absent
- `onto_mcp/keycloak_auth.py` -> `pytest`, auth flow regression checks, review secret handling paths
- `onto_mcp/token_storage.py` -> `pytest`, verify safe persistence/migration behavior
- `onto_mcp/settings.py` -> `pytest`, environment/config smoke check
- `README.md` or `docs/agents/**` -> proofread only unless commands/examples changed materially
