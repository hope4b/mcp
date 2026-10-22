# Remove historical baseline SHA assertion

## Task
- Objective: remove only the stale historical SHA assertion from
  `ServerRuntimeTests.test_public_tool_contract_matches_read_only_pre_change_baseline`.
- Scope: `tests/test_server_runtime.py` and this task note only.
- Out of scope: product runtime, process architecture, feature lifecycle/checkpoints,
  baseline edits, external writes, independent QA, commits, PRs and delivery.
- Owner explicitly approved this exact repair in the current chat (`давай`).

## Context Used
- AGENTS.md, ROLES.md, PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md and
  TEST_STRATEGY.md read: yes; TASK_TEMPLATE.md used.
- Read direct-owner assignment contract, MCP Owner bootstrap and runtime kernel.
- Authoritative supplied bootstrap: valid active/execution resident `mcp-owner`,
  boot allowed; accepted/current Constitution `b826563c-f1ab-47ec-a994-0dfe86662833`,
  Registry `306f6b34-daeb-4e36-a8b7-035d5509f21c`, own Charter
  `656fdd41-a025-4f1e-8e44-b804c0657a0a`. Governance was not reread.
- Territory: MCP runtime/toolset/HTTP/guidance and MCP-scoped evidence; author only.
- Locked anchors: no Onto task anchor supplied; none discovered or substituted.

```yaml
direct_owner_task_context:
  contract: direct_owner_task_context_v1
  assignment_source: human_owner_current_chat
  role: mcp-owner
  task_mode: implementation
  repository_root: /home/ubuntu/git/onto/_platform/agent-runtime/.runtime/feature-worktrees/mcp-historical-baseline-sha
  branch: codex/fix-mcp-historical-baseline-sha
  head_commit: fdc5ade46cf2acbb19935812feafc0d3e21a29d5
  scope: Remove historical SHA assertion; preserve baseline requirements and public-contract comparisons.
  allowed_mutation:
    - tests/test_server_runtime.py
    - docs/agents/tasks/2026-10-23-remove-historical-baseline-sha.md
  validation_route: Focused test before/after, then complete pytest suite against supplied immutable baseline.
  result_destination: docs/agents/tasks/2026-10-23-remove-historical-baseline-sha.md and final structured result
  independence: Author verification only; independent reviewer follows separately.
  orchestrator_run: none
```

## Changes
- Removed the four-line `GENERIC_QA_BASE_SHA` equality assertion only.
- Preserved required `GENERIC_QA_BASELINE_ROOT`, baseline file check, runtime
  comparison, exact tool-set comparison and every per-tool snapshot comparison.
- No product/public contract or process semantics changed; no new tests or skips.
- Initial working tree was clean and branch/HEAD matched the assignment.

## Validation
- Interpreter: `/home/ubuntu/git/onto/_platform/qa/mcp-feature-venv/bin/python`,
  Python 3.14.4. With inherited `PYTHONPATH` removed, import checks resolved
  `onto_mcp/__init__.py` and `onto_mcp/server.py` inside this worktree.
- Exact focused command, run before and after the removal from repository root:

```sh
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 GENERIC_QA_BASELINE_ROOT=/home/ubuntu/git/onto/_platform/agent-runtime/.runtime/generic-feature-checks/58d8b863-c13d-490c-9805-2c551751b486/mcp/baseline-source GENERIC_QA_BASE_SHA=fdc5ade46cf2acbb19935812feafc0d3e21a29d5 /home/ubuntu/git/onto/_platform/qa/mcp-feature-venv/bin/python -m pytest -p no:cacheprovider tests/test_server_runtime.py::ServerRuntimeTests::test_public_tool_contract_matches_read_only_pre_change_baseline
```

- Before: exit 1; 1 collected, 1 failed in 1.00s at line 940, with supplied
  `fdc5ade46cf2acbb19935812feafc0d3e21a29d5` unequal to the historical literal
  `636577f6375bf4aa3c910ff821bb4083e5c71857`, before snapshot comparison.
- After: exit 1; 1 collected, 1 failed in 121.12s. The SHA assertion no
  longer blocks, but the unchanged baseline `_public_contract_snapshot` subprocess
  raised `subprocess.TimeoutExpired` after its existing 120-second limit at
  test line 941 / helper line 249. Candidate comparison was not reached; no
  public-contract equivalence verdict is claimed.
- Exact full-suite command:

```sh
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 GENERIC_QA_BASELINE_ROOT=/home/ubuntu/git/onto/_platform/agent-runtime/.runtime/generic-feature-checks/58d8b863-c13d-490c-9805-2c551751b486/mcp/baseline-source GENERIC_QA_BASE_SHA=fdc5ade46cf2acbb19935812feafc0d3e21a29d5 /home/ubuntu/git/onto/_platform/qa/mcp-feature-venv/bin/python -m pytest -p no:cacheprovider
```

- Full suite: 279 collected; output reached 49% with preceding cases reported
  passed, then stalled without further output in
  `CanonicalProjectionTests.test_production_http_boundary_keeps_sentinels_out_of_observable_channels`.
  Interrupted with Ctrl-C; exit 130, no final aggregate counts emitted.
  The suite did not complete; no full-suite pass is claimed. Root cause of the
  stall is unverified and outside this four-line repair.
- `git diff --check`: passed. Exact source comparison against HEAD confirms
  the sole test-file change is deletion of the specified assertion.
- `compileall` not run: product sources unchanged; scoped validation requires
  the focused test and full suite only.
- Baseline is read-only input and was not edited. Probe code explicitly binds
  each subprocess's source root; the candidate root derives from this test file.
- Live smoke/deploy not run: outside this local test-only assignment.

## Commit Description (English)
- Remove stale historical SHA assertion from MCP contract test.

## Handoff
- Residual risk: author verification cannot satisfy independent review/QA.
- Validation blocker: unchanged baseline snapshot timed out; complete suite
  stalled in a separate existing test. The next owner must arrange a suitable
  local validation environment and repeat the same checks before claiming a
  passing public-contract comparison or full suite. No broader permissions,
  timeout changes, skips, historical SHA injection or runtime fixes attempted.
- Next owner: independent reviewer assigned by the parent; parent assembles the
  reviewed commit separately. No commit or delivery performed in this run.

## Host validation follow-up

The parent reran the same checks on the host after the sandbox-only stalls.
The source, immutable baseline, baseline SHA and existing test timeouts were
unchanged. No service, runtime or test-comparison policy was modified.

- Focused command: the exact focused command above, outside the sandbox.
  Exit 0: **1 passed, 69 subtests passed in 4.63s**. Both baseline and candidate
  snapshots completed and all public-contract comparisons passed.
- Full-suite command: the exact full-suite command above with `-q` appended,
  outside the sandbox. Exit 0: **279 passed, 1 warning in 10.72s**.
- These successful host checks supersede the validation blockers from the
  author's sandbox runs; the earlier failures remain documented as history.
- Independent review is still a separate next step. No change to the existing
  batch execution checkpoint or its source revision is authorized by these
  checks. This is local test evidence, not deployment or live MCP QA.
