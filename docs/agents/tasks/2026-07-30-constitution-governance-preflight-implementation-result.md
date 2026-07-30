# Constitution Governance Preflight Implementation Result

## Task And Bootstrap

- Spec: `MCP-CONSTITUTION-GOVERNANCE-PREFLIGHT-001`.
- Role: accepted resident `mcp-owner`, `task_mode=implementation`, carrying
  Application Developer obligations for `mcp`.
- Resident evidence: `valid_active_resident`, active, valid,
  `boot_allowed=true`; accepted/current charter
  `b11f65f3-244d-40e4-88a8-2ae760af7f56`.
- Process source:
  `onto-docs/main@466d97014209b51bb6d4099d70c0f3d820c4f5ef`;
  approved spec/handoff persisted at
  `onto-docs/main@524b252ff2e2cb54b86bf0a35feba782e11c75ae`.
- Owner implementation-start evidence: exact response `Делай`.
- Approved baseline:
  `41bce29c9052065ddecd1ff2c6c3275cf6d8272f`, tree
  `7e55e95cd7158754bee486f0b142fba607791b01`.
- Branch: `feature/mcp-constitution-governance-preflight`.
- Isolated worktree:
  `/home/ubuntu/git/onto/_platform/.worktrees/mcp-constitution-governance-preflight`.
- Initial `git status --porcelain=v1`: empty.
- Shared dirty `mcp` checkout: excluded and untouched.
- Documentation realm:
  `000ba00a-00a0-0a00-a000-000a0a0a0aa3`; Onto bootstrap reads were
  read-only.
- Primary Onto anchor: none exists; milestone logging is `not_applicable`.

## Implemented Delta

- The existing read-only
  `preflight_realm_agent_governance_proposal(realm_id,
  proposal_artifact_id) -> str` now admits only exact
  `realm/agents/constitution`.
- Constitution success adds only:
  `proposal_kind="constitution"`, `charter_slug=null`, and required
  predecessor source `current_constitution` bound to the already validated
  accepted/current Constitution id.
- Frozen submit-time registry authority, exact current-Constitution read,
  stable captured-registry resident-charter reads, exact UTF-8 hashing,
  existing framing/bounds/errors and all charter/registry paths remain intact.
- Empty Constitution body stops after the two exact-id reads and captured
  registry temporal proof, before hash/current-governance reads, with the
  approved retained/null projection.
- Malformed predecessor stops after one proposal read. Null or unequal
  canonical predecessor stops only after hashing and complete governance
  validation with the approved late projection and ledger.
- Runtime description, Agent Contract and human guidance now say
  Constitution/charter/registry. Tool name, marker, registration, schema,
  tool count and safety classification did not change.

## Changed-File Manifest And SHA-256

| File | SHA-256 |
|---|---|
| `MCP_SETUP.md` | `64d1923786b041210df2cab0c2493f22116506399154023f85477ca3dff46ad2` |
| `README.md` | `77145b336488c663cd49fcc914137683a732b6642c9ac3eabdb2e8e08d50cf77` |
| `docs/AGENT_ENTRY_GUIDE.md` | `7438129ec7339f0fef24fea35ada167383d110a63787aa301a1bf74a00aca1a5` |
| `docs/income/QA_MCP_TOOL_CATALOG.md` | `9197a23e8fb38c5cf046a042378edb521db8a8a2aaa60c01397b5db687f18b3c` |
| `onto_mcp/agent_contract.json` | `80ef895ba7da0e8ec26acd0d6a05f482cadf6544a568fbbf59b4da3682f730fc` |
| `onto_mcp/agent_contract.py` | `a02b0f8e57138ea7b955378a6d95b4986ed245e106c3fa9b4351f0ce73e7f589` |
| `onto_mcp/api_resources.py` | `f90c91339e618541f7e3c022da8bc1d2edb247eae36b5c173aefea0d045cc46d` |
| `onto_mcp/realm_agents.py` | `e14509503ebe40e726d4297b49a34a4cd758b8b4e7e8ccfa361e62e695ed8c33` |
| `tests/test_agent_contract.py` | `1fea98e1185075acda8d7900a98fd46b1546328432187fc5f14f84654ffefe91` |
| `tests/test_realm_agent_governance_preflight.py` | `a8527aa52e31e50611534a01b18a892dc5ebda84b7217a639318b50f5f84e2b5` |

The result plus required HANDOFF/WORKLOG entries are process evidence. No
decision record was needed because no architecture or canonical process
changed.

## AC-001..AC-022 Traceability

- `AC-001..AC-003`: unchanged exact two-string schema and ordering; exact
  Constitution path plus case/prefix/suffix negatives and multi-invalid
  precedence are covered.
- `AC-004`: all seven approved literal SHA-256 values pass; empty string has
  the exact two-read pre-hash stop; whitespace-only is hashed and passes.
- `AC-005..AC-006`: success and malformed/null/unequal predecessor families
  have exact kind, predecessor, retained/null fields and request ledgers.
- `AC-007..AC-009`: missing/invalid current Constitution and existing frozen
  electorate/registry/charter failure matrices fail closed at pinned reads.
- `AC-010..AC-012`: success/failure framing, sole issues, exact ordered
  ledgers and no-later-read behavior are covered.
- `AC-013..AC-014`: all existing charter/registry, realm-agent, generic
  MemoryArtifact and Agent Contract regressions pass.
- `AC-015..AC-016`: real FastMCP in-process and stdio expose exactly `64`
  tools, one registration, exact schema and one-label/one-JSON framing; the
  registered in-process Constitution fixture passes.
- `AC-017..AC-018`: only injected exact-id/path readers were invoked by the
  registered Constitution fixture. Mutation, lifecycle, search, sheet,
  position, vote, chat/object-chat and other product-write ledgers are empty;
  existing dependency, timeout, redaction, cancellation and bounds tests pass.
- `AC-019..AC-020`: no backend/public-dependency/auth/fallback change and only
  the approved minimal implementation/test/guidance surface changed.
- `AC-021`: remains `backend_qa_pending`; developer evidence is not a QA
  verdict. The Orchestrator must prepare the separately pinned QA Contract
  Handoff from the final delivery identity.
- `AC-022`: not executed. Production deploy/probe require later QA and
  separate delivery authority.

## Developer Validation

Environment: local isolated Docker runtime
`onto-mcp-reqa-python311:local`; Python `3.11.15`, FastMCP `3.4.4`,
Pydantic `2.13.4`, pytest `9.1.1`.

- Governance unittest: `28` passed.
- Agent Contract unittest: `44` passed.
- Realm-agent/MemoryArtifact/Agent Contract regressions: `83` passed.
- Full unittest discovery with `PYTHONPATH=/app`: `156` passed.
- Full pytest with `PYTHONPATH=/app`: `156` passed.
- Compileall, Agent Contract JSON and `git diff --check`: passed.
- Project-image Ruff `0.15.22` on the five approved Python surfaces: zero.
- Fixed Ruff `0.16.0` unrestricted comparison on the same files:
  baseline `33`, current `33`; normalized
  `(relative path, code, message)` multisets are equal with no addition or
  removal. The unchanged baseline findings keep exit `1`; no ignore,
  suppression, config or unrelated cleanup was added.

The first system-Python attempt stopped before tests because Python `3.14.4`
lacked `pydantic`. An initial Docker full-suite attempt without
`PYTHONPATH=/app` reached `151` tests and failed only when an existing
subprocess probe could not import the checkout. Supplying the project path
made both complete suites pass `156`. Neither environment error changed
product state.

## Real FastMCP Evidence

- In-process and stdio each list `64` tools and exactly one preflight.
- Both schemas require exactly `realm_id` and `proposal_artifact_id`, both
  strings, with `additionalProperties=false`.
- Agent Contract marker remains
  `2026-07-26.realm-agent-governance-preflight`.
- Registered invalid input returns one label/one JSON and sole
  `realm_id_invalid`.
- Registered in-process Constitution fixture returns `pass`, kind
  `constitution`, source `current_constitution`, and exact hash
  `b1f7989bf4a3feee87aaf841d3c94385337f12cdbf356e0db33f68edfe535f16`.
- Exact ledger: proposal id, captured registry id, accepted/current
  Constitution path, accepted/current Steward charter. No current-registry
  path, duplicate Constitution read, search, write or network fallback.
- Stdio uses only the invalid-input fixture because process-local transport
  patching cannot cross the child boundary. No live backend/realm substitute
  was created.

## Boundaries And Status

- Backend semantic fit remains `no_change`; no backend object, link, schema,
  persistence, identifier, naming, API, authorization or migration changed.
- No fallback, compatibility, dual shape, adapter, tolerant parser, alias,
  alternate endpoint/tool/path, direct HTTP or new issue/status/dependency.
- No independent QA, merge, push, deploy, production probe, realm mutation,
  proposal, sheet, position, vote, accept, supersede or Article 9 occurred.
- Implementation commit:
  `41c898e297f85f012a419633d23f7464c697d12f`, tree
  `0b27715b3f9d8b20a754919e911130d11fb9a70b`.
- Baseline-to-implementation binary diff SHA-256:
  `6df0ddc54835e2b2c9c4639a648b56ecdbc2493f247c4ea6ec2db8d05cb97bc6`.
- Final evidence commit: reported externally because it contains this
  implementation-identity read-back.
- State: `committed`, not pushed, `backend_qa_pending`, not deployed.
- Evidence is valid only in the named local isolated worktree/Docker runtime.

## Handoff

- Next owner: Orchestrator.
- Next gate: pin the exact final evidence identity and prepare the separate
  exact-identity Backend QA Contract Handoff.
- Push, independent QA, merge, deploy, production probe and Article 9 remain
  outside this implementation run.

## Commit Description (English)

- Add Constitution governance proposal preflight
