# Accepted Change Spec implementation

## Task
- Short objective: Preserve invocation ContextVars across the clone deadline worker so result lookup can authenticate using the invoking caller's API key or OAuth authority.
- Scope: repository `mcp`; the accepted files and changes below.
- Out of scope: changes outside the accepted specification; merge and deployment.

## Context Used
- AGENTS.md read: yes
- PROJECT_CONTEXT.md read: yes
- ARCHITECTURE_MAP.md read: yes
- Task: https://internal.ontonet.ru/ru/context/000ba00a-00a0-0a00-a000-000a0a0a0aa3/entity/241fda0f-e437-4306-9fa3-2adb76ecfd31
- Accepted Change Spec: `d65bedbd-bc3c-4a6d-89cf-ab281798f83d`

## Changes
- Files changed:
  - `onto_mcp/realm_object_clone.py`
  - `tests/test_http_onto_api_key_passthrough.py`
  - `docs/agents/tasks/defect-d65bedbd-bc3c-4a6d-89cf-ab281798f83d.md`
- Behavioral impact (accepted changes):
  - `onto_mcp/realm_object_clone.py`: Capture contextvars.copy_context() in the invoking thread for every deadline-helper invocation, then execute the existing worker through that captured context's run method. Allocate a fresh context per invocation and retain the existing worker body, deadline calculation, exception forwarding, and request-attempt behavior.
  - `tests/test_http_onto_api_key_passthrough.py`: Add regression coverage for the six unchanged acceptance criteria: canonical HTTP API-key and OAuth authentication through the real deadline helper, overlapping caller isolation and missing-authentication isolation, existing typed found/not-found results, existing exception and timeout behavior, and unchanged request counts with no automatic write retries. Use the real canonical authentication sender with controlled Core responses.
- Risks (accepted specification):
  - Medium risk according to the supplied expertise: this changes worker execution context on an authentication-sensitive path.
  - Reusing a captured Context across concurrent calls would undermine isolation; each helper invocation must capture its own context.
  - The supplied source diagnosis does not establish which deployed images contain the defect.

## Validation
- Commands run:
  - `/usr/bin/env FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=/home/ubuntu/git/onto/_platform/agent-runtime/.runtime/mcp-defect-attempts/d65bedbd-bc3c-4a6d-89cf-ab281798f83d/60158348-3537-4c3e-bedc-aa22c8f7f7ee/feature-worktrees/d65bedbd-bc3c-4a6d-89cf-ab281798f83d/mcp /home/ubuntu/git/onto/_platform/qa/mcp-feature-venv/bin/python -m compileall -q onto_mcp`
  - `/usr/bin/env FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=/home/ubuntu/git/onto/_platform/agent-runtime/.runtime/mcp-defect-attempts/d65bedbd-bc3c-4a6d-89cf-ab281798f83d/60158348-3537-4c3e-bedc-aa22c8f7f7ee/feature-worktrees/d65bedbd-bc3c-4a6d-89cf-ab281798f83d/mcp /home/ubuntu/git/onto/_platform/qa/mcp-feature-venv/bin/python -m pytest --ignore=tests/test_oauth_keycloak24_integration.py --ignore=tests/test_oauth_state_mongo_integration.py --junitxml=/home/ubuntu/git/onto/_platform/agent-runtime/.runtime/mcp-defect-attempts/d65bedbd-bc3c-4a6d-89cf-ab281798f83d/60158348-3537-4c3e-bedc-aa22c8f7f7ee/pytest-evidence/pytest-5hurtbel/results.xml`
- Result:
  - `/usr/bin/env FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=/home/ubuntu/git/onto/_platform/agent-runtime/.runtime/mcp-defect-attempts/d65bedbd-bc3c-4a6d-89cf-ab281798f83d/60158348-3537-4c3e-bedc-aa22c8f7f7ee/feature-worktrees/d65bedbd-bc3c-4a6d-89cf-ab281798f83d/mcp /home/ubuntu/git/onto/_platform/qa/mcp-feature-venv/bin/python -m compileall -q onto_mcp`: exit code 0; output SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - `/usr/bin/env FASTMCP_CHECK_FOR_UPDATES=off PYTHONPATH=/home/ubuntu/git/onto/_platform/agent-runtime/.runtime/mcp-defect-attempts/d65bedbd-bc3c-4a6d-89cf-ab281798f83d/60158348-3537-4c3e-bedc-aa22c8f7f7ee/feature-worktrees/d65bedbd-bc3c-4a6d-89cf-ab281798f83d/mcp /home/ubuntu/git/onto/_platform/qa/mcp-feature-venv/bin/python -m pytest --ignore=tests/test_oauth_keycloak24_integration.py --ignore=tests/test_oauth_state_mongo_integration.py --junitxml=/home/ubuntu/git/onto/_platform/agent-runtime/.runtime/mcp-defect-attempts/d65bedbd-bc3c-4a6d-89cf-ab281798f83d/60158348-3537-4c3e-bedc-aa22c8f7f7ee/pytest-evidence/pytest-5hurtbel/results.xml`: exit code 0; output SHA-256 `6f4424c9c0fd28bad7f8f5ed7ab8cba618f1742d6ca8e079041df8bcd4d07c66`
- Not run (and why): live environment verification is outside these repository checks and requires the delivery gate; no functional QA verdict is claimed.

## Commit Description (English)
- Short commit description: fix: implement d65bedbd-bc3c-4a6d-89cf-ab281798f83d (mcp)

## Handoff
- Remaining work: independent review, PR creation and separately authorized delivery verification.
- Recommended next owner (area): the controller for independent review and PR handoff.

Commit description (EN): fix: implement d65bedbd-bc3c-4a6d-89cf-ab281798f83d (mcp)
