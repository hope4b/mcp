# MCP Realm-Agent Discovery And Validation — Implementation Result

## Task
- Spec id: `MCP-REALM-AGENTS-001`.
- Objective: implement the approved read-only `list_realm_agents(realm_id)` and `get_realm_agent(realm_id, slug)` MCP contracts.
- Change Spec: `onto-docs/docs/agents/tasks/2026-07-18-realm-agent-discovery-mcp-change-spec.md`.
- Implementation handoff: `onto-docs/docs/agents/tasks/2026-07-19-realm-agent-discovery-mcp-implementation-handoff.md`.
- Scope: only the isolated `mcp` worktree, deterministic realm-agent validation, exact accepted/current MemoryArtifact path transport, tool registration/routing, documentation, and tests.
- Out of scope: backend, persistence, authorization, UI, gateway, server/deploy repository, governance writes, consensus, admission, boot runtime, search, candidate enumeration, compatibility, fallback, alternate endpoints, commit, push, PR, QA verdict, and deploy.
- Status: `implemented_locally`; `qa_environment_pending`; `backend_qa_pending`.

## Bootstrap, Approval, And Anchor
- MCP Application Developer bootstrap acknowledgement: accepted by the Orchestrator before implementation edits.
- Canonical process source: `onto-docs/main` at `6131720f3f81d1dd80ac2587a3313c7e869e8e33`.
- Owner implementation approval: yes, at `2026-07-19T14:42:53Z`.
- Approval evidence: `Согласовано, бери в реализацию MCP-REALM-AGENTS-001`.
- Locked Onto anchor received and preserved: realm `000ba00a-00a0-0a00-a000-000a0a0a0aa3`, object `b3964620-0bc7-4581-bf86-a482262014da`, code `MCP-REALM-AGENTS-001`; it was not searched for, replaced, or substituted.
- Onto reads/writes or object-chat milestone actions performed by this developer: none. Milestone routing remains with the Orchestrator.

## Clean Worktree And Implementation Identity
- Shared checkout preserved: yes. `/home/ubuntu/git/onto/_platform/mcp` remained on `mcp-how-to-bug-reclassification-routing` at `7a1e2b0ced2546d9930cd0a5cd410f2cb901fe8d` with its three pre-existing untracked task files unchanged.
- Isolated worktree: `/home/ubuntu/git/onto/_platform/.worktrees/mcp-realm-agents-001`.
- Branch: `feature/mcp-realm-agents-001`.
- Baseline: freshly fetched `origin/main` at `64ae4c3db599bff446c4e9e663bce63c1f8396a8`.
- Worktree `HEAD`: the same baseline SHA; implementation is an uncommitted working-tree delta.
- Runtime used for developer checks: Python `3.14.4`, FastMCP `3.4.4`, Pydantic `2.13.4`, requests `2.34.2`.
- Dependency isolation: the active interpreter initially lacked Pydantic/FastMCP. Required dependencies were installed only under `/tmp/mcp-realm-agents-deps`; no repository or global dependency declaration/environment was changed.

## Implemented Behavior

### Dedicated realm-agent read model
- Added a pure deterministic validator in `onto_mcp/realm_agents.py`.
- `list_realm_agents` reads the fixed constitution and registry paths, retains every deterministically recoverable physical registry row, validates only exact registered charter paths, returns stable one-based `row_index`, normalized resident state, per-row validity, effective fail-closed boot decisions, counts, completeness, source metadata, and closed issues.
- `get_realm_agent` validates the whole registry before resolving the exact case-sensitive slug as active, suspended, invalid, globally blocked, or not registered. Only a globally valid absent slug permits one exact derived charter probe.
- Exact canonical registry header, exact charter labels, exact path/slug/realm invariants, closed input/status/resolution/validity/state/issue/dependency vocabularies, and deterministic issue order are enforced.
- `MAX_REGISTRY_ENTRIES=32` is checked before charter fan-out. `MAX_RESULT_BYTES=65536` measures the complete UTF-8 string and replaces overflow with the approved compact same-label fail-closed result.
- Both public tools always return one `str` with exactly one tool-specific label and one JSON suffix using `schema_version="1"`.

### Accepted/current transport and stop behavior
- Added a private typed exact-path loader over only `POST /realm/{realm_id}/agent-memory/artifact/path` with payload `{"artifact_path":"<exact path>"}`.
- Exact-path `404` remains a position-sensitive domain absence. `401`, `403`, request timeout, network failure, other non-404 backend errors, invalid JSON/minimum fields, and a non-accepted status use the approved dependency classes without raw exception text.
- Existing generic MemoryArtifact public signatures, endpoint/payload behavior, labels, data blocks, redaction, and validation remain unchanged.
- The existing global tool timeout now emits the realm-agent tool's normal JSON framing and marks the timed-out execution cancelled so it cannot start later registry/charter reads.

### Discovery and documentation
- Registered both tools exactly once in a new read-only `realm_agent_discovery` family.
- `how_to_use_onto_mcp` routes realm-agent list intent only to `list_realm_agents` and exact-slug/boot intent only to `get_realm_agent`; missing values remain explicit and generic MemoryArtifact/AgentMemory/write paths are not recommended.
- Updated the generated contract version/tool count and convention-required README, setup, entry-guide, and QA catalog entries.

## Acceptance-Criteria Traceability
- `AC-001..AC-006`: active/suspended residents, unregistered charter/no-charter variants, registered charter `404`, duplicate row retention, stable row indices, and global boot denial are covered by focused result and ordered-ledger tests.
- `AC-007..AC-010`: malformed/unparseable rows, required fields, unsupported states, every charter mismatch family, governance absence, every dependency kind, exact input codes, lowercase UUID canonicalization, unsafe slugs, and case-only mismatch are covered.
- `AC-011..AC-014`: exact endpoint/payload, source-body/audit redaction, static forbidden-path checks, and the unchanged generic MemoryArtifact regression suite pass.
- `AC-015`: registration equality, no duplicate family membership, guide markers, exclusive list/get routing, and missing arguments pass contract tests.
- `AC-016..AC-019`: one-string/one-label/one-JSON framing, closed result vocabulary, global/per-row fail-closed aggregation, and exact absent-slug `404` behavior pass.
- `AC-020..AC-022`: ordered calls/stops, invalid-path no-call, maximum `34` list and `35` absent-slug reads, both approved limits, timeout cancellation, and completeness semantics pass.

## Files Changed
- `onto_mcp/realm_agents.py` — new pure parser, validator, projection, serializer, bounds, and typed domain/dependency failures.
- `onto_mcp/api_resources.py` — private accepted/current data loader, timeout-stop seam, and two FastMCP registrations.
- `onto_mcp/agent_contract.json` — new read-only family/task/tool contracts, edges, and contract version.
- `onto_mcp/agent_contract.py` — exclusive realm-agent routing.
- `tests/test_realm_agent_tools.py` — focused AC matrix, ordered call ledgers, transport/error/boundary/limit tests.
- `tests/test_agent_contract.py` — exclusive list/get routing and missing-input tests.
- `docs/AGENT_ENTRY_GUIDE.md` — synchronized contract markers and route guidance.
- `README.md`, `MCP_SETUP.md`, `docs/income/QA_MCP_TOOL_CATALOG.md` — convention-required public tool documentation.
- `docs/agents/tasks/2026-07-19-realm-agent-discovery-mcp-implementation-result.md`, `docs/agents/WORKLOG.md`, `docs/agents/HANDOFF.md` — implementation evidence and project memory.

## Runtime/Test File Manifest
SHA-256 values for the implementation-bearing files before project-memory-only edits:

```text
2103c53fd183f3d9d88fabbf87e9625f1f314fa67c8f04585339e8327357605a  MCP_SETUP.md
7e67760c34a9e25ee42a2a06325968f1d3113256d9b1dfe67303982b74f5a35b  README.md
c3a609d31a6d9c883c0a41f779e9bf1d1c206340bfb2f70c09a07713ad8b7872  docs/AGENT_ENTRY_GUIDE.md
4ce990acf6f321d58cb5508bc6e4e66e1306fa1ef861efcd8ef27668396a2f17  docs/income/QA_MCP_TOOL_CATALOG.md
00a6631bcd48dcd93f0d7d7042ffadcf4605eb8cc851306e6d20120973ba1062  onto_mcp/agent_contract.json
c57c966733a7d73eeb546e13986adcf65dec4b4c81e9500ff00113b1e59b74fc  onto_mcp/agent_contract.py
ecf7d29f4df1aadabf307ba85c477a7edaaff12dcec4ccc73a83a4597ca2236e  onto_mcp/api_resources.py
589725ee2137330cfb7e9066ab0af4852bda38eb8d412855cb52312b9173ab95  onto_mcp/realm_agents.py
3cf4c0b155529ffdc5a5f5e713eafee9920b0f3ff19ed4dab75b55f95c3a0dbf  tests/test_agent_contract.py
f5fd7c4abe10d52ba642ee757664d0f3a6b10c443d1d7dead50192c12d37fcff  tests/test_realm_agent_tools.py
```

## Validation
- `PYTHONPATH=.:/tmp/mcp-realm-agents-deps python3 -m unittest tests.test_realm_agent_tools` — passed, `23` tests.
- `PYTHONPATH=.:/tmp/mcp-realm-agents-deps python3 -m unittest tests.test_agent_contract tests.test_memory_artifact_tools` — passed, `42` tests.
- `PYTHONPATH=.:/tmp/mcp-realm-agents-deps python3 -m unittest discover -s tests -p 'test_*.py'` — passed, `109` tests.
- `PYTHONPATH=.:/tmp/mcp-realm-agents-deps python3 -m compileall -q onto_mcp` — passed.
- `/tmp/mcp-realm-agents-ruff/bin/ruff check ...` for every touched Python file — passed.
- `python3 -m json.tool onto_mcp/agent_contract.json` — passed.
- `git diff --check` plus `git diff --no-index --check` for the three new files — passed after final project-memory edits; each new-file check produced zero whitespace diagnostics.
- Static AST/token allowlist check — passed: new tools have no search, AgentMemory-record, ordinary Onto, object-chat, Git/filesystem, mutation, fallback, alternate endpoint, legacy path, or `agent_principal` runtime call path.
- Real FastMCP in-memory `tools/list`/`tools/call` developer smoke — passed: exact schemas require `realm_id` and `realm_id+slug`; both invalid-input calls returned non-error tool results with exactly one approved label and `governance_status=input_error` JSON.
- Optional Black check across all touched Python files reported that pre-existing tracked modules/tests are not globally Black-formatted. Only the two new Python files were formatted and then passed Black; no broad baseline reformat was applied.

## Initial Environment Limitations And Resolutions
- The first focused command stopped at import with `ModuleNotFoundError: pydantic` in the active bare Python environment. Pydantic and then the repository-declared FastMCP/runtime dependencies were installed to the isolated `/tmp` target; the required commands were rerun successfully.
- The first full-suite subprocess probe also required the worktree root in `PYTHONPATH`; the final commands use `PYTHONPATH=.:/tmp/mcp-realm-agents-deps`, after which the complete suite passed.
- No weaker test was substituted and no failed required check remains.

## Forbidden-Path And Compatibility Confirmation
- No fallback, backward compatibility, dual response shape, dual/tolerant parser, transitional adapter, alternate/old endpoint, legacy path, alias, fuzzy matching, pagination, batch read, cache-as-authorization, silent normalization, silent truncation, or partial completeness was introduced.
- No `a4b-core`, `a4b-webui`, `ext-api-gw`, `mcp-server`, backend endpoint, persistence, authorization, deployment, governance artifact, ordinary Onto object, AgentMemory record, or object-chat behavior was changed.
- No secrets, API keys, headers, source artifact bodies, append entries, audit bodies, or raw backend exceptions are included in outputs or evidence.

## Risks And Remaining Work
- Strict Markdown parsing intentionally fails closed if accepted governance formatting drifts.
- Registered-charter reads remain linear but bounded at `32`; no concurrency, retry, batch, cache, or partial-success behavior was added.
- Independent backend QA completed against the exact pinned implementation identity with `QA PASS with notes`, `Blocking: no`.
- The only QA note is that the optional live accepted/current Platform Onto smoke was not run because explicit endpoint/credential prerequisites were absent. The owner explicitly accepted this non-blocking note.

## Independent QA And Delivery Authorization
- QA result: `/home/ubuntu/git/onto/_platform/onto-docs/docs/agents/tasks/2026-07-19-realm-agent-discovery-mcp-qa-result.md`.
- QA verdict: `QA PASS with notes`; blocking findings: none.
- QA identity: baseline/HEAD `64ae4c3db599bff446c4e9e663bce63c1f8396a8`, tracked implementation diff SHA-256 `62f9f33bed6dbcf2012fa1c931cf1858104517bb7ab73efbe6c2b9713f7257d4`, and the ten-file manifest in this result all matched before and after QA.
- QA evidence: focused `23/23`, contract plus generic MemoryArtifact `42/42`, full unittest `109/109`, real FastMCP in-process and QA-owned stdio protocol checks, call ceilings, bounds, timeout cancellation, and static scope checks passed.
- Owner note acceptance and delivery authorization: `2026-07-19T17:41:22Z`, exact evidence `QA-примечание принимаю. Разрешаю commit, push и PR для MCP-REALM-AGENTS-001. Deploy не запускать.`
- Authorized delivery scope: commit the exact QA-tested MCP delta, push `feature/mcp-realm-agents-001`, and open a PR to `hope4b/mcp:main`.
- Explicit prohibition: do not deploy to preprod or production and do not perform Onto/object-chat/MemoryArtifact writes.

## Delivery Status
- Implementation: implemented locally and independently QA-passed with the non-blocking note accepted by the owner.
- Commit/push/PR: explicitly authorized for the exact pinned identity. This file is prepared as part of that delivery unit; immutable commit and PR identifiers are reported by the delivery agent after creation.
- Deploy/preprod/prod: explicitly forbidden by the owner; not requested and not deployed.
- Onto writes: forbidden for this delivery role and not performed.

## Handoff
- Delivery agent: commit only the exact `MCP-REALM-AGENTS-001` files, push `feature/mcp-realm-agents-001`, and open the authorized PR against `main`.
- After PR creation: return immutable commit/push/PR evidence to the Orchestrator. Deploy remains prohibited and requires a separate future owner gate.

## Commit Description (English)
- Short commit description: Add fail-closed MCP realm-agent discovery tools.
