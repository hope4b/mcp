# Test Strategy

## Core Rules
- Run targeted tests for touched scope.
- Run full suite for cross-scope/high-risk changes.
- Record skipped checks and risks.

## Baseline Commands
- Lint: no dedicated lint command is defined in-repo; if introduced, document it here.
- Unit: `pytest`
- Build: `python -m compileall onto_mcp`

## Live stdio MCP QA Runbook
- Default `stdio` auth baseline:
  - configure `ONTO_API_BASE`
  - configure `ONTO_API_KEY`
  - expect outbound Onto auth through `X-API-Key`
- Default preprod target:
  - `https://preprod.ontonet.ru/api/v2/core`
- Preferred validation order:
  1. run wrapper-level tests;
  2. run `compileall`;
  3. run real `stdio MCP` smoke through a real FastMCP client/server transport, not only direct Python function import;
  4. if the scenario needs controlled data, create a temporary QA realm, populate the minimum fixture, verify semantics, then delete the realm.
- On Windows in this workspace, if `fastmcp` is not importable in the active interpreter:
  - use repository-local `.deps` as an isolated runtime path;
  - prefer `site.addsitedir()` or `PYTHONPATH` rather than changing global machine state.
- If `stdio` transport fails because of sandbox pipe restrictions, rerun the live smoke outside the sandbox and keep the rest of the test method unchanged.

## Scope To Validation Matrix
- `onto_mcp/resources.py` -> `pytest`, targeted manual sanity of affected MCP tools if tests are absent
- `onto_mcp/keycloak_auth.py` -> `pytest`, auth flow regression checks, review secret handling paths
- `onto_mcp/token_storage.py` -> `pytest`, verify safe persistence/migration behavior
- `onto_mcp/settings.py` -> `pytest`, environment/config smoke check
- `README.md` or `docs/agents/**` -> proofread only unless commands/examples changed materially
