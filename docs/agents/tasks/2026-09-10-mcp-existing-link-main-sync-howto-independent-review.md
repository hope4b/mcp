# MCP existing-link main sync and how-to independent review

## Task
- Short objective: independently review merge commit `c3f03809be7808432caff151705c8c32fcd9190b` and implementation commit `842b611e08a4579b25bf89e605600d34e745ac80` for main ancestry, tract preservation, canonical tool alignment, existing-link guidance semantics, and one-call/no-probe behavior.
- Scope: review-only graph and scoped-diff inspection, static contract/runtime/guide checks, available focused tests without dependency mutation, compilation, JSON validation, and this review artifact.
- Out of scope: runtime or test edits, PR merge, deploy, QA, dependency installation, and realm, subject, memory, or object-chat mutation.

## Context Used
- Resident role: accepted/current `mcp-owner`; governance validation returned `valid_active_resident`, `boot_allowed=true`.
- Manifest: `2026-09-10-mcp-existing-link-main-sync-howto-review-v1` at `onto-docs/docs/mcp-existing-link-representation-spec@ec2834f7b9711c2a75cdadf7515a2feebe9122c3`.
- Process source: `onto-docs/main@8ef5d21cdb3844c3410caaf953e73c44784e3b10`.
- Runtime target: `mcp/feat/mcp-existing-link-representation@842b611e08a4579b25bf89e605600d34e745ac80` with clean pre-review worktree.
- All 11 manifest bootstrap/input files matched their declared byte lengths and SHA-256 hashes; aggregate input size was exactly 243,848 bytes.

## Findings
- No blocking findings.
- Graph gate passed: `842b611e08a4579b25bf89e605600d34e745ac80` has sole parent `c3f03809be7808432caff151705c8c32fcd9190b`; that merge has feature parent `fe27de2110f1913cecf87f1e1092e45b0c38bd94` and exact main parent `9062e99a19032e0fcc5e48b8db8dbfaf18fee1f4`. Exact main is a full ancestor of the reviewed target.
- Merge preservation passed. Main's `about_realm`/realm-declaration implementation, contract, guide, tests, and main-only files remain present, while the feature's existing-link tool, contract route, guide entry, and focused test file remain present. Combined-diff inspection showed the shared-file resolutions retain both tracts; neither parent contributed a deleted file.
- Canonical alignment passed: `onto_mcp/api_resources.py` contains 67 unique `@mcp.tool` registrations; `tool_contract` contains 67 entries; tool families contain 67 unique entries; all three name sets are equal; and the generated guide marker is 67.
- The unordered-pair rule is explicit and aligned in the canonical JSON purpose/review notes, runtime answer, runtime safety note, generated guide, and regression assertions: at most one link total may exist between the same unordered pair of represented objects, so an existing A-to-B link forbids another A-to-B and B-to-A link regardless of relation type.
- One-call/no-probe behavior passed static and direct guidance checks. With all five exact flat inputs and `write_intent`, runtime guidance emits exactly one `create_existing_link_representation` call with only those inputs. The tool implementation performs one `_request_json` POST to the canonical `/representation/link/existing` endpoint and contains no pre-read, duplicate probe, alternate endpoint, relation-creation call, retry, or second MCP call.
- The post-merge implementation delta is scoped to the canonical contract, runtime guidance, generated guide, regression assertions, and implementation note. No backend, deploy, realm, subject, memory, or object-chat change is present.

## Validation
- `git merge-base --is-ancestor 9062e99a19032e0fcc5e48b8db8dbfaf18fee1f4 842b611e08a4579b25bf89e605600d34e745ac80`: passed.
- Parent, combined-diff, scoped name-status, deleted-file, and post-merge delta inspection: passed.
- Manifest byte-length and SHA-256 verification for all 11 inputs: passed.
- Static registration/contract/family/guide alignment script: passed at 67 unique tools with equal name sets and no family duplicates.
- Direct `build_how_to_response` write-intent check: passed with exactly one disclosed call, exact five-input params, aligned answer/safety text, and no target tool in `avoid_tools`.
- `python3 -m json.tool onto_mcp/agent_contract.json`: passed.
- `python3 -m compileall -q onto_mcp`: passed.
- `git diff --check`: passed.
- Focused pytest command did not execute tests: collection stopped with four `ModuleNotFoundError: No module named 'pydantic'` errors. Five items were collected before interruption. Dependency installation was forbidden and was not attempted.

## Verdict
- `approved_with_notes`.
- The implementation satisfies the exact review scope with no blocking finding. The pytest limitation is material evidence debt: this review does not claim a focused/full test pass, independent QA, merge readiness beyond this reviewed contract, deploy readiness, or release acceptance. The focused suite must be rerun in an environment containing the repository-declared dependencies before any stronger validation claim.

## Commit Description (English)
- Short commit description: Record independent review of existing-link main sync and guidance.

## Handoff
- Remaining work: rerun the focused tests with declared dependencies through a separately authorized validation route; preserve the no-deploy boundary.
- Recommended next owner (area): `orchestrator` for process routing.
