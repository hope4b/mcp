# MCP Implementation Result: `MEMART-PROPOSED-SUCCESSOR-001`

## Task
- Short objective: expose the approved reviewable replace-mode MemoryArtifact successor intent through the existing MCP draft/review lifecycle.
- Scope: MCP portions of `TB-001`, `TB-011..TB-014`, `AC-004`, and `AC-019..AC-023` that are provable by developer-level wrapper/schema/guidance tests.
- Out of scope: backend changes, new tools/endpoints, fallback or compatibility behavior, client-side lifecycle emulation, independent QA, live mutation, commit, push, PR, deploy, and Onto/memory/milestone writes.

## Process, Approval, And Inputs
- Process source: `onto-docs/main` at `835f7e105f141ee51b2dc09df24732f3921e7bab`.
- Change Spec: `MEMART-PROPOSED-SUCCESSOR-001`, approved at `2026-07-21T18:41:37Z`.
- Owner implementation-start approval: `2026-07-21T18:57:35Z`.
- Owner delivery directive: `Деплой на препрод бекенда и mcp без QA`; backend and MCP independent QA are deferred for preprod only, production remains forbidden.
- MCP handoff verdict: `implementation_handoff_ready`, blocking `no`.
- Backend implementation report used: `/home/ubuntu/git/onto/_platform/.worktrees/memart-proposed-successor-backend/docs/agents/tasks/2026-07-21-memory-artifact-proposed-successor-backend-implementation-result.md`.
- Backend reported identity: branch `feature/memart-proposed-successor-backend`, baseline/HEAD `55396217f5efd48c981ed33fe1bac7f219b9a85e`, uncommitted implementation-bearing diff `dddb6f25f7ddbeaf5013a810c51fde886cb1c87805dd966df33956559a01a307`; backend QA remains `QA BLOCKED` and owner-deferred for preprod only.

## Locked Onto Anchor
- role: `primary_change_object`
- realm_id: `000ba00a-00a0-0a00-a000-000a0a0a0aa3`
- object_id: `dbef27c8-e978-4fb5-a3de-f0952b6ed3b1`
- object_code: `unknown`
- locked: `yes`
- substitution allowed: `no`
- Developer Onto/memory/milestone write performed: `no`

## Exact Local Implementation Identity
- Repository: `mcp`
- Worktree: `/home/ubuntu/git/onto/_platform/.worktrees/memart-proposed-successor-mcp`
- Branch: `feature/memart-proposed-successor-mcp`
- Fresh fetched baseline and current `HEAD`: `origin/main` / `37a21419fc2bb56f7333c89eacddeefa30ddb5d0`
- Implementation form: uncommitted working-tree delta from that baseline.
- Implementation-bearing diff SHA-256: `b2dc5e00acb047c45c183cddd4c80f36e1bf1f22d5287fb219c85565325b1fdd` (runtime, canonical contract/guidance/catalog/decision, and focused tests; coordination log/handoff/report excluded).
- Dependency manifests were unchanged: `requirements.txt` SHA-256 `7e0b7d0021ba38c3cd5b992e134cc817441f8bd68ce7f6430bea99a2909cfc1e`; `pyproject.toml` SHA-256 `8c29705c92ba9bfeab113d1284302f5ac76c07f8e2c9d940d6a3664d536b4bc8`.

### Implementation File Manifest
- `onto_mcp/api_resources.py`: `bd9bcc0e6208092c09aa8c6fd6b8582d62910f6434b290ae0fc700e6d0f2d373`
- `onto_mcp/agent_contract.py`: `c772e961d5cec7c90cc0e635f0bdf8c16d11add6db26ca5ef6e76260a252bcb6`
- `onto_mcp/agent_contract.json`: `d3f5bff950368dba103064ab1f1b392f2aad6e2b4a1aa758fbdcf0b4c577400a`
- `docs/AGENT_ENTRY_GUIDE.md`: `1e16f032cc04fae6fc83a5f2307ccca910005796027e9c02a9eade4d1faac600`
- `docs/income/QA_MCP_TOOL_CATALOG.md`: `aaa0dcc4de1da019047af0c818409496dee4c9b2bfafa009dd6a9fc29122eaa0`
- `docs/agents/DECISIONS.md`: `9db8f852992f660ccb87f7308dcd06a12fd3af186820ba413f6e9c2207c7d620`
- `tests/test_memory_artifact_tools.py`: `6d35292f615df8e4ef88fbe881672a46a12f772e09c627a42014666acd87f484`
- `tests/test_memory_artifact_schema_transport.py`: `3f9a126870dd72c933cb137dcdda6f20f865e1ac52125ae1e40171bd4bd190ff`
- `tests/_memory_artifact_schema_transport_probe.py`: `7d4b916843f5495e023fa5d77304dc1746d9fbff13e2179ce4be409ac1792afd`
- `tests/test_agent_contract.py`: `a5bd82240c633475ec19116050fc5d8454d1a0ced1ae2cfa5b6b7221c868603a`

### Coordination File Snapshots
- `docs/agents/HANDOFF.md`: `3209612eeb216fffb30c34c765d87b2260ad7261d57282d72239c7e9a49ffcb4`
- `docs/agents/WORKLOG.md`: `74539e62418828a4c47de19ae6a0a7d4cd2b72a050a876fe5c7176304ae7b515`
- This implementation result is intentionally not self-hashed; changing it to record its own hash would change that hash.

## Behavior Changed
- `create_memory_artifact_draft` exposes optional snake_case `supersedes_artifact_id` in its MCP schema.
- A supplied value is normalized with the existing UUID convention before any backend call and is mapped only into the existing draft-create payload and endpoint.
- Omission leaves the field absent, preserving ordinary draft behavior.
- Submit, accept, revoke, update, append, and direct supersede wrappers/routes/bodies were not changed.
- The runtime agent contract carries the exact predecessor into draft creation, then routes exact-id draft read, submit, accept, and accepted path/search readback; it explicitly forbids substituting direct supersede.
- Canonical JSON, Agent Entry Guide, and QA catalog now describe the same successor path while preserving the ordinary draft path.

## Contract Trace
- `TB-001`, `TB-011`: optional field, UUID pre-validation, exact draft endpoint/payload mapping, and omission regression are covered.
- `TB-012`: direct supersede remains a distinct unchanged operation; existing route/body regression remains green.
- `TB-014`, `AC-023`: runtime routing passes the exact predecessor through create, preserves `create -> read -> submit -> accept -> accepted readback`, and excludes direct supersede; ordinary create parameters omit the field.
- `AC-019..AC-020`: dedicated route and invalid-input no-call evidence pass; existing backend error/lifecycle wrapper regressions pass.
- `AC-021..AC-022`: not claimed. Backend QA is historically blocked and owner-deferred for preprod, and no independent/live MCP QA was run.

## Developer Validation
- Plain `python -m unittest ...`: not available because the shell has no `python` executable.
- Initial `python3` focused run without dependencies: blocked by missing `pydantic`; no product failure.
- Project dependencies installed only into `/tmp/memart-proposed-successor-mcp-deps` from unchanged `requirements.txt`; repository/global environment was not modified.
- Focused unittest: `PYTHONPATH=<worktree>:/tmp/memart-proposed-successor-mcp-deps python3 -m unittest tests.test_memory_artifact_tools tests.test_memory_artifact_schema_transport tests.test_agent_contract` -> `50` passed.
- Full unittest: `PYTHONPATH=<worktree>:/tmp/memart-proposed-successor-mcp-deps python3 -m unittest discover -s tests -p "test_*.py"` -> `113` passed.
- Full pytest: `PYTHONPATH=<worktree>:/tmp/memart-proposed-successor-mcp-deps python3 -m pytest tests` -> `113` passed, `97` subtests passed.
- Compile: `python3 -X pycache_prefix=/tmp/memart-proposed-successor-mcp-pycache -m compileall onto_mcp` with isolated dependencies -> passed.
- Ruff on all touched Python files -> passed.
- `git diff --check` -> passed.

## Skipped Checks And Residual Risks
- No live backend/MCP call, mutation, authorization/conflict scenario, preprod smoke, or independent QA was run by this developer.
- The owner-accepted unverified risks remain: backend real-Neo4j concurrency/rollback, five-actor authorization, live lifecycle/audit/visibility/exclusion, exact backend environment, and real delivered MCP end-to-end behavior.
- The MCP implementation was validated against wrapper mocks and real FastMCP schema transport locally, not against a running backend.
- Preprod smoke must remain delivery evidence only and must not be relabeled QA PASS.

## Scope And Delivery Confirmation
- No backend edit, new endpoint/tool, fallback, compatibility alias/parser, dual shape, alternate spelling, transitional adapter, legacy path, client-side emulation, new solution path, migration, authorization override, or scope expansion was introduced.
- Delivery state: `implemented locally, not committed, not pushed, not deployed`.
- Lifecycle state: `implementation_reported`; next state is `preprod_delivery_pending` after Orchestrator accepts this exact identity.
- Exact verification environment currently valid: local isolated worktree and dependency directory only; no remote URL is valid for this implementation.

## Handoff
- Remaining work: Orchestrator verifies the recorded identity and separately authorizes commit/push/PR/preprod delivery of the exact checked delta; any implementation-bearing change requires renewed checks and refreshed identity.
- Independent MCP QA remains owner-deferred for this preprod delivery only; production remains blocked.

## Commit Description (English)
- Short commit description: `Add reviewable MemoryArtifact successor draft support`
