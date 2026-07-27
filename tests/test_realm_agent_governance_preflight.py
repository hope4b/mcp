from __future__ import annotations

import inspect
import json
import sys
import time
import types
import unittest
from copy import deepcopy
from hashlib import sha256
from unittest.mock import patch

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _HTTPError(Exception):
        def __init__(self, response=None) -> None:
            super().__init__("stub http error")
            self.response = response

    class _Timeout(Exception):
        pass

    class _ConnectionError(Exception):
        pass

    class _RequestsExceptions:
        HTTPError = _HTTPError
        Timeout = _Timeout
        ConnectionError = _ConnectionError

    def _unexpected_request(*args, **kwargs):
        raise AssertionError("requests.request should not be called unexpectedly")

    requests_stub.exceptions = _RequestsExceptions()
    requests_stub.request = _unexpected_request
    sys.modules["requests"] = requests_stub

if "fastmcp" not in sys.modules:
    fastmcp_stub = types.ModuleType("fastmcp")
    fastmcp_server_stub = types.ModuleType("fastmcp.server")
    fastmcp_server_context_stub = types.ModuleType("fastmcp.server.context")
    fastmcp_server_dependencies_stub = types.ModuleType(
        "fastmcp.server.dependencies"
    )

    class _FastMCP:
        def __init__(self, name: str) -> None:
            self.name = name

        def tool(self, fn):
            return fn

        def resource(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

    class _Context:
        pass

    def _default_get_http_request():
        raise RuntimeError("no request")

    fastmcp_stub.FastMCP = _FastMCP
    fastmcp_server_context_stub.Context = _Context
    fastmcp_server_dependencies_stub.get_http_request = _default_get_http_request
    sys.modules["fastmcp"] = fastmcp_stub
    sys.modules["fastmcp.server"] = fastmcp_server_stub
    sys.modules["fastmcp.server.context"] = fastmcp_server_context_stub
    sys.modules["fastmcp.server.dependencies"] = fastmcp_server_dependencies_stub

from onto_mcp import api_resources, realm_agents
from onto_mcp.realm_agents import (
    GovernancePreflightArtifactMissing,
    GovernancePreflightDependencyFailure,
)

REALM_ID = "000ba00a-00a0-0a00-a000-000a0a0a0aa3"
PROPOSAL_ID = "11111111-1111-4111-8111-111111111111"
REGISTRY_ID = "22222222-2222-4222-8222-222222222222"
CURRENT_REGISTRY_ID = REGISTRY_ID
CONSTITUTION_ID = "33333333-3333-4333-8333-333333333333"
STEWARD_ID = "44444444-4444-4444-8444-444444444444"
OLD_CANDIDATE_ID = "55555555-5555-4555-8555-555555555555"
SUBMITTED_AT = "2026-07-26T18:00:00.123456Z"
ACCEPTED_AT = "2026-07-25T10:00:00Z"

HEADER = "| `slug` | Роль | Зона путей | Режим | Чартер | Состояние |"
SEPARATOR = "|---|---|---|---|---|---|"


def _row(slug: str, state: str = "активен") -> str:
    return (
        f"| `{slug}` | Role | `realm/agents/*` | `execution` | "
        f"`realm/agents/{slug}/charter` | `{state}` |"
    )


def _registry(*rows: str) -> str:
    return "\n".join(["# Registry", "", HEADER, SEPARATOR, *rows])


def _charter(
    slug: str,
    *,
    path_label: str = "Путь артефакта",
    body_suffix: str = "",
) -> str:
    return "\n".join(
        [
            f"# {slug}",
            "",
            f"**Пространство:** Платформа Онто · realm `{REALM_ID}`",
            f"**{path_label}:** `realm/agents/{slug}/charter`",
            f"**Slug:** `{slug}`",
            body_suffix,
        ]
    )


def _artifact(
    artifact_id: str,
    artifact_path: str,
    body: str,
    *,
    status: str = "accepted",
    artifact_kind: str = "decision",
    write_mode: str = "replace",
    realm_id: str = REALM_ID,
    scope_kind: str = "realm",
    scope_id: str = REALM_ID,
    **extra,
) -> dict:
    result = {
        "artifact_id": artifact_id,
        "realm_id": realm_id,
        "artifact_path": artifact_path,
        "artifact_kind": artifact_kind,
        "write_mode": write_mode,
        "scope_kind": scope_kind,
        "scope_id": scope_id,
        "status": status,
        "body": body,
    }
    result.update(extra)
    return result


def _proposal(
    path: str = "realm/agents/candidate/charter",
    body: str | None = None,
    *,
    predecessor: str | None = None,
    updated_at: object = SUBMITTED_AT,
    source_context: object | None = None,
    **extra,
) -> dict:
    if body is None:
        slug = path.split("/")[2] if path != realm_agents.REGISTRY_PATH else ""
        body = _registry(_row("constitutional-steward")) if not slug else _charter(slug)
    if source_context is None:
        source_context = {
            "realm_agent_governance_submit": {
                "schema_version": "1",
                "electorate_registry_artifact_id": REGISTRY_ID,
            }
        }
    return _artifact(
        PROPOSAL_ID,
        path,
        body,
        status="proposed",
        supersedes_artifact_id=predecessor,
        updated_at=updated_at,
        source_context=source_context,
        **extra,
    )


def _captured_registry(
    body: str | None = None,
    *,
    status: str = "accepted",
    accepted_at: object = ACCEPTED_AT,
    superseded_at: object = None,
    artifact_id: str = REGISTRY_ID,
    **extra,
) -> dict:
    return _artifact(
        artifact_id,
        realm_agents.REGISTRY_PATH,
        body or _registry(_row("constitutional-steward")),
        status=status,
        accepted_at=accepted_at,
        superseded_at=superseded_at,
        **extra,
    )


def _accepted_mapping(*, candidate: dict | None = None) -> dict[str, object]:
    mapping: dict[str, object] = {
        realm_agents.CONSTITUTION_PATH: _artifact(
            CONSTITUTION_ID,
            realm_agents.CONSTITUTION_PATH,
            "# Constitution",
        ),
        "realm/agents/constitutional-steward/charter": _artifact(
            STEWARD_ID,
            "realm/agents/constitutional-steward/charter",
            _charter("constitutional-steward"),
        ),
        realm_agents.REGISTRY_PATH: _captured_registry(),
    }
    if candidate is not None:
        mapping["realm/agents/candidate/charter"] = candidate
    return mapping


def _parse(result: str) -> dict:
    assert result.count(realm_agents.PREFLIGHT_LABEL) == 1, result
    prefix, payload = result.split(realm_agents.PREFLIGHT_LABEL, 1)
    assert prefix.strip()
    return json.loads(payload.strip())


def _call(
    proposal: dict,
    registry: dict | None = None,
    *,
    accepted: dict[str, object] | None = None,
    realm_id: str = REALM_ID,
    proposal_id: str = PROPOSAL_ID,
) -> tuple[str, dict, list[tuple[str, str]]]:
    exact = {
        PROPOSAL_ID: proposal,
        REGISTRY_ID: registry or _captured_registry(),
    }
    accepted_mapping = accepted or _accepted_mapping()
    ledger: list[tuple[str, str]] = []

    def read_id(artifact_id: str):
        ledger.append(("id", artifact_id))
        value = exact.get(artifact_id)
        if value is None:
            raise GovernancePreflightArtifactMissing(
                (
                    "read_proposal_by_id"
                    if artifact_id == PROPOSAL_ID
                    else "read_submit_electorate_registry_by_id"
                ),
                artifact_id=artifact_id,
            )
        if isinstance(value, Exception):
            raise value
        return deepcopy(value)

    def read_path(path: str):
        ledger.append(("path", path))
        value = accepted_mapping.get(path)
        if value is None:
            raise GovernancePreflightArtifactMissing(
                (
                    "read_accepted_constitution"
                    if path == realm_agents.CONSTITUTION_PATH
                    else (
                        "read_accepted_registry"
                        if path == realm_agents.REGISTRY_PATH
                        else "read_accepted_charter"
                    )
                ),
                artifact_path=path,
            )
        if isinstance(value, Exception):
            raise value
        return deepcopy(value)

    result = realm_agents.preflight_realm_agent_governance_proposal_result(
        realm_id,
        proposal_id,
        read_id,
        read_path,
    )
    return result, _parse(result), ledger


class RealmAgentGovernancePreflightTests(unittest.TestCase):
    def test_signature_and_input_precedence_make_zero_calls(self) -> None:
        signature = inspect.signature(
            api_resources.preflight_realm_agent_governance_proposal
        )
        self.assertEqual(list(signature.parameters), ["realm_id", "proposal_artifact_id"])
        self.assertTrue(
            all(
                parameter.default is inspect.Parameter.empty
                for parameter in signature.parameters.values()
            )
        )
        cases = [
            ("", "", "realm_id_required"),
            ("bad", "", "realm_id_invalid"),
            ("", "bad", "realm_id_required"),
            ("bad", PROPOSAL_ID, "realm_id_invalid"),
            (REALM_ID, "", "proposal_artifact_id_required"),
            (REALM_ID, "bad", "proposal_artifact_id_invalid"),
        ]
        for realm_id, proposal_id, code in cases:
            with self.subTest(code=code):
                ledger: list[str] = []

                def record(value: str, target=ledger):
                    target.append(value)

                result = realm_agents.preflight_realm_agent_governance_proposal_result(
                    realm_id,
                    proposal_id,
                    record,
                    record,
                )
                data = _parse(result)
                self.assertEqual(data["preflight_status"], "input_error")
                self.assertEqual([item["code"] for item in data["issues"]], [code])
                self.assertEqual(ledger, [])

    def test_proposal_missing_and_returned_id_mismatch_stop_after_one_read(self) -> None:
        ledger: list[str] = []

        def missing(artifact_id: str):
            ledger.append(artifact_id)
            raise GovernancePreflightArtifactMissing(
                "read_proposal_by_id",
                artifact_id=artifact_id,
            )

        missing_data = _parse(
            realm_agents.preflight_realm_agent_governance_proposal_result(
                REALM_ID,
                PROPOSAL_ID,
                missing,
                lambda path: self.fail(path),
            )
        )
        self.assertEqual(missing_data["preflight_status"], "proposal_unavailable")
        self.assertEqual(missing_data["issues"][0]["code"], "proposal_missing")
        self.assertEqual(ledger, [PROPOSAL_ID])

        wrong = _proposal()
        wrong["artifact_id"] = OLD_CANDIDATE_ID
        _, mismatch, mismatch_ledger = _call(wrong)
        self.assertEqual(mismatch["preflight_status"], "invalid_proposal")
        self.assertEqual(
            mismatch["issues"][0]["code"],
            "proposal_artifact_id_mismatch",
        )
        self.assertIsNone(mismatch["proposal"])
        self.assertEqual(mismatch_ledger, [("id", PROPOSAL_ID)])

    def test_proposal_envelope_failures_are_deterministic_and_one_call(self) -> None:
        cases = [
            ("realm_id", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "proposal_realm_mismatch"),
            ("scope_kind", "entity", "proposal_scope_mismatch"),
            ("status", "draft", "proposal_status_unsupported"),
            ("artifact_kind", "worklog", "proposal_kind_mismatch"),
            ("write_mode", "append", "proposal_write_mode_mismatch"),
            ("artifact_path", "realm/agents/bad/path", "proposal_path_unsupported"),
            ("body", 3, "proposal_body_invalid"),
        ]
        for field, value, code in cases:
            with self.subTest(code=code):
                proposal = _proposal()
                proposal[field] = value
                _, data, ledger = _call(proposal)
                self.assertEqual(data["preflight_status"], "invalid_proposal")
                self.assertEqual(data["issues"][0]["code"], code)
                self.assertEqual(ledger, [("id", PROPOSAL_ID)])

    def test_proposal_timestamp_grammar_and_typed_transport_failures(self) -> None:
        invalid = [
            "2026-02-30T00:00:00Z",
            "2026-07-26T18:00:00",
            "2026-07-26T18:00:00z",
            "2026-07-26T18:00:00+00:00",
            "2026-07-26T21:00:00+03:00",
            "2026-07-26T18:00:00.1Z",
            "2026-07-26T18:00:00.1234Z",
        ]
        for value in invalid:
            with self.subTest(value=value):
                _, data, ledger = _call(_proposal(updated_at=value))
                self.assertEqual(
                    data["issues"][0]["code"],
                    "proposal_submitted_at_invalid",
                )
                self.assertIsNone(data["proposal"]["proposal_submitted_at"])
                self.assertEqual(ledger, [("id", PROPOSAL_ID)])
        for value in [None, 123]:
            with self.subTest(value=value):
                _, data, ledger = _call(_proposal(updated_at=value))
                self.assertEqual(data["preflight_status"], "dependency_error")
                self.assertEqual(data["dependency"]["kind"], "invalid_response")
                self.assertEqual(ledger, [("id", PROPOSAL_ID)])
        missing = _proposal()
        del missing["updated_at"]
        _, data, ledger = _call(missing)
        self.assertEqual(data["preflight_status"], "dependency_error")
        self.assertEqual(data["dependency"]["kind"], "invalid_response")
        self.assertEqual(ledger, [("id", PROPOSAL_ID)])

    def test_submit_capture_shape_failures_stop_after_proposal_read(self) -> None:
        invalid_contexts = [
            {},
            {"realm_agent_governance_submit": "wrong"},
            {"realm_agent_governance_submit": {"schema_version": "1"}},
            {
                "realm_agent_governance_submit": {
                    "schema_version": "2",
                    "electorate_registry_artifact_id": REGISTRY_ID,
                }
            },
            {
                "realm_agent_governance_submit": {
                    "schema_version": "1",
                    "electorate_registry_artifact_id": "bad",
                }
            },
            {
                "realm_agent_governance_submit": {
                    "schema_version": "1",
                    "electorate_registry_artifact_id": REGISTRY_ID,
                    "extra": True,
                }
            },
        ]
        for context in invalid_contexts:
            with self.subTest(context=context):
                _, data, ledger = _call(_proposal(source_context=context))
                self.assertIn(
                    data["issues"][0]["code"],
                    {"submit_electorate_missing", "submit_electorate_invalid"},
                )
                self.assertEqual(ledger, [("id", PROPOSAL_ID)])

    def test_captured_registry_identity_timestamp_and_interval_failures_are_two_calls(self) -> None:
        wrong_id = _captured_registry(artifact_id=OLD_CANDIDATE_ID)
        _, mismatch, ledger = _call(_proposal(), wrong_id)
        self.assertEqual(
            mismatch["issues"][0]["code"],
            "submit_electorate_registry_artifact_id_mismatch",
        )
        self.assertIsNone(mismatch["proposal"]["proposal_body_sha256"])
        self.assertEqual(
            ledger,
            [("id", PROPOSAL_ID), ("id", REGISTRY_ID)],
        )

        cases = [
            (
                _captured_registry(accepted_at="bad"),
                "submit_electorate_registry_accepted_at_invalid",
            ),
            (
                _captured_registry(
                    status="superseded",
                    superseded_at="2026-07-26T18:00:00+00:00",
                ),
                "submit_electorate_registry_superseded_at_invalid",
            ),
            (
                _captured_registry(accepted_at="2026-07-27T00:00:00Z"),
                "submit_electorate_not_current_at_submit",
            ),
            (
                _captured_registry(
                    status="superseded",
                    superseded_at=SUBMITTED_AT,
                ),
                "submit_electorate_not_current_at_submit",
            ),
            (
                _captured_registry(
                    status="superseded",
                    superseded_at=ACCEPTED_AT,
                ),
                "submit_electorate_not_current_at_submit",
            ),
            (
                _captured_registry(status="accepted", superseded_at="2026-08-01T00:00:00Z"),
                "submit_electorate_not_current_at_submit",
            ),
        ]
        for registry, code in cases:
            with self.subTest(code=code):
                _, data, calls = _call(_proposal(), registry)
                self.assertEqual(data["issues"][0]["code"], code)
                self.assertEqual(
                    calls,
                    [("id", PROPOSAL_ID), ("id", REGISTRY_ID)],
                )
                self.assertIsNone(data["proposal"]["proposal_body_sha256"])

    def test_captured_registry_lifecycle_boundaries_and_transport_types(self) -> None:
        invalid_timestamps = [
            "2026-02-30T00:00:00Z",
            "2026-07-25T10:00:00",
            "2026-07-25T10:00:00z",
            "2026-07-25T10:00:00+00:00",
            "2026-07-25T13:00:00+03:00",
            "2026-07-25T10:00:00.1Z",
            "2026-07-25T10:00:00.1234Z",
        ]
        for field, code in [
            (
                "accepted_at",
                "submit_electorate_registry_accepted_at_invalid",
            ),
            (
                "superseded_at",
                "submit_electorate_registry_superseded_at_invalid",
            ),
        ]:
            for value in invalid_timestamps:
                with self.subTest(field=field, value=value):
                    registry = _captured_registry(
                        status="superseded" if field == "superseded_at" else "accepted",
                        superseded_at=(
                            value if field == "superseded_at" else None
                        ),
                    )
                    registry[field] = value
                    _, data, ledger = _call(_proposal(), registry)
                    self.assertEqual(data["preflight_status"], "invalid_current_governance")
                    self.assertEqual(data["issues"][0]["code"], code)
                    self.assertEqual(
                        ledger,
                        [("id", PROPOSAL_ID), ("id", REGISTRY_ID)],
                    )

        for field, value in [
            ("accepted_at", None),
            ("accepted_at", 3),
            ("superseded_at", 3),
        ]:
            with self.subTest(field=field, value=value):
                registry = _captured_registry()
                registry[field] = value
                _, data, ledger = _call(_proposal(), registry)
                self.assertEqual(data["preflight_status"], "dependency_error")
                self.assertEqual(data["dependency"]["kind"], "invalid_response")
                self.assertEqual(
                    ledger,
                    [("id", PROPOSAL_ID), ("id", REGISTRY_ID)],
                )

        for field in ["accepted_at", "superseded_at"]:
            with self.subTest(missing=field):
                registry = _captured_registry()
                del registry[field]
                _, data, ledger = _call(_proposal(), registry)
                self.assertEqual(data["preflight_status"], "dependency_error")
                self.assertEqual(data["dependency"]["kind"], "invalid_response")
                self.assertEqual(
                    ledger,
                    [("id", PROPOSAL_ID), ("id", REGISTRY_ID)],
                )

        equal_accept = _captured_registry(accepted_at=SUBMITTED_AT)
        _, accepted, _ = _call(_proposal(), equal_accept)
        self.assertEqual(accepted["preflight_status"], "pass")
        self.assertEqual(
            accepted["electorate_registry"]["accepted_at"],
            SUBMITTED_AT,
        )

        later_supersede = _captured_registry(
            status="superseded",
            superseded_at="2026-07-26T18:00:01.000000000Z",
        )
        _, superseded, _ = _call(_proposal(), later_supersede)
        self.assertEqual(superseded["preflight_status"], "pass")
        self.assertEqual(
            superseded["electorate_registry"]["superseded_at"],
            "2026-07-26T18:00:01.000000000Z",
        )

    def test_candidate_success_has_exact_hash_capture_and_non_null_predecessor(self) -> None:
        body = _charter("candidate", body_suffix="é")
        result, data, ledger = _call(_proposal(body=body))
        self.assertIsInstance(result, str)
        self.assertEqual(data["preflight_status"], "pass")
        self.assertTrue(data["preflight_passed"])
        self.assertEqual(data["proposal_kind"], "candidate_charter")
        self.assertEqual(
            data["expected_predecessor"],
            {"required": False, "artifact_id": None, "source": "none"},
        )
        self.assertEqual(
            data["proposal"]["proposal_body_sha256"],
            sha256(body.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            data["submit_electorate_capture"]["source_field"],
            "source_context.realm_agent_governance_submit.electorate_registry_artifact_id",
        )
        self.assertEqual(
            data["electorate_registry"]["artifact_id"],
            REGISTRY_ID,
        )
        self.assertTrue(data["electorate_registry"]["current_at_proposal_submit"])
        self.assertEqual(data["proposal"]["proposal_submitted_at"], SUBMITTED_AT)
        self.assertEqual(
            ledger,
            [
                ("id", PROPOSAL_ID),
                ("id", REGISTRY_ID),
                ("path", realm_agents.CONSTITUTION_PATH),
                ("path", "realm/agents/constitutional-steward/charter"),
                ("path", "realm/agents/candidate/charter"),
            ],
        )

    def test_candidate_repair_and_resident_amendment_bind_exact_predecessor(self) -> None:
        existing = _artifact(
            OLD_CANDIDATE_ID,
            "realm/agents/candidate/charter",
            "historically unparseable body",
        )
        accepted = _accepted_mapping(candidate=existing)
        _, repair, _ = _call(
            _proposal(predecessor=OLD_CANDIDATE_ID),
            accepted=accepted,
        )
        self.assertEqual(repair["proposal_kind"], "candidate_charter_repair")
        self.assertEqual(
            repair["expected_predecessor"]["artifact_id"],
            OLD_CANDIDATE_ID,
        )

        resident_proposal = _proposal(
            path="realm/agents/constitutional-steward/charter",
            predecessor=STEWARD_ID,
        )
        _, resident, _ = _call(resident_proposal)
        self.assertEqual(resident["proposal_kind"], "resident_charter_amendment")
        self.assertEqual(
            resident["expected_predecessor"],
            {
                "required": True,
                "artifact_id": STEWARD_ID,
                "source": "current_registered_charter",
            },
        )

    def test_charter_metadata_and_predecessor_fail_closed(self) -> None:
        wrong_label = _proposal(
            body=_charter("candidate", path_label="Путь будущего артефакта")
        )
        _, wrong_label_data, _ = _call(wrong_label)
        self.assertEqual(
            wrong_label_data["issues"][0]["code"],
            "charter_unparseable",
        )
        predecessor_cases = [
            (
                _proposal(
                    path="realm/agents/constitutional-steward/charter",
                    predecessor=None,
                ),
                "proposal_predecessor_missing",
            ),
            (
                _proposal(predecessor=STEWARD_ID),
                "proposal_predecessor_unexpected",
            ),
            (
                _proposal(
                    path="realm/agents/constitutional-steward/charter",
                    predecessor=OLD_CANDIDATE_ID,
                ),
                "proposal_predecessor_mismatch",
            ),
        ]
        for proposal, code in predecessor_cases:
            with self.subTest(code=code):
                _, data, _ = _call(proposal)
                self.assertEqual(data["issues"][0]["code"], code)
                self.assertIsNotNone(data["expected_predecessor"])

    def test_charter_metadata_ambiguity_and_mismatches_are_closed(self) -> None:
        another_realm = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        cases = [
            (
                _charter("candidate")
                + "\n**Slug:** `candidate`",
                "charter_unparseable",
            ),
            (
                _charter("candidate").replace(
                    "**Slug:** `candidate`",
                    "",
                ),
                "charter_unparseable",
            ),
            (
                _charter("candidate").replace(
                    "realm/agents/candidate/charter",
                    "realm/agents/other/charter",
                ),
                "charter_path_mismatch",
            ),
            (
                _charter("candidate").replace(
                    "**Slug:** `candidate`",
                    "**Slug:** `other`",
                ),
                "charter_slug_mismatch",
            ),
            (
                _charter("candidate").replace(REALM_ID, another_realm),
                "charter_realm_mismatch",
            ),
        ]
        for body, code in cases:
            with self.subTest(code=code):
                _, data, _ = _call(_proposal(body=body))
                self.assertEqual(data["preflight_status"], "invalid_proposal")
                self.assertEqual(data["issues"][0]["code"], code)

    def test_registry_proposal_passes_reads_each_charter_once_and_cannot_remove_resident(self) -> None:
        proposal = _proposal(
            path=realm_agents.REGISTRY_PATH,
            predecessor=REGISTRY_ID,
        )
        _, data, ledger = _call(proposal)
        self.assertEqual(data["preflight_status"], "pass")
        self.assertEqual(data["proposal_kind"], "registry_amendment")
        self.assertIsNone(data["charter_slug"])
        self.assertEqual(
            ledger.count(("path", "realm/agents/constitutional-steward/charter")),
            1,
        )
        self.assertEqual(ledger[-1], ("path", realm_agents.REGISTRY_PATH))

        empty_registry = f"# Registry\n\n{HEADER}\n{SEPARATOR}"
        _, removed, _ = _call(
            _proposal(
                path=realm_agents.REGISTRY_PATH,
                body=empty_registry,
                predecessor=REGISTRY_ID,
            )
        )
        self.assertEqual(removed["issues"][0]["code"], "registry_resident_removed")

    def test_registry_addition_requires_accepted_strict_charter(self) -> None:
        proposed_body = _registry(_row("constitutional-steward"), _row("new-agent"))
        proposal = _proposal(
            path=realm_agents.REGISTRY_PATH,
            body=proposed_body,
            predecessor=REGISTRY_ID,
        )
        _, missing, _ = _call(proposal)
        self.assertEqual(missing["issues"][0]["code"], "charter_missing")

        accepted = _accepted_mapping()
        accepted["realm/agents/new-agent/charter"] = _artifact(
            OLD_CANDIDATE_ID,
            "realm/agents/new-agent/charter",
            _charter("new-agent"),
        )
        _, passed, _ = _call(proposal, accepted=accepted)
        self.assertEqual(passed["preflight_status"], "pass")

        accepted["realm/agents/new-agent/charter"]["artifact_kind"] = "worklog"
        _, strict, _ = _call(proposal, accepted=accepted)
        self.assertEqual(strict["issues"][0]["code"], "charter_kind_mismatch")

    def test_registry_structure_duplicate_state_path_and_size_fail_closed(self) -> None:
        malformed = f"# Registry\n\n{HEADER}\n{SEPARATOR}\n| `broken` | too | short |"
        cases = [
            (malformed, "registry_row_malformed"),
            (
                _registry(
                    _row("constitutional-steward"),
                    _row("constitutional-steward"),
                ),
                "registry_slug_duplicate",
            ),
            (
                _registry(_row("constitutional-steward", state="unknown")),
                "resident_state_unsupported",
            ),
            (
                _registry(
                    _row("constitutional-steward").replace(
                        "realm/agents/constitutional-steward/charter",
                        "realm/agents/other/charter",
                    )
                ),
                "charter_path_mismatch",
            ),
        ]
        for body, code in cases:
            with self.subTest(code=code):
                _, data, _ = _call(
                    _proposal(
                        path=realm_agents.REGISTRY_PATH,
                        body=body,
                        predecessor=REGISTRY_ID,
                    )
                )
                self.assertEqual(data["preflight_status"], "invalid_proposal")
                self.assertEqual(data["issues"][0]["code"], code)

        rows = [_row("constitutional-steward")]
        rows.extend(_row(f"agent-{index}") for index in range(32))
        _, oversized, ledger = _call(
            _proposal(
                path=realm_agents.REGISTRY_PATH,
                body=_registry(*rows),
                predecessor=REGISTRY_ID,
            )
        )
        self.assertEqual(
            oversized["issues"][0]["code"],
            "registry_size_limit_exceeded",
        )
        self.assertEqual(
            ledger,
            [
                ("id", PROPOSAL_ID),
                ("id", REGISTRY_ID),
                ("path", realm_agents.CONSTITUTION_PATH),
                ("path", "realm/agents/constitutional-steward/charter"),
            ],
        )

    def test_registry_drift_preserves_charter_electorate_but_blocks_registry_predecessor(self) -> None:
        changed_current = _accepted_mapping()
        changed_current[realm_agents.REGISTRY_PATH] = _captured_registry(
            artifact_id=OLD_CANDIDATE_ID
        )
        charter = _proposal()
        _, charter_data, _ = _call(charter, accepted=changed_current)
        self.assertEqual(charter_data["preflight_status"], "pass")
        self.assertEqual(
            charter_data["electorate_registry"]["artifact_id"],
            REGISTRY_ID,
        )

        registry = _proposal(
            path=realm_agents.REGISTRY_PATH,
            predecessor=REGISTRY_ID,
        )
        _, registry_data, _ = _call(registry, accepted=changed_current)
        self.assertEqual(
            registry_data["issues"][0]["code"],
            "proposal_predecessor_mismatch",
        )
        self.assertEqual(
            registry_data["electorate_registry"]["artifact_id"],
            REGISTRY_ID,
        )

    def test_current_governance_missing_wrong_envelope_and_untrusted_response(self) -> None:
        accepted = _accepted_mapping()
        del accepted[realm_agents.CONSTITUTION_PATH]
        _, missing, missing_ledger = _call(_proposal(), accepted=accepted)
        self.assertEqual(missing["issues"][0]["code"], "constitution_missing")
        self.assertEqual(missing_ledger[-1], ("path", realm_agents.CONSTITUTION_PATH))

        accepted = _accepted_mapping()
        accepted[realm_agents.CONSTITUTION_PATH]["artifact_path"] = "wrong"
        _, wrong, _ = _call(_proposal(), accepted=accepted)
        self.assertEqual(wrong["issues"][0]["code"], "constitution_path_mismatch")
        self.assertEqual(wrong["current_governance_status"], "invalid_governance_state")

        accepted = _accepted_mapping()
        accepted[realm_agents.CONSTITUTION_PATH] = {"artifact_id": "only"}
        _, invalid, _ = _call(_proposal(), accepted=accepted)
        self.assertEqual(invalid["preflight_status"], "dependency_error")
        self.assertEqual(invalid["dependency"]["kind"], "invalid_response")

    def test_dependency_failure_projection_is_closed_and_secret_free(self) -> None:
        kinds = ["unauthenticated", "forbidden", "timeout", "network", "backend_error"]
        for kind in kinds:
            with self.subTest(kind=kind):
                failure = GovernancePreflightDependencyFailure(
                    kind,
                    "read_proposal_by_id",
                    artifact_id=PROPOSAL_ID,
                    http_status=429 if kind == "backend_error" else None,
                )
                ledger: list[str] = []

                def fail(
                    artifact_id: str,
                    target=ledger,
                    current_failure=failure,
                ):
                    target.append(artifact_id)
                    raise current_failure

                result = realm_agents.preflight_realm_agent_governance_proposal_result(
                    REALM_ID,
                    PROPOSAL_ID,
                    fail,
                    lambda path: self.fail(path),
                )
                data = _parse(result)
                self.assertEqual(data["preflight_status"], "dependency_error")
                self.assertEqual(data["dependency"]["kind"], kind)
                self.assertEqual(
                    data["dependency"]["operation"],
                    "read_proposal_by_id",
                )
                self.assertNotIn("secret", result.lower())
                self.assertEqual(ledger, [PROPOSAL_ID])

    def test_exact_body_hash_does_not_normalize_bytes(self) -> None:
        variants = [
            _charter("candidate"),
            _charter("candidate") + "\n",
            _charter("candidate").replace("\n", "\r\n"),
            _charter("candidate", body_suffix="é"),
            _charter("candidate", body_suffix="e\u0301"),
        ]
        observed = []
        for body in variants:
            _, data, _ = _call(_proposal(body=body))
            observed.append(data["proposal"]["proposal_body_sha256"])
            self.assertEqual(observed[-1], sha256(body.encode("utf-8")).hexdigest())
        self.assertEqual(len(set(observed)), len(variants))

    def test_repeated_success_preserves_exact_capture_and_timestamps(self) -> None:
        proposal = _proposal()
        registry = _captured_registry()
        _, first, _ = _call(proposal, registry)
        _, second, _ = _call(proposal, registry)
        self.assertEqual(first, second)
        self.assertEqual(
            first["submit_electorate_capture"],
            {
                "source_field": (
                    "source_context.realm_agent_governance_submit."
                    "electorate_registry_artifact_id"
                ),
                "registry_artifact_id": REGISTRY_ID,
                "proposal_submitted_at": SUBMITTED_AT,
            },
        )
        self.assertEqual(first["electorate_registry"]["accepted_at"], ACCEPTED_AT)

    def test_transport_readers_use_only_exact_routes_and_closed_http_mapping(self) -> None:
        class Response:
            def __init__(self, status: int, payload: object) -> None:
                self.status_code = status
                self.payload = payload

            def json(self):
                if isinstance(self.payload, Exception):
                    raise self.payload
                return self.payload

        captured: list[tuple[str, str, object]] = []

        def request(method, url, *, json=None, **kwargs):
            captured.append((method, url, json))
            return Response(200, _proposal())

        with patch.object(
            api_resources,
            "ONTO_API_BASE",
            "https://onto.example/api/core",
        ), patch.object(
            api_resources,
            "_onto_headers",
            return_value={"X-API-Key": "secret"},
        ), patch.object(
            sys.modules["requests"],
            "request",
            side_effect=request,
        ):
            api_resources._read_preflight_artifact_by_id(
                REALM_ID,
                PROPOSAL_ID,
                "read_proposal_by_id",
            )
            api_resources._read_preflight_accepted_artifact(
                REALM_ID,
                realm_agents.CONSTITUTION_PATH,
            )
        self.assertEqual(captured[0][0], "GET")
        self.assertTrue(captured[0][1].endswith(f"/artifact/{PROPOSAL_ID}"))
        self.assertIsNone(captured[0][2])
        self.assertEqual(captured[1][0], "POST")
        self.assertTrue(captured[1][1].endswith("/artifact/path"))
        self.assertEqual(
            captured[1][2],
            {"artifact_path": realm_agents.CONSTITUTION_PATH},
        )

        for status, kind in [
            (401, "unauthenticated"),
            (403, "forbidden"),
            (400, "backend_error"),
            (409, "backend_error"),
            (429, "backend_error"),
            (500, "backend_error"),
        ]:
            with self.subTest(status=status), patch.object(
                api_resources,
                "_onto_headers",
                return_value={"X-API-Key": "secret"},
            ), patch.object(
                sys.modules["requests"],
                "request",
                return_value=Response(status, {"secret": "DO_NOT_LEAK"}),
            ):
                with self.assertRaises(GovernancePreflightDependencyFailure) as caught:
                    api_resources._read_preflight_artifact_by_id(
                        REALM_ID,
                        PROPOSAL_ID,
                        "read_proposal_by_id",
                    )
                self.assertEqual(caught.exception.kind, kind)
                self.assertEqual(caught.exception.http_status, status)
                self.assertNotIn("DO_NOT_LEAK", str(caught.exception))

    def test_tool_level_timeout_uses_preflight_framing_and_cancels_later_reads(self) -> None:
        ledger: list[str] = []

        class Response:
            status_code = 200

            def json(self):
                return _proposal()

        def slow_request(method, url, **kwargs):
            ledger.append(url)
            time.sleep(0.05)
            return Response()

        with patch.object(
            api_resources,
            "_HTTP_MCP_TOOL_TIMEOUT_SECONDS",
            0.001,
        ), patch.object(
            api_resources,
            "_onto_headers",
            return_value={"X-API-Key": "secret"},
        ), patch.object(
            sys.modules["requests"],
            "request",
            side_effect=slow_request,
        ):
            result = api_resources.preflight_realm_agent_governance_proposal(
                REALM_ID,
                PROPOSAL_ID,
            )
        data = _parse(result)
        self.assertEqual(data["preflight_status"], "dependency_error")
        self.assertEqual(data["dependency"]["kind"], "timeout")
        time.sleep(0.06)
        self.assertEqual(len(ledger), 1)

    def test_overflow_returns_pinned_compact_shape(self) -> None:
        with patch.object(realm_agents, "MAX_RESULT_BYTES", 800):
            result, data, _ = _call(_proposal(body=_charter("candidate") + "x" * 10000))
        self.assertLessEqual(len(result.encode("utf-8")), 800)
        self.assertEqual(
            data["issues"][0]["code"],
            "response_size_limit_exceeded",
        )
        self.assertEqual(data["preflight_status"], "invalid_current_governance")
        self.assertEqual(data["current_governance_status"], "invalid_governance_state")
        self.assertIsNone(data["proposal"])


if __name__ == "__main__":
    unittest.main()
