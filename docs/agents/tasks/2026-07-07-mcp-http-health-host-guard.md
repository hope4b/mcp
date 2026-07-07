# MCP HTTP Health And Host Guard Fix

## Task
- Short objective: Fix preprod MCP HTTP runtime health and `/mcp` 421 blocker after deploying `get_diagram` representation details.
- Scope: MCP HTTP startup evidence, operational `/healthz`, FastMCP allowed-host configuration, preprod deploy health probes.
- Out of scope: Prod deploy, database/backend changes, `get_diagram` feature changes, QA Gate 2 verdict, defect completion, fallback/alternate MCP endpoint/legacy path/compatibility parser work.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes
- TEST_STRATEGY.md read: yes
- HANDOFF.md / WORKLOG.md read: yes
- QA Gate 2 blocker note read: yes, `docs/agents/tasks/2026-07-06-get-diagram-representation-details-qa-gate-2.md`
- Locked Onto anchor received: yes, object `c160d7ad-22ec-4e04-8b9d-6b8f328980b3`; substitution not allowed

## Changes
- Files changed: `onto_mcp/server.py`, `onto_mcp/settings.py`, `tests/test_server_runtime.py`, `docs/agents/tasks/2026-07-07-mcp-http-health-host-guard.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md`, plus deploy config files in `/home/ubuntu/git/onto/_platform/mcp-server`.
- Behavioral impact: HTTP startup logs now include app, transport, port, MCP ref, package/runtime version, FastMCP version, and Python version. Runtime exposes `/healthz` as an operational health endpoint that returns 200 without MCP JSON-RPC negotiation or Onto API key. HTTP runtime passes configured allowed hosts/origins to FastMCP.
- Deploy impact: Preprod compose allows `preprod.ontonet.ru` through FastMCP host-origin protection, passes `MCP_REF` into the container, and uses `/healthz` for Docker health. The workflow quick local probe now uses `/healthz`.
- Root cause: FastMCP 3.4.3 enables host-origin protection by default. Default allowed hosts are loopback/local, so preprod requests with `Host: preprod.ontonet.ru` returned HTTP 421 until the host is explicitly configured.
- Risks: Preprod still needs an approved redeploy and QA Gate 2 must rerun against the deployed fix. NGINX/proxy behavior should be confirmed on preprod after deploy.
- Onto milestone: HTTP blocker-fix `implementation_reported` was written to the locked defect object chat.

## Validation
- Commands run:
  - `python3 -m unittest tests.test_server_runtime`
  - `python3 -m unittest discover -s tests -p "test_*.py"`
  - `python3 -m compileall onto_mcp`
  - `git diff --check` in `mcp`
  - `git diff --check` in `mcp-server`
  - Local HTTP probe with FastMCP 3.4.3 from `/tmp/fastmcp_probe`
- Result: Focused test passed 3 tests; full unittest discovery passed 71 tests; compileall passed; both diff checks passed. Local HTTP probe returned 200 for `/healthz`, returned 200 for MCP initialize with `Host: preprod.ontonet.ru`, and still returned 421 for an unconfigured host.
- Not run (and why): Preprod redeploy and QA Gate 2 were not run because deploy/QA require separate gates.

## Commit Description (English)
- Short commit description: Add MCP health and runtime startup evidence.
- Required for code changes: assistant final response must end with `Commit description (EN): Add MCP health and runtime startup evidence.`

## Handoff
- Remaining work: Commit/push/PR if owner approves delivery, then deploy the approved runtime/deploy refs to preprod and rerun QA Gate 2.
- Recommended next owner (area): MCP Owner for commit/PR/deploy gate, then QA for preprod runtime validation.
