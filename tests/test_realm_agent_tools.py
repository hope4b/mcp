from __future__ import annotations

import json
import sys
import time
import types
import unittest
from unittest.mock import patch

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _HTTPError(Exception):
        pass

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

if not hasattr(sys.modules["requests"].exceptions, "Timeout"):

    class _Timeout(Exception):
        pass

    sys.modules["requests"].exceptions.Timeout = _Timeout

if not hasattr(sys.modules["requests"].exceptions, "ConnectionError"):

    class _ConnectionError(Exception):
        pass

    sys.modules["requests"].exceptions.ConnectionError = _ConnectionError

if "fastmcp" not in sys.modules:
    fastmcp_stub = types.ModuleType("fastmcp")
    fastmcp_server_stub = types.ModuleType("fastmcp.server")
    fastmcp_server_context_stub = types.ModuleType("fastmcp.server.context")
    fastmcp_server_dependencies_stub = types.ModuleType("fastmcp.server.dependencies")

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
from onto_mcp.realm_agents import RealmAgentDependencyFailure, RealmAgentPathMissing

REALM_ID = "000ba00a-00a0-0a00-a000-000a0a0a0aa3"
CONSTITUTION_ID = "59465d72-ed94-4716-8078-7da527e7ee66"
REGISTRY_ID = "9ef9f8b2-3eb7-4354-95f0-7d69c690807a"
STEWARD_ID = "9339ce9c-6953-4d75-9547-715cf6e6a229"
DEFECT_ID = "09eb1f60-2de2-4b1c-bca3-3745dc67c805"

HEADER = "| `slug` | Роль | Зона путей | Режим | Чартер | Состояние |"
SEPARATOR = "|---|---|---|---|---|---|"


def _registry(*rows: str, header: str = HEADER) -> str:
    return "\n".join(["# Registry", "", header, SEPARATOR, *rows, "", "After table."])


def _row(
    slug: str,
    *,
    role: str = "Realm role",
    path_zone: str = "realm/agents/*",
    mode: str = "execution",
    charter_path: str | None = None,
    state: str = "активен",
) -> str:
    path = charter_path if charter_path is not None else f"realm/agents/{slug}/charter"
    return f"| `{slug}` | {role} | `{path_zone}` | `{mode}` | `{path}` | `{state}` |"


def _charter(slug: str, *, realm_id: str = REALM_ID, path: str | None = None) -> str:
    artifact_path = path if path is not None else f"realm/agents/{slug}/charter"
    return "\n".join(
        [
            f"# Charter {slug}",
            "",
            f"**Пространство:** Платформа Онто · realm `{realm_id}`",
            f"**Путь артефакта:** `{artifact_path}`",
            f"**Slug:** `{slug}`",
            "",
            "SECRET SOURCE BODY THAT MUST NEVER APPEAR",
        ]
    )


def _artifact(
    artifact_id: str,
    artifact_path: str,
    body: str,
    *,
    realm_id: str = REALM_ID,
    scope_kind: str = "realm",
    scope_id: str = REALM_ID,
    status: str = "accepted",
) -> dict:
    return {
        "artifact_id": artifact_id,
        "realm_id": realm_id,
        "artifact_path": artifact_path,
        "artifact_kind": "decision",
        "write_mode": "replace",
        "scope_kind": scope_kind,
        "scope_id": scope_id,
        "status": status,
        "body": body,
        "summary": "summary",
        "append_entries": [{"body": "SECRET APPEND"}],
        "audit_summary": {"last_event": "accepted", "body": "SECRET AUDIT"},
    }


def _base_mapping(registry_body: str | None = None) -> dict[str, object]:
    body = (
        registry_body
        if registry_body is not None
        else _registry(_row("constitutional-steward"))
    )
    return {
        realm_agents.CONSTITUTION_PATH: _artifact(
            CONSTITUTION_ID,
            realm_agents.CONSTITUTION_PATH,
            "SECRET CONSTITUTION BODY",
        ),
        realm_agents.REGISTRY_PATH: _artifact(
            REGISTRY_ID,
            realm_agents.REGISTRY_PATH,
            body,
        ),
        "realm/agents/constitutional-steward/charter": _artifact(
            STEWARD_ID,
            "realm/agents/constitutional-steward/charter",
            _charter("constitutional-steward"),
        ),
    }


def _reader(mapping: dict[str, object], ledger: list[str]):
    def read(_realm_id: str, artifact_path: str):
        ledger.append(artifact_path)
        value = mapping.get(artifact_path, RealmAgentPathMissing(artifact_path))
        if isinstance(value, Exception):
            raise value
        return value

    return read


def _parse(result: str, label: str) -> dict:
    assert result.count(label) == 1, result
    prefix, payload = result.split(label, 1)
    assert prefix.strip()
    return json.loads(payload.strip())


class RealmAgentToolTests(unittest.TestCase):
    def _call_list(self, mapping: dict[str, object]) -> tuple[str, dict, list[str]]:
        ledger: list[str] = []
        with patch.object(
            api_resources,
            "_read_accepted_memory_artifact_data",
            side_effect=_reader(mapping, ledger),
        ):
            result = api_resources.list_realm_agents(REALM_ID)
        return result, _parse(result, realm_agents.LIST_LABEL), ledger

    def _call_get(
        self, mapping: dict[str, object], slug: str
    ) -> tuple[str, dict, list[str]]:
        ledger: list[str] = []
        with patch.object(
            api_resources,
            "_read_accepted_memory_artifact_data",
            side_effect=_reader(mapping, ledger),
        ):
            result = api_resources.get_realm_agent(REALM_ID, slug)
        return result, _parse(result, realm_agents.GET_LABEL), ledger

    def test_constants_and_current_fixture_active_list_contract(self) -> None:
        self.assertEqual(realm_agents.MAX_REGISTRY_ENTRIES, 32)
        self.assertEqual(realm_agents.MAX_RESULT_BYTES, 65536)

        result, data, ledger = self._call_list(_base_mapping())

        self.assertIsInstance(result, str)
        self.assertEqual(data["schema_version"], "1")
        self.assertEqual(data["governance_status"], "valid")
        self.assertEqual(
            data["counts"],
            {
                "registry_entries": 1,
                "valid_active": 1,
                "valid_suspended": 0,
                "invalid": 0,
            },
        )
        self.assertEqual(data["agents"][0]["row_index"], 1)
        self.assertEqual(data["agents"][0]["slug"], "constitutional-steward")
        self.assertEqual(data["agents"][0]["validity"], "valid")
        self.assertEqual(data["agents"][0]["resident_state"], "active")
        self.assertTrue(data["agents"][0]["boot_allowed"])
        self.assertFalse(data["unregistered_charters_enumerated"])
        self.assertNotIn("defect-registrar", result)
        self.assertEqual(
            ledger,
            [
                realm_agents.CONSTITUTION_PATH,
                realm_agents.REGISTRY_PATH,
                "realm/agents/constitutional-steward/charter",
            ],
        )
        for forbidden in (
            "SECRET CONSTITUTION",
            "SECRET SOURCE BODY",
            "SECRET APPEND",
            "SECRET AUDIT",
        ):
            self.assertNotIn(forbidden, result)

    def test_get_unregistered_with_accepted_charter_uses_one_exact_probe(self) -> None:
        mapping = _base_mapping()
        mapping["realm/agents/defect-registrar/charter"] = _artifact(
            DEFECT_ID,
            "realm/agents/defect-registrar/charter",
            _charter("defect-registrar"),
        )

        result, data, ledger = self._call_get(mapping, "defect-registrar")

        self.assertEqual(data["governance_status"], "valid")
        self.assertEqual(data["resolution"], "not_registered")
        self.assertEqual(data["validity"], "not_resident")
        self.assertFalse(data["boot_allowed"])
        self.assertTrue(data["unregistered_charter"]["exists"])
        self.assertEqual(data["unregistered_charter"]["artifact_id"], DEFECT_ID)
        self.assertEqual(
            [issue["code"] for issue in data["issues"]], ["registry_entry_missing"]
        )
        self.assertEqual(ledger[-1], "realm/agents/defect-registrar/charter")
        self.assertEqual(ledger.count("realm/agents/defect-registrar/charter"), 1)
        self.assertNotIn("SECRET SOURCE BODY", result)

    def test_get_unregistered_without_charter_keeps_domain_absence(self) -> None:
        _, data, ledger = self._call_get(_base_mapping(), "missing-agent")

        self.assertEqual(data["resolution"], "not_registered")
        self.assertFalse(data["unregistered_charter"]["exists"])
        self.assertIsNone(data["unregistered_charter"]["artifact_id"])
        self.assertIsNone(data["dependency"])
        self.assertEqual(ledger[-1], "realm/agents/missing-agent/charter")

    def test_valid_suspended_resident_is_not_boot_allowed(self) -> None:
        mapping = _base_mapping(
            _registry(_row("sleeping-agent", state="приостановлен"))
        )
        mapping.pop("realm/agents/constitutional-steward/charter")
        mapping["realm/agents/sleeping-agent/charter"] = _artifact(
            STEWARD_ID,
            "realm/agents/sleeping-agent/charter",
            _charter("sleeping-agent"),
        )

        _, data, _ = self._call_get(mapping, "sleeping-agent")

        self.assertEqual(data["resolution"], "valid_suspended_resident")
        self.assertEqual(data["resident_state"], "suspended")
        self.assertEqual(data["validity"], "valid")
        self.assertFalse(data["boot_allowed"])

    def test_registered_charter_404_is_invalid_registry_entry(self) -> None:
        mapping = _base_mapping()
        mapping["realm/agents/constitutional-steward/charter"] = RealmAgentPathMissing(
            "realm/agents/constitutional-steward/charter"
        )

        _, data, ledger = self._call_get(mapping, "constitutional-steward")

        self.assertEqual(data["governance_status"], "invalid_governance_state")
        self.assertEqual(data["resolution"], "invalid_registry_entry")
        self.assertEqual(data["validity"], "invalid")
        self.assertFalse(data["boot_allowed"])
        self.assertEqual(
            [issue["code"] for issue in data["issues"]], ["charter_missing"]
        )
        self.assertEqual(len(ledger), 3)

    def test_duplicate_rows_are_retained_and_globally_deny_boot(self) -> None:
        mapping = _base_mapping(_registry(_row("same-agent"), _row("same-agent")))
        mapping.pop("realm/agents/constitutional-steward/charter")
        mapping["realm/agents/same-agent/charter"] = _artifact(
            STEWARD_ID,
            "realm/agents/same-agent/charter",
            _charter("same-agent"),
        )

        _, data, ledger = self._call_list(mapping)

        self.assertEqual(data["governance_status"], "invalid_governance_state")
        self.assertEqual([row["row_index"] for row in data["agents"]], [1, 2])
        self.assertTrue(all(row["validity"] == "invalid" for row in data["agents"]))
        self.assertTrue(all(not row["boot_allowed"] for row in data["agents"]))
        self.assertEqual(data["counts"]["invalid"], 2)
        self.assertEqual(
            [
                issue["row_index"]
                for issue in data["issues"]
                if issue["code"] == "registry_slug_duplicate"
            ],
            [1, 2],
        )
        self.assertEqual(ledger.count("realm/agents/same-agent/charter"), 2)

    def test_recoverable_invalid_row_forces_other_active_row_boot_false(self) -> None:
        malformed = "| `broken-agent` | Role only |"
        mapping = _base_mapping(_registry(_row("constitutional-steward"), malformed))

        _, data, _ = self._call_list(mapping)

        self.assertEqual(data["governance_status"], "invalid_governance_state")
        self.assertTrue(data["complete_for_registry"])
        self.assertEqual(len(data["agents"]), 2)
        self.assertEqual(data["agents"][0]["validity"], "valid")
        self.assertFalse(data["agents"][0]["boot_allowed"])
        self.assertEqual(data["agents"][1]["validity"], "invalid")
        self.assertEqual(
            [issue["code"] for issue in data["agents"][1]["issues"]],
            ["registry_row_malformed", "registry_required_field_missing"],
        )

        _, get_data, _ = self._call_get(mapping, "constitutional-steward")
        self.assertEqual(get_data["resolution"], "invalid_governance_state")
        self.assertEqual(get_data["validity"], "unknown")
        self.assertFalse(get_data["boot_allowed"])

    def test_unparseable_header_returns_no_rows_counts_or_charter_calls(self) -> None:
        mapping = _base_mapping(
            _registry(_row("constitutional-steward"), header="| slug | role |")
        )

        _, data, ledger = self._call_list(mapping)

        self.assertEqual(data["governance_status"], "invalid_governance_state")
        self.assertEqual(data["agents"], [])
        self.assertIsNone(data["counts"])
        self.assertFalse(data["complete_for_registry"])
        self.assertEqual(
            [issue["code"] for issue in data["issues"]], ["registry_unparseable"]
        )
        self.assertEqual(
            ledger, [realm_agents.CONSTITUTION_PATH, realm_agents.REGISTRY_PATH]
        )

    def test_required_field_and_unsupported_state_have_ordered_distinct_codes(
        self,
    ) -> None:
        mapping = _base_mapping(_registry(_row("odd-agent", role="", state="unknown")))
        mapping.pop("realm/agents/constitutional-steward/charter")
        mapping["realm/agents/odd-agent/charter"] = _artifact(
            STEWARD_ID,
            "realm/agents/odd-agent/charter",
            _charter("odd-agent"),
        )

        _, data, _ = self._call_list(mapping)

        self.assertEqual(
            [issue["code"] for issue in data["agents"][0]["issues"]],
            ["registry_required_field_missing", "resident_state_unsupported"],
        )
        self.assertIsNone(data["agents"][0]["resident_state"])

    def test_charter_invalidity_families_are_closed_and_fail_closed(self) -> None:
        cases: list[tuple[str, dict, str]] = []

        unparseable = _base_mapping()
        unparseable["realm/agents/constitutional-steward/charter"] = _artifact(
            STEWARD_ID,
            "realm/agents/constitutional-steward/charter",
            "# no required metadata",
        )
        cases.append(("unparseable", unparseable, "charter_unparseable"))

        duplicate_metadata = _base_mapping()
        duplicate_metadata["realm/agents/constitutional-steward/charter"] = _artifact(
            STEWARD_ID,
            "realm/agents/constitutional-steward/charter",
            _charter("constitutional-steward") + "\n**Slug:** `constitutional-steward`",
        )
        cases.append(("duplicate_metadata", duplicate_metadata, "charter_unparseable"))

        path_mismatch = _base_mapping()
        path_mismatch["realm/agents/constitutional-steward/charter"] = _artifact(
            STEWARD_ID,
            "realm/agents/constitutional-steward/charter",
            _charter("constitutional-steward", path="realm/agents/other/charter"),
        )
        cases.append(("path", path_mismatch, "charter_path_mismatch"))

        slug_mismatch = _base_mapping()
        slug_mismatch["realm/agents/constitutional-steward/charter"] = _artifact(
            STEWARD_ID,
            "realm/agents/constitutional-steward/charter",
            _charter("other-agent", path="realm/agents/constitutional-steward/charter"),
        )
        cases.append(("slug", slug_mismatch, "charter_slug_mismatch"))

        realm_mismatch = _base_mapping()
        realm_mismatch["realm/agents/constitutional-steward/charter"] = _artifact(
            STEWARD_ID,
            "realm/agents/constitutional-steward/charter",
            _charter(
                "constitutional-steward",
                realm_id="11111111-1111-1111-1111-111111111111",
            ),
        )
        cases.append(("realm", realm_mismatch, "charter_realm_mismatch"))

        scope_mismatch = _base_mapping()
        scope_mismatch["realm/agents/constitutional-steward/charter"] = _artifact(
            STEWARD_ID,
            "realm/agents/constitutional-steward/charter",
            _charter("constitutional-steward"),
            scope_kind="entity",
        )
        cases.append(("scope", scope_mismatch, "charter_realm_mismatch"))

        for label, mapping, expected_code in cases:
            with self.subTest(label=label):
                _, data, _ = self._call_get(mapping, "constitutional-steward")
                self.assertEqual(data["resolution"], "invalid_registry_entry")
                self.assertIn(
                    expected_code, [issue["code"] for issue in data["issues"]]
                )
                self.assertFalse(data["boot_allowed"])

    def test_invalid_registry_charter_path_is_never_called_but_other_rows_continue(
        self,
    ) -> None:
        mapping = _base_mapping(
            _registry(
                _row("bad-path", charter_path="realm/agents/other/charter"),
                _row("constitutional-steward"),
            )
        )

        _, data, ledger = self._call_list(mapping)

        self.assertEqual(data["governance_status"], "invalid_governance_state")
        self.assertNotIn("realm/agents/other/charter", ledger)
        self.assertIn("realm/agents/constitutional-steward/charter", ledger)
        self.assertIn(
            "charter_path_mismatch",
            [issue["code"] for issue in data["agents"][0]["issues"]],
        )

    def test_governance_404_variants_stop_in_exact_position(self) -> None:
        constitution_missing = _base_mapping()
        constitution_missing[realm_agents.CONSTITUTION_PATH] = RealmAgentPathMissing(
            realm_agents.CONSTITUTION_PATH
        )
        _, data, ledger = self._call_list(constitution_missing)
        self.assertEqual(data["governance_status"], "governance_unavailable")
        self.assertEqual(
            [issue["code"] for issue in data["issues"]], ["constitution_missing"]
        )
        self.assertEqual(ledger, [realm_agents.CONSTITUTION_PATH])

        registry_missing = _base_mapping()
        registry_missing[realm_agents.REGISTRY_PATH] = RealmAgentPathMissing(
            realm_agents.REGISTRY_PATH
        )
        _, data, ledger = self._call_list(registry_missing)
        self.assertEqual(data["governance_status"], "governance_unavailable")
        self.assertEqual(
            [issue["code"] for issue in data["issues"]], ["registry_missing"]
        )
        self.assertEqual(
            ledger, [realm_agents.CONSTITUTION_PATH, realm_agents.REGISTRY_PATH]
        )

    def test_every_dependency_kind_uses_same_label_and_stops_later_calls(self) -> None:
        kinds = [
            "authentication",
            "authorization",
            "timeout",
            "network",
            "backend_error",
            "invalid_response",
        ]
        for kind in kinds:
            with self.subTest(kind=kind):
                mapping = _base_mapping()
                mapping[realm_agents.REGISTRY_PATH] = RealmAgentDependencyFailure(
                    kind,
                    realm_agents.REGISTRY_PATH,
                    401 if kind == "authentication" else None,
                )
                result, data, ledger = self._call_get(mapping, "constitutional-steward")
                self.assertEqual(result.count(realm_agents.GET_LABEL), 1)
                self.assertEqual(data["governance_status"], "dependency_error")
                self.assertEqual(data["resolution"], "dependency_error")
                self.assertEqual(data["dependency"]["kind"], kind)
                self.assertFalse(data["complete_for_registry"])
                self.assertEqual(
                    ledger, [realm_agents.CONSTITUTION_PATH, realm_agents.REGISTRY_PATH]
                )
                self.assertNotIn("SECRET CONSTITUTION BODY", result)

    def test_input_validation_is_pre_call_and_case_only_slug_is_not_aliased(
        self,
    ) -> None:
        invalid_list = [
            ("", "realm_id_required"),
            (" ", "realm_id_required"),
            ("not-a-uuid", "realm_id_invalid_uuid"),
            (f" {REALM_ID}", "realm_id_invalid_uuid"),
            (REALM_ID + " ", "realm_id_invalid_uuid"),
        ]
        for realm_id, expected_code in invalid_list:
            with self.subTest(realm_id=realm_id), patch.object(
                api_resources, "_read_accepted_memory_artifact_data"
            ) as read:
                result = api_resources.list_realm_agents(realm_id)
                data = _parse(result, realm_agents.LIST_LABEL)
                read.assert_not_called()
                self.assertEqual(data["governance_status"], "input_error")
                self.assertEqual(
                    [issue["code"] for issue in data["issues"]], [expected_code]
                )

        invalid_slugs = [
            "",
            " ",
            "two words",
            "bad_slug",
            ".",
            "..",
            "a/b",
            "a\\b",
            "a%2Fb",
            "x" * 65,
        ]
        for slug in invalid_slugs:
            with self.subTest(slug=slug), patch.object(
                api_resources, "_read_accepted_memory_artifact_data"
            ) as read:
                result = api_resources.get_realm_agent(REALM_ID, slug)
                data = _parse(result, realm_agents.GET_LABEL)
                read.assert_not_called()
                self.assertEqual(data["governance_status"], "input_error")
                expected_code = (
                    "slug_required" if not slug.strip() else "slug_invalid_format"
                )
                self.assertEqual(
                    [issue["code"] for issue in data["issues"]], [expected_code]
                )

        _, data, ledger = self._call_get(_base_mapping(), "Constitutional-Steward")
        self.assertEqual(data["resolution"], "not_registered")
        self.assertEqual(ledger[-1], "realm/agents/Constitutional-Steward/charter")

    def test_uppercase_uuid_is_canonicalized_for_calls_and_output(self) -> None:
        upper = REALM_ID.upper()
        ledger: list[tuple[str, str]] = []
        mapping = _base_mapping()

        def reader(realm_id: str, path: str):
            ledger.append((realm_id, path))
            value = mapping[path]
            return value

        with patch.object(
            api_resources, "_read_accepted_memory_artifact_data", side_effect=reader
        ):
            result = api_resources.list_realm_agents(upper)
        data = _parse(result, realm_agents.LIST_LABEL)
        self.assertEqual(data["realm_id"], REALM_ID)
        self.assertTrue(all(realm_id == REALM_ID for realm_id, _ in ledger))

    def test_registry_row_bound_stops_before_fanout(self) -> None:
        rows = [_row(f"agent-{index}") for index in range(33)]
        mapping = _base_mapping(_registry(*rows))

        _, data, ledger = self._call_list(mapping)

        self.assertEqual(
            [issue["code"] for issue in data["issues"]],
            ["registry_size_limit_exceeded"],
        )
        self.assertEqual(data["agents"], [])
        self.assertIsNone(data["counts"])
        self.assertFalse(data["complete_for_registry"])
        self.assertEqual(
            ledger, [realm_agents.CONSTITUTION_PATH, realm_agents.REGISTRY_PATH]
        )

    def test_maximum_registry_fanout_is_exactly_two_plus_n(self) -> None:
        rows = [_row(f"agent-{index}") for index in range(32)]
        mapping = _base_mapping(_registry(*rows))
        mapping.pop("realm/agents/constitutional-steward/charter")
        for index in range(32):
            slug = f"agent-{index}"
            path = f"realm/agents/{slug}/charter"
            mapping[path] = _artifact(
                f"00000000-0000-0000-0000-{index:012d}", path, _charter(slug)
            )

        _, data, ledger = self._call_list(mapping)

        self.assertEqual(data["governance_status"], "valid")
        self.assertEqual(len(ledger), 34)
        self.assertEqual(data["counts"]["registry_entries"], 32)

        _, get_data, get_ledger = self._call_get(mapping, "absent-agent")
        self.assertEqual(get_data["resolution"], "not_registered")
        self.assertEqual(len(get_ledger), 35)
        self.assertEqual(get_ledger[-1], "realm/agents/absent-agent/charter")

    def test_full_result_byte_bound_replaces_oversize_with_compact_error(self) -> None:
        huge_role = "Р" * 3000
        mapping = _base_mapping(
            _registry(_row("constitutional-steward", role=huge_role))
        )

        with patch.object(realm_agents, "MAX_RESULT_BYTES", 700):
            result, data, _ = self._call_list(mapping)

        self.assertLessEqual(len(result.encode("utf-8")), 700)
        self.assertEqual(data["governance_status"], "invalid_governance_state")
        self.assertEqual(
            [issue["code"] for issue in data["issues"]],
            ["response_size_limit_exceeded"],
        )
        self.assertEqual(data["agents"], [])
        self.assertFalse(data["complete_for_registry"])

    def test_closed_vocabularies_and_complete_semantics(self) -> None:
        allowed_status = {
            "valid",
            "invalid_governance_state",
            "governance_unavailable",
            "dependency_error",
            "input_error",
        }
        allowed_validity = {"valid", "invalid"}
        allowed_states = {"active", "suspended", None}
        _, data, _ = self._call_list(_base_mapping())
        self.assertIn(data["governance_status"], allowed_status)
        for row in data["agents"]:
            self.assertIn(row["validity"], allowed_validity)
            self.assertIn(row["resident_state"], allowed_states)
        self.assertTrue(data["complete_for_registry"])

        _, unavailable, _ = self._call_list(
            {
                realm_agents.CONSTITUTION_PATH: RealmAgentPathMissing(
                    realm_agents.CONSTITUTION_PATH
                )
            }
        )
        self.assertFalse(unavailable["complete_for_registry"])

    def test_transport_loader_uses_only_exact_endpoint_and_payload(self) -> None:
        captured: dict[str, object] = {}

        class Response:
            status_code = 200

            def json(self):
                return _artifact(
                    STEWARD_ID,
                    "realm/agents/test-agent/charter",
                    _charter("test-agent"),
                )

        def request(method, url, *, json=None, headers=None, timeout=None, **kwargs):
            captured.update(
                method=method,
                url=url,
                json=json,
                headers=headers,
                timeout=timeout,
                kwargs=kwargs,
            )
            return Response()

        with patch.object(
            api_resources, "ONTO_API_BASE", "https://onto.example/api/core"
        ), patch.object(
            api_resources, "_onto_headers", return_value={"X-API-Key": "secret"}
        ), patch.object(
            sys.modules["requests"], "request", side_effect=request
        ):
            data = api_resources._read_accepted_memory_artifact_data(
                REALM_ID,
                "realm/agents/test-agent/charter",
            )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(
            captured["url"],
            f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/artifact/path",
        )
        self.assertEqual(
            captured["json"], {"artifact_path": "realm/agents/test-agent/charter"}
        )
        self.assertEqual(captured["timeout"], 30)
        self.assertEqual(data["artifact_id"], STEWARD_ID)

    def test_transport_loader_classifies_404_statuses_and_invalid_response(
        self,
    ) -> None:
        class Response:
            def __init__(self, status: int, payload: object) -> None:
                self.status_code = status
                self.payload = payload

            def json(self):
                if isinstance(self.payload, Exception):
                    raise self.payload
                return self.payload

        cases = [
            (404, {}, RealmAgentPathMissing, None),
            (401, {}, RealmAgentDependencyFailure, "authentication"),
            (403, {}, RealmAgentDependencyFailure, "authorization"),
            (500, {}, RealmAgentDependencyFailure, "backend_error"),
            (
                200,
                ValueError("bad json"),
                RealmAgentDependencyFailure,
                "invalid_response",
            ),
            (
                200,
                {"artifact_id": "only"},
                RealmAgentDependencyFailure,
                "invalid_response",
            ),
            (
                200,
                _artifact(
                    STEWARD_ID,
                    "realm/agents/test-agent/charter",
                    _charter("test-agent"),
                    status="draft",
                ),
                RealmAgentDependencyFailure,
                "invalid_response",
            ),
        ]
        for status, payload, expected_type, expected_kind in cases:
            with self.subTest(status=status, payload=payload), patch.object(
                api_resources, "_onto_headers", return_value={"X-API-Key": "secret"}
            ), patch.object(
                sys.modules["requests"],
                "request",
                return_value=Response(status, payload),
            ):
                with self.assertRaises(expected_type) as caught:
                    api_resources._read_accepted_memory_artifact_data(
                        REALM_ID, realm_agents.REGISTRY_PATH
                    )
                if expected_kind is not None:
                    self.assertEqual(caught.exception.kind, expected_kind)

    def test_transport_loader_classifies_authentication_timeout_and_network_without_raw_errors(
        self,
    ) -> None:
        with patch.object(
            api_resources,
            "_onto_headers",
            side_effect=RuntimeError("secret auth detail"),
        ):
            with self.assertRaises(RealmAgentDependencyFailure) as caught:
                api_resources._read_accepted_memory_artifact_data(
                    REALM_ID, realm_agents.CONSTITUTION_PATH
                )
        self.assertEqual(caught.exception.kind, "authentication")

        transport_cases = [
            (
                sys.modules["requests"].exceptions.Timeout("secret timeout detail"),
                "timeout",
            ),
            (
                sys.modules["requests"].exceptions.ConnectionError(
                    "secret network detail"
                ),
                "network",
            ),
        ]
        for failure, expected_kind in transport_cases:
            with self.subTest(kind=expected_kind), patch.object(
                api_resources, "_onto_headers", return_value={"X-API-Key": "secret"}
            ), patch.object(sys.modules["requests"], "request", side_effect=failure):
                with self.assertRaises(RealmAgentDependencyFailure) as caught:
                    api_resources._read_accepted_memory_artifact_data(
                        REALM_ID, realm_agents.REGISTRY_PATH
                    )
            self.assertEqual(caught.exception.kind, expected_kind)
            self.assertNotIn("secret", str(caught.exception))

    def test_tool_level_timeout_keeps_tool_specific_json_framing(self) -> None:
        ledger: list[str] = []

        class Response:
            status_code = 200

            def json(self):
                return _base_mapping()[realm_agents.CONSTITUTION_PATH]

        def slow_request(
            method, url, *, json=None, headers=None, timeout=None, **kwargs
        ):
            ledger.append(json["artifact_path"])
            time.sleep(0.05)
            return Response()

        with patch.object(
            api_resources, "_HTTP_MCP_TOOL_TIMEOUT_SECONDS", 0.001
        ), patch.object(
            api_resources, "_onto_headers", return_value={"X-API-Key": "secret"}
        ), patch.object(
            sys.modules["requests"], "request", side_effect=slow_request
        ):
            result = api_resources.get_realm_agent(REALM_ID, "constitutional-steward")

        data = _parse(result, realm_agents.GET_LABEL)
        self.assertEqual(data["governance_status"], "dependency_error")
        self.assertEqual(data["resolution"], "dependency_error")
        self.assertEqual(data["dependency"]["kind"], "timeout")
        self.assertEqual(
            data["dependency"]["operation"], "read_accepted_artifact_by_path"
        )
        time.sleep(0.06)
        self.assertEqual(ledger, [realm_agents.CONSTITUTION_PATH])


if __name__ == "__main__":
    unittest.main()
