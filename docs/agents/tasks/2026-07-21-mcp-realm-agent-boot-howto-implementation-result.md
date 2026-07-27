# MCP Implementation Result: `MCP-REALM-AGENT-BOOT-HOWTO-001`

## Task
- Objective: implement the approved deterministic read-only realm-agent how-to contract for list, exact identity decision, identity-and-charter, and bootstrap-prefix intents.
- Scope: `AC-001..AC-030` in the approved Change Spec, including RU/EN routing, precedence, scalar parsing, complete/incomplete/error plans, conditional stop semantics, canonical contract/guide synchronization, and regressions.
- Out of scope: backend or endpoint changes, public tool/schema additions, realm-agent F-02 verified boot-package assembly, F-03 executor launch, charter interpretation/recovery execution, authorization, fallback/compatibility behavior, independent QA, commit, push, PR, deploy, and Onto/chat writes.

## Process, Approval, And Inputs
- Canonical process source: `onto-docs/main`.
- Change Spec: `MCP-REALM-AGENT-BOOT-HOWTO-001`, status `approved`.
- Implementation handoff: `implementation_handoff_ready`; blocking `no`.
- Owner implementation-start approval: exact response `согласовано`.
- Rework authority: prior bootstrap and owner implementation approval remained valid; independent QA returned `QA FAIL` with `QA-FAIL-001`, scoped only to approved `AC-021` realm UUID continuation boundaries.
- Developer bootstrap: completed from workspace and `mcp` project instructions before application edits.
- The shared `mcp` checkout contained unrelated work and was preserved; implementation used a task-specific clean worktree.

## Locked Onto Anchor
- role: `primary_change_object`
- realm_id: `000ba00a-00a0-0a00-a000-000a0a0a0aa3`
- object_id: `6800c192-bec9-4515-8313-5c8db947fe03`
- locked: `yes`
- substitution allowed: `no`
- Developer Onto/chat/memory/milestone write performed: `no`

## Exact Local Implementation Identity
- Repository: `mcp`
- Worktree: `/home/ubuntu/git/onto/_platform/.worktrees/mcp-realm-agent-boot-howto`
- Branch: `feature/mcp-realm-agent-boot-howto`
- Baseline and current `HEAD`: `origin/main` / `13e1b7eea4066305cbd407fcb118c90df298c344`
- Implementation form: uncommitted working-tree delta from that clean baseline.
- Rework product implementation diff SHA-256: `c6a591d7491e645c4d55203a98d9344cf11f90929e7d6e17f40c016e14bef8e7` (the four product/test files below; coordination/report files excluded).
- Superseded pre-QA rework identity: `e7092a1bc50c56d12b0028ab0598eec6f026828411daf6c3cd3dbbc8fa59c51d`; independent QA recorded `QA FAIL` for that identity and it must not be reused.
- Dependency manifests are unchanged: `requirements.txt` SHA-256 `7e0b7d0021ba38c3cd5b992e134cc817441f8bd68ce7f6430bea99a2909cfc1e`; `pyproject.toml` SHA-256 `8c29705c92ba9bfeab113d1284302f5ac76c07f8e2c9d940d6a3664d536b4bc8`.

### Product And Test File Manifest
- `onto_mcp/agent_contract.py`: `1e8c50b7df123022bd3ed46ffec882ff0b6c77f17e404948b138bfe8bd2f2905`
- `onto_mcp/agent_contract.json`: `6cec9d3c877358afb1134d3fed5a6560086a01a72f9b04bb93d74231f6ee885f`
- `docs/AGENT_ENTRY_GUIDE.md`: `5bf0e99072966d8464e885d2a9d8bdaef660030dd25227209247c2b24bac9226`
- `tests/test_agent_contract.py`: `af5aeddd7b399809a5edc925660fe9f964c020b9b64faf3879820c9a3627c4e3`
- This implementation result is intentionally not self-hashed.

## Behavior Changed
- Realm-agent how-to requests now select exactly one of four approved intents after the existing explicit supported `Route:` directive: list, identity decision, identity-and-charter, or bootstrap prefix.
- Compound RU/EN evidence and deterministic precedence prevent broad words such as `agent`, `registry`, `charter`, or `boot` from selecting the route alone.
- The four-call bootstrap prefix reads accepted/current constitution and registry, validates the exact case-sensitive slug, and conditionally reads the exact charter only after `valid_active_resident` with `boot_allowed=true`.
- All other identity outcomes stop and report a blocker. Successful charter acquisition hands control to the charter-defined ordered recovery and role-zone restoration; the static how-to does not inspect or execute that continuation.
- Missing values stay on the selected route with exact `missing_args`; missing `realm_id` never adds realm discovery. Malformed UUIDs and malformed/conflicting slugs produce the approved fail-closed calls and clarifications.
- UUIDs are accepted only in canonical hyphenated shape and normalized to lowercase; safe slugs retain case. Label-specific scalar parsing does not change existing free-text extraction.
- Rework for `QA-FAIL-001`: a canonical labeled realm UUID followed by the approved ordinary English `and ...` or Russian `и ...` continuation ends exactly at the UUID. Extra suffix characters, slash/underscore tails, or a connector without continuation remain malformed and fail closed.
- Lone `artifact_path` input continues to use generic MemoryArtifact routing. No realm-agent write/search execution or public tool/schema-count change was introduced.
- Canonical JSON version marker, runtime contract, guide examples, and tests are synchronized; registered tool count remains `63`.

## Acceptance-Criteria Trace
- `AC-001..AC-006`: four route families, RU/EN intent evidence, precedence, positive gate, and exact ordered complete plans are covered by focused response assertions.
- `AC-007..AC-012`: missing realm/slug, incomplete bootstrap-prefix plans, exact clarifications, and absence of implicit realm discovery are covered.
- `AC-013..AC-018`: malformed realm UUID, empty/invalid/conflicting slug, combined-input failure, lowercase UUID normalization, and slug case preservation are covered.
- `AC-019..AC-022`: exact charter path construction, conditional purpose/stop wording, exact EN/RU realm UUID continuation boundaries and negative malformed neighbors, route precedence, read-only call set, no generic search/write, and no F-02/F-03 execution are covered.
- `AC-023..AC-026`: bootstrap-prefix completion terminology, charter-defined continuation, required-source stop semantics, and no authority claim are asserted in runtime guidance and guide text.
- `AC-027..AC-030`: contract/guide/version/tool-count consistency, realm-agent and generic MemoryArtifact regressions, compile/static checks, and full test suites pass.

## Developer Validation
- Project dependencies were installed only into `/tmp/mcp-realm-agent-boot-howto-deps` from unchanged `requirements.txt`; repository and global environments were not modified.
- Focused contract tests: `python3 -m unittest tests.test_agent_contract` with the task worktree and isolated dependencies on `PYTHONPATH` -> `42` passed.
- Realm-agent regression: `python3 -m unittest tests.test_realm_agent_tools` -> `23` passed.
- MemoryArtifact regression: `python3 -m unittest tests.test_memory_artifact_tools` -> `16` passed.
- Full unittest discovery: `python3 -m unittest discover -s tests -p "test_*.py"` -> `126` passed.
- Full pytest: `pytest` -> `126` passed, `115` subtests passed.
- JSON parsing: `python3 -m json.tool onto_mcp/agent_contract.json` -> passed.
- Compile: isolated-cache `python3 -m compileall -q onto_mcp` -> passed.
- Ruff on touched Python files -> passed.
- `git diff --check` -> passed.

## Validation Notes And Residual Risks
- Independent QA on the superseded identity returned `QA FAIL` for `QA-FAIL-001`: canonical labeled UUIDs consumed trailing `and report result` / `и сообщи результат`. The narrow rework adds the exact scalar boundary and positive/negative regressions; fresh independent Re-QA is required for the new identity.
- An initial full unittest invocation used an incomplete `PYTHONPATH`; the schema-transport subprocess could not import the checkout. Re-running with both the task worktree and isolated dependency directory passed the full suite.
- Running the realm-agent and MemoryArtifact modules together in one unittest process exposed their existing test-level `requests` stub contamination. Each required regression module passed in isolation, and both complete discovery runners passed.
- Black `--check` would reformat both touched Python files, but it reports the same two files on the exact clean baseline. No broad mechanical formatting delta was introduced.
- No live MCP/backend call, remote smoke, or independent Re-QA was run by this developer. Re-QA remains pending on the owner-authorized isolated local worktree containing this exact rework identity.

## Scope And Delivery Confirmation
- No backend edit, endpoint/tool addition, public schema/count change, persistence, migration, authorization override, fallback, backward compatibility, dual-shape handling, transitional adapter, alternate endpoint, tolerant parser, legacy path, lifecycle change, or new solution path was introduced.
- Delivery state: `rework implemented locally, not committed, not pushed, not deployed`.
- Lifecycle state: `rework_implementation_reported`; `backend_reqa_pending`.
- Exact currently valid verification environment: the local isolated worktree and dependency directory only; no preprod or production URL is valid for this implementation.

## Handoff
- Orchestrator should verify this exact rework identity, record `rework_implementation_reported`, and route fresh independent Re-QA through the updated QA contract handoff against the owner-authorized isolated local worktree.
- Any implementation-bearing change requires refreshed validation and identity evidence before QA.

## Re-QA And Delivery Authorization Update
- Independent Re-QA result: `QA PASS` at `2026-07-22T00:31:56Z` for exact product diff `c6a591d7491e645c4d55203a98d9344cf11f90929e7d6e17f40c016e14bef8e7`; all four pinned file hashes matched and `QA-FAIL-001` is closed.
- Owner delivery authorization: exact response `Коммит пуш`; commit and push only for the Re-QA-passed identity.
- Explicitly unauthorized: PR, deploy, rebase, merge, unrelated history change, and Onto/object-chat write.
- Product/test identity after this evidence update: unchanged.

## Commit Description (English)
- Short commit description: `Implement realm-agent bootstrap-prefix guidance`
