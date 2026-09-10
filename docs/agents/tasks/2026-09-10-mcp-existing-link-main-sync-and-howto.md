# MCP existing-link main sync and how-to implementation result

## Task
- Short objective: merge exact `mcp/main@9062e99a19032e0fcc5e48b8db8dbfaf18fee1f4` into `feat/mcp-existing-link-representation@fe27de2110f1913cecf87f1e1092e45b0c38bd94`, preserve both runtime tracts, and make the existing-link unordered-pair limit explicit in agent guidance.
- Scope: normal main merge; declared conflict resolution; canonical Agent Contract, runtime how-to answer and safety guidance, generated guide, focused regression assertions, and this task note.
- Out of scope: rebase, force-push, PR merge, deploy, dependency changes, backend behavior, client-side probes or additional backend/MCP calls, realm/subject/memory/object-chat mutation, and independent review or QA verdict.

## Context Used
- AGENTS.md read: yes, exact feature ref from manifest.
- PROJECT_CONTEXT.md read: yes, exact feature ref from manifest.
- ARCHITECTURE_MAP.md read: yes, exact feature ref from manifest.
- Additional bootstrap: `docs/agents/ROLES.md`, `docs/agents/TEST_STRATEGY.md`, live accepted/current realm governance, MCP Owner bootstrap, task-manifest contract, and runtime receiver kernel.
- Manifest: `2026-09-10-mcp-existing-link-main-sync-and-howto-v3` at `onto-docs/docs/mcp-existing-link-representation-spec@034749a948fb4d7a73eb346c1fa3342a9bfaa5a0`.
- Process source: `onto-docs/main@8ef5d21cdb3844c3410caaf953e73c44784e3b10`.

## Changes
- Normal merge commit: `c3f0380` with parents feature `fe27de2110f1913cecf87f1e1092e45b0c38bd94` and main `9062e99a19032e0fcc5e48b8db8dbfaf18fee1f4`.
- Merge conflict resolution: preserved the feature's existing-link representation contract/tests and main's `about_realm`/realm-declaration contract/tests. All main-only files and feature-only files remain present.
- Canonical merged tool count: 67; contract and guide markers/count assertions are aligned.
- Existing-link rule: at most one link total may exist between the same unordered pair of represented objects. An existing A-to-B link forbids another A-to-B link and also a B-to-A link, regardless of relation type.
- Runtime behavior: guidance still routes exactly one `create_existing_link_representation` call with the five existing flat inputs. No probe, pre-read, client-side duplicate check, second MCP call, or backend change was added.
- Files changed after the merge: `onto_mcp/agent_contract.py`, `onto_mcp/agent_contract.json`, `docs/AGENT_ENTRY_GUIDE.md`, `tests/test_agent_contract.py`, and this note.
- Risk: the developer environment lacks the declared runtime dependency `pydantic`, so pytest collection could not execute. Static contract/runtime/guide checks and compilation pass, but independent review and QA remain required.

## Validation
- `python3 -m pytest tests/test_create_existing_link_representation.py tests/test_agent_contract.py tests/test_realm_declaration.py tests/test_server_runtime.py tests/test_realm_agent_admission_schema_transport.py`: blocked during collection because `pydantic` is not installed; 5 items collected and 4 modules errored before tests ran.
- `python3 -m pytest`: blocked during collection because `pydantic` is not installed; 16 items collected and 18 modules errored before tests ran.
- Dependency installation was not attempted because dependency mutation is outside this manifest.
- `python3 -m compileall onto_mcp`: passed.
- `python3 -m json.tool onto_mcp/agent_contract.json`: passed.
- Static canonical registration/family/guide-marker check: passed; 67 unique registered, contract, and family tools agree.
- Focused runtime guidance check: passed; exact write-intent prompt routes one call and the unordered-pair rule appears in the runtime answer, safety notes, JSON review notes, and generated guide.
- `git diff --check`: passed.
- Final ancestry, ahead/behind, clean-tree, commit and push evidence: recorded in the handoff after the implementation commit.

## Commit Description (English)
- Short commit description: Clarify the unordered-pair limit for existing-link representations.

## Handoff
- Remaining work: independent review is required before any future deploy. Pytest must be rerun in an environment with the repository's declared dependencies; no QA or deploy verdict is claimed here.
- Recommended next owner (area): `orchestrator` for routing independent review/QA.
