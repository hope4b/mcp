# OAuth candidate check completion repair

## Task
- Objective: implement QA-CANDIDATE-01 (AC-03) and QA-CANDIDATE-02 (AC-04).
- Scope: MCP synthetic test sources and fixed inventory oracle only.
- Out of scope: runtime changes, provider operations, independent QA, deployment,
  publication, Core/Web UI changes and governance.

## Context Used
- AGENTS.md, ROLES.md, PROJECT_CONTEXT.md, ARCHITECTURE_MAP.md,
  TEST_STRATEGY.md and TASK_TEMPLATE.md read; no nested AGENTS.md exists.
- Native assignment: `../authority.json`, SHA256
  `c66faee60e1854f0190388b7bc30d895e94cb6e5ced6d7c8ee357a7f5c7707f9`.
- Role/mode: active execution resident mcp-owner / runtime, feature_write.
- Locked realm/anchor: `000ba00a-00a0-0a00-a000-000a0a0a0aa3` /
  `528303fe-678c-445c-bd76-e96a22aca27a`; no discovery or substitution.
- Supplied accepted Constitution b826563c-f1ab-47ec-a994-0dfe86662833,
  Registry 4b2edeff-fe1c-4419-a607-22843ffe27d6, valid active resident verdict,
  and Charter 656fdd41-a025-4f1e-8e44-b804c0657a0a used without rereading.
- Process source: b9984318abb3bdbaabfb7b29817f0ad61b1adaa7;
  MCP_OWNER_BOOTSTRAP_TEMPLATE.md and FEATURE_PIPELINE_RECEIVER.md apply.
- All 14 pinned source lengths/hashes and ten material body hashes verified.
- Approved specification/start binding: f1acd520-10d4-4f29-b33f-3c36ee3f80b5
  @68e3878b25b6dcaf0eb77e8974cab2c42f861e8da7725ce4c7ae7d6adeff017b.
- Exact repair evidence: e6a3a64f-5e21-45b1-8175-08c890963377
  @84c99b4932821a8a4df31be1ed92782b88298c23cb3adca7a3b86bdf41dc7484.
- Starting HEAD/tree: d2425fdd490ad62c3fee0c29b2ab09cc58c158c9 /
  cd4bbcf1d11e93912bbd3d700a8a46447d9ea24e.
- Original/effective/assigned main: 4dcb0e5b63521a8a6fefc4afa67ece5af6081b5c.
  It already underlies the attempt parent; no incorporation needed.

## Changes
- `tests/fixtures/oauth_scope_inventory.json` pins the approved named 28 read,
  42 read-plus-write and two-resource inventory. The read list comes from the
  approved AC-03 oracle; write names are the remaining inherited registrations.
  Tests do not compute expected classifications from runtime READ_TOOLS or
  WRITE_TOOLS. Swapped classifications fail exact set and metadata assertions.
- Authorization, HTTP metadata and schema regression checks use that fixed oracle.
- Both actual resource registrations run with no/read/write/read-plus-write
  scopes through registered reads and direct invocation. Only underlying data
  helpers are inert mocks; rejected paths assert zero helper dispatch.
- Test-only represented-consent inspection follows configured Core audience and
  allowlisted external clients. It accepts the delivered conforming policy and
  changed Core audience, and rejects Core consent enabled/omitted, missing or
  misbound Core record, either external client's disabled consent, and incorrect
  settings/exchange target bindings. Each contradiction is isolated and checked
  for its exact affected binding. No runtime configuration validator was added.

## Validation
- `python -m pytest -q tests/test_oauth_authorization.py`: interrupted with exit
  130 after stalling at the asynchronous resource boundary, consistent with the
  inherited sandbox cross-thread event-loop wakeup limitation. No failure was
  suppressed. The process was stopped.
- Documented timer-wakeup runner copied verbatim to
  `/tmp/mcp_oauth_completion_pytest.py` from
  `docs/agents/tasks/2026-11-05-oauth-test-runner.txt`.
- `timeout 90s python /tmp/mcp_oauth_completion_pytest.py -q tests/test_oauth_authorization.py tests/test_oauth_http.py tests/test_server_runtime.py`:
  285 passed, one warning, exit 0. Full output:
  `docs/agents/tasks/2026-11-06-oauth-completion-validation.txt`.
- Initial ruff check found an import-order issue; it was corrected. Subsequent
  focused ruff check, compileall and git diff --check passed.
- Python 3.14.4 used; the declared Python 3.11 Docker runtime was not exercised.
  No full-suite rerun: this repair changes only scoped test assertions/fixtures;
  previous full-suite failures remain retained in prior committed evidence.

## Commit Description (English)
- Add independent OAuth inventory and consent inspection checks.

## Handoff
- Next owner: controller technical executor, independent reviewer, then qa-agent
  for fresh candidate QA; PREPROD QA remains separately mandatory.
- Register the three modified test-source paths as technical_checks; controller
  checks are neither independent functional QA nor deployment evidence.
- T1-C remains unresolved and fixed-audience ChatGPT compatibility unverified.
  Formal tests prove neither live OAuth/Core behavior nor deployed configuration.
- No agents, live HTTP/provider operations, credentials, ledgers, push, PR, merge,
  deployment or temporary services. Test-owned workers/processes exited.
