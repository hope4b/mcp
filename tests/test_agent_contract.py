from __future__ import annotations

import ast
import inspect
import re
import sys
import types
import unittest
from pathlib import Path

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _HTTPError(Exception):
        def __init__(self, response=None) -> None:
            super().__init__("stub http error")
            self.response = response

    class _RequestsExceptions:
        HTTPError = _HTTPError

    def _unexpected_request(*args, **kwargs):
        raise AssertionError("requests.request should not be called in these tests")

    requests_stub.exceptions = _RequestsExceptions()
    requests_stub.request = _unexpected_request
    sys.modules["requests"] = requests_stub

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

from onto_mcp import api_resources
from onto_mcp.agent_contract import _requirement_present, build_how_to_response, get_agent_contract


REPO_ROOT = Path(__file__).resolve().parents[1]
REALM_ID = "000ba00a-00a0-0a00-a000-000a0a0a0aa3"


def _registered_tool_names() -> list[str]:
    source = (REPO_ROOT / "onto_mcp" / "api_resources.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    names: list[str] = []
    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Attribute)
                and isinstance(decorator.value, ast.Name)
                and decorator.value.id == "mcp"
                and decorator.attr == "tool"
            ):
                names.append(node.name)
    return names


def _next_tools(response: dict) -> list[str]:
    return [call["tool"] for call in response["next_calls"]]


def _avoid_tools(response: dict) -> set[str]:
    return set(response.get("avoid_tools", []))


def _call_for(response: dict, tool_name: str) -> dict:
    for call in response["next_calls"]:
        if call["tool"] == tool_name:
            return call
    raise AssertionError(f"{tool_name} not found in next_calls: {response['next_calls']}")


def _missing_arg_sources(call: dict) -> dict[str, str]:
    return {item["arg"]: item["get_with_tool"] for item in call["missing_args"]}


class AgentContractTests(unittest.TestCase):
    def test_registered_tools_are_covered_by_contract_once(self) -> None:
        contract = get_agent_contract()
        registered_tools = set(_registered_tool_names())
        contract_tools = set(contract["tool_contract"])
        family_tools = [
            tool_name
            for family in contract["tool_families"].values()
            for tool_name in family["tools"]
        ]

        self.assertEqual(registered_tools, contract_tools)
        self.assertEqual(contract_tools, set(family_tools))
        self.assertEqual(len(family_tools), len(set(family_tools)))

    def test_guide_markers_match_contract(self) -> None:
        contract = get_agent_contract()
        guide = (REPO_ROOT / "docs" / "AGENT_ENTRY_GUIDE.md").read_text(encoding="utf-8")

        version_match = re.search(r"contract-version: ([^ ]+) -->", guide)
        count_match = re.search(r"contract-tool-count: ([0-9]+) -->", guide)

        self.assertIsNotNone(version_match)
        self.assertIsNotNone(count_match)
        self.assertEqual(version_match.group(1), contract["contract_version"])
        self.assertEqual(int(count_match.group(1)), len(contract["tool_contract"]))

    def test_public_tool_signature_and_docstring_are_agent_first(self) -> None:
        signature = inspect.signature(api_resources.how_to_use_onto_mcp)

        self.assertEqual(list(signature.parameters), ["question", "safety_mode"])
        self.assertIn("Call this first before other Onto MCP tools", api_resources.how_to_use_onto_mcp.__doc__)
        self.assertIn("user goal and known inputs", api_resources.how_to_use_onto_mcp.__doc__)

    def test_response_is_agent_shaped_not_family_classifier_shaped(self) -> None:
        response = api_resources.how_to_use_onto_mcp("Goal: find an object by name. Known inputs: object name only.")

        self.assertIn("answer", response)
        self.assertIn("next_calls", response)
        self.assertNotIn("tool_families", response)
        self.assertNotIn("classification", response)
        for call in response["next_calls"]:
            self.assertEqual(set(call), {"step", "tool", "purpose", "params", "missing_args"})

    def test_manage_templates_read_only_starts_with_realms_and_avoids_mutation(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: manage templates. Known inputs: none. Need next Onto MCP calls.",
            "read_only",
        )

        self.assertEqual(_next_tools(response)[0], "list_available_realms")
        self.assertIn("search_templates", _next_tools(response))
        self.assertIn("save_template", _avoid_tools(response))
        self.assertIn("delete_template", _avoid_tools(response))
        self.assertNotIn("save_template", _next_tools(response))
        self.assertNotIn("delete_template", _next_tools(response))
        self.assertTrue(any("read_only mode" in note for note in response["safety_notes"]))

    def test_find_object_by_name_routes_realm_then_object_entity_search(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: find an object by name. Known inputs: object name only. Need safe first calls.",
            "read_only",
        )

        self.assertEqual(_next_tools(response)[0], "list_available_realms")
        self.assertIn("search_objects", _next_tools(response))
        self.assertIn("search_entities", _next_tools(response))
        search_objects_call = _call_for(response, "search_objects")
        self.assertEqual(_missing_arg_sources(search_objects_call)["realm_id"], "list_available_realms")
        self.assertNotIn("save_entity", _next_tools(response))

    def test_find_object_by_field_value_routes_to_field_search_tool(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: find vendor object by INN field value 1215156909. Known inputs: realm name and template name.",
            "read_only",
        )

        self.assertEqual(_next_tools(response)[0], "list_available_realms")
        self.assertIn("search_templates", _next_tools(response))
        self.assertIn("get_template", _next_tools(response))
        self.assertIn("search_entities_by_fields", _next_tools(response))
        field_search_call = _call_for(response, "search_entities_by_fields")
        missing_sources = _missing_arg_sources(field_search_call)
        self.assertEqual(missing_sources["realm_id"], "list_available_realms")
        self.assertEqual(missing_sources["field_filters"], "get_template")
        self.assertNotIn("save_entity", _next_tools(response))

    def test_update_diagram_routes_read_discovery_before_write(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: update a diagram. Known inputs: diagram name only. Need required IDs and next calls.",
            "read_only",
        )

        self.assertEqual(_next_tools(response)[0], "list_available_realms")
        self.assertIn("search_diagrams", _next_tools(response))
        self.assertIn("get_diagram", _next_tools(response))
        self.assertNotIn("update_diagram", _next_tools(response))
        self.assertIn("update_diagram", _avoid_tools(response))
        get_diagram_call = _call_for(response, "get_diagram")
        self.assertEqual(_missing_arg_sources(get_diagram_call)["diagram_id"], "search_diagrams")
        self.assertTrue(any("write_intent" in note for note in response["safety_notes"]))

    def test_delete_template_name_only_does_not_route_delete(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: delete a template. Known inputs: template name only. Need safe next calls.",
            "destructive_intent",
        )

        self.assertEqual(_next_tools(response)[0], "list_available_realms")
        self.assertIn("search_templates", _next_tools(response))
        self.assertIn("get_template", _next_tools(response))
        self.assertNotIn("delete_template", _next_tools(response))
        self.assertIn("delete_template", _avoid_tools(response))
        self.assertIn("clarifying_question", response)
        self.assertTrue(any("exact realm_id and template_id" in note for note in response["safety_notes"]))
        self.assertTrue(any("explicit operator confirmation" in note for note in response["safety_notes"]))

    def test_memory_artifact_read_with_realm_and_entity_id_does_not_become_ambiguous(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: read MemoryArtifact handoff for realm_id=7ac494c7-fd91-47e7-bb2b-f62c8a3c7073 "
            "and target entity_id=779d76ca-c037-45af-8d6b-d919f2eecbc5.",
            "read_only",
        )

        self.assertIn("search_memory_artifacts", _next_tools(response))
        self.assertNotIn("search_objects", _next_tools(response))
        self.assertNotIn("create_memory_artifact_draft", _next_tools(response))
        self.assertNotIn("Which route should be used", response.get("clarifying_question", ""))

    def test_realm_agent_list_intent_routes_only_to_dedicated_list_tool(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: list realm agents. Known input: "
            "realm_id=000ba00a-00a0-0a00-a000-000a0a0a0aa3.",
            "read_only",
        )

        self.assertEqual(_next_tools(response), ["list_realm_agents"])
        list_call = _call_for(response, "list_realm_agents")
        self.assertEqual(list_call["params"]["realm_id"], "000ba00a-00a0-0a00-a000-000a0a0a0aa3")
        self.assertEqual(list_call["missing_args"], [])
        self.assertNotIn("search_memory_artifacts", _next_tools(response))
        self.assertNotIn("search_agent_memory", _next_tools(response))
        self.assertNotIn("list_available_realms", _next_tools(response))

    def test_realm_agent_boot_intent_routes_only_to_exact_slug_tool(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: decide whether realm agent can boot. Known inputs: "
            "realm_id=000ba00a-00a0-0a00-a000-000a0a0a0aa3; slug=QA-Agent.",
            "read_only",
        )

        self.assertEqual(_next_tools(response), ["get_realm_agent"])
        get_call = _call_for(response, "get_realm_agent")
        self.assertEqual(get_call["params"]["realm_id"], "000ba00a-00a0-0a00-a000-000a0a0a0aa3")
        self.assertEqual(get_call["params"]["slug"], "QA-Agent")
        self.assertEqual(get_call["missing_args"], [])
        self.assertNotIn("search_memory_artifacts", _next_tools(response))
        self.assertNotIn("search_agent_memory", _next_tools(response))
        self.assertNotIn("list_realm_agents", _next_tools(response))

    def test_realm_agent_routes_report_only_their_required_missing_inputs(self) -> None:
        list_response = api_resources.how_to_use_onto_mcp(
            "Goal: which agents are registered in this realm?",
            "read_only",
        )
        get_response = api_resources.how_to_use_onto_mcp(
            "Goal: can this realm agent boot?",
            "read_only",
        )

        self.assertEqual(_next_tools(list_response), ["list_realm_agents"])
        self.assertEqual(
            _missing_arg_sources(_call_for(list_response, "list_realm_agents")),
            {"realm_id": "list_available_realms"},
        )
        self.assertEqual(_next_tools(get_response), ["get_realm_agent"])
        self.assertEqual(
            _missing_arg_sources(_call_for(get_response, "get_realm_agent")),
            {"realm_id": "list_available_realms", "slug": "user_input"},
        )

    def test_realm_agent_bootstrap_prefix_routes_ru_and_en_four_call_plan(self) -> None:
        questions = [
            f'realm_id = {REALM_ID}; my_slug = analyst; directive = "Прочти realm/agents/constitution '
            'и realm/agents/registry, найди себя, действуй по своему чартеру"',
            f"Recover the realm agent bootstrap prefix: read constitution and registry, validate my_slug=analyst, "
            f"and read its charter in realm_id={REALM_ID}.",
        ]
        for question in questions:
            with self.subTest(question=question):
                response = api_resources.how_to_use_onto_mcp(question, "read_only")
                self.assertEqual(
                    _next_tools(response),
                    [
                        "get_memory_artifact_by_path",
                        "get_memory_artifact_by_path",
                        "get_realm_agent",
                        "get_memory_artifact_by_path",
                    ],
                )
                self.assertEqual(
                    [call["params"]["artifact_path"] for call in (response["next_calls"][0], response["next_calls"][1])],
                    ["realm/agents/constitution", "realm/agents/registry"],
                )
                self.assertEqual(response["next_calls"][2]["params"], {"realm_id": REALM_ID, "slug": "analyst"})
                self.assertEqual(
                    response["next_calls"][3]["params"]["artifact_path"],
                    "realm/agents/analyst/charter",
                )
                self.assertIn("valid_active_resident", response["next_calls"][3]["purpose"])
                self.assertIn("bootstrap_prefix_complete", response["answer"])
                self.assertIn("does not inspect the charter", response["answer"])

    def test_realm_agent_identity_and_charter_routes_ru_and_en_two_calls(self) -> None:
        questions = [
            f"Проверь slug=analyst и прочитай его чартер в realm_id={REALM_ID}",
            f"Validate realm agent slug=analyst and read its charter in realm_id={REALM_ID}",
        ]
        for question in questions:
            with self.subTest(question=question):
                response = api_resources.how_to_use_onto_mcp(question, "read_only")
                self.assertEqual(_next_tools(response), ["get_realm_agent", "get_memory_artifact_by_path"])
                self.assertEqual(response["next_calls"][0]["params"]["slug"], "analyst")
                self.assertEqual(
                    response["next_calls"][1]["params"]["artifact_path"],
                    "realm/agents/analyst/charter",
                )
                self.assertNotIn("realm/agents/constitution", str(response["next_calls"]))
                self.assertIn("Every other result stops", response["answer"])

    def test_realm_agent_ru_list_and_identity_remain_one_call(self) -> None:
        list_response = api_resources.how_to_use_onto_mcp(
            f"Покажи список агентов пространства realm_id={REALM_ID}", "read_only"
        )
        identity_response = api_resources.how_to_use_onto_mcp(
            f"Проверь, может ли агент со slug=analyst загрузиться в realm_id={REALM_ID}", "read_only"
        )
        self.assertEqual(_next_tools(list_response), ["list_realm_agents"])
        self.assertEqual(_next_tools(identity_response), ["get_realm_agent"])
        self.assertEqual(identity_response["next_calls"][0]["params"]["slug"], "analyst")

    def test_realm_agent_bootstrap_missing_inputs_have_exact_plans(self) -> None:
        missing_realm = api_resources.how_to_use_onto_mcp(
            "Bootstrap prefix: read constitution and registry, validate my_slug=analyst, and read charter.",
            "read_only",
        )
        self.assertEqual(
            _next_tools(missing_realm),
            ["get_memory_artifact_by_path", "get_memory_artifact_by_path", "get_realm_agent", "get_memory_artifact_by_path"],
        )
        for call in missing_realm["next_calls"]:
            self.assertNotIn("realm_id", call["params"])
            self.assertEqual(_missing_arg_sources(call)["realm_id"], "list_available_realms")
        self.assertEqual(
            missing_realm["clarifying_question"],
            "Provide the exact realm_id for the realm-agent bootstrap prefix.",
        )

        missing_slug = api_resources.how_to_use_onto_mcp(
            f"Bootstrap prefix realm_id={REALM_ID}: read constitution and registry and then the charter.",
            "read_only",
        )
        self.assertEqual(
            _next_tools(missing_slug),
            ["get_memory_artifact_by_path", "get_memory_artifact_by_path", "get_realm_agent"],
        )
        self.assertEqual(_missing_arg_sources(missing_slug["next_calls"][2]), {"slug": "user_input"})
        self.assertEqual(
            missing_slug["clarifying_question"],
            "Provide the exact case-sensitive my_slug (or slug) to validate.",
        )

        missing_both = api_resources.how_to_use_onto_mcp(
            "Bootstrap prefix: read constitution and registry and then the charter.", "read_only"
        )
        self.assertEqual(
            _next_tools(missing_both),
            ["get_memory_artifact_by_path", "get_memory_artifact_by_path", "get_realm_agent"],
        )
        self.assertEqual(
            _missing_arg_sources(missing_both["next_calls"][2]),
            {"realm_id": "list_available_realms", "slug": "user_input"},
        )
        self.assertEqual(
            missing_both["clarifying_question"],
            "Provide the exact realm_id and exact case-sensitive my_slug (or slug) for the realm-agent bootstrap prefix.",
        )
        self.assertNotIn("list_available_realms", _next_tools(missing_realm) + _next_tools(missing_slug) + _next_tools(missing_both))

    def test_realm_agent_short_routes_apply_exact_missing_input_transform(self) -> None:
        list_response = api_resources.how_to_use_onto_mcp("Which realm agents are registered?", "read_only")
        self.assertEqual(_next_tools(list_response), ["list_realm_agents"])
        self.assertEqual(list_response["clarifying_question"], "Provide the exact realm_id for realm-agent discovery.")

        identity_response = api_resources.how_to_use_onto_mcp("Can this realm agent boot?", "read_only")
        self.assertEqual(_next_tools(identity_response), ["get_realm_agent"])
        self.assertEqual(
            _missing_arg_sources(identity_response["next_calls"][0]),
            {"realm_id": "list_available_realms", "slug": "user_input"},
        )
        self.assertEqual(
            identity_response["clarifying_question"],
            "Provide the exact realm_id and exact case-sensitive my_slug (or slug) for exact realm-agent validation.",
        )

        charter_response = api_resources.how_to_use_onto_mcp(
            f"Validate the realm agent and read its charter in realm_id={REALM_ID}", "read_only"
        )
        self.assertEqual(_next_tools(charter_response), ["get_realm_agent"])
        self.assertEqual(_missing_arg_sources(charter_response["next_calls"][0]), {"slug": "user_input"})

    def test_realm_agent_malformed_realm_fails_closed(self) -> None:
        for realm_value in ("not-a-uuid", '" 000ba00a-00a0-0a00-a000-000a0a0a0aa3 "'):
            with self.subTest(realm_value=realm_value):
                response = api_resources.how_to_use_onto_mcp(
                    f"Can realm agent slug=analyst boot in realm_id={realm_value}?", "read_only"
                )
                self.assertEqual(response["next_calls"], [])
                self.assertEqual(
                    response["clarifying_question"],
                    "Provide a canonical hyphenated realm_id UUID without surrounding whitespace.",
                )
                self.assertIn("Input error: realm_id_invalid_uuid.", response["safety_notes"])

    def test_realm_agent_slug_errors_are_fail_closed_and_bootstrap_keeps_only_governance_reads(self) -> None:
        cases = [
            ("my_slug=;", "slug_required", "Provide a non-empty exact case-sensitive my_slug (or slug)."),
            ("my_slug=bad_slug;", "slug_invalid_format", "Provide my_slug (or slug) as one 1-64 character case-sensitive ASCII path segment."),
            ("my_slug=bad/value;", "slug_invalid_format", "Provide my_slug (or slug) as one 1-64 character case-sensitive ASCII path segment."),
            ('my_slug="bad value";', "slug_invalid_format", "Provide my_slug (or slug) as one 1-64 character case-sensitive ASCII path segment."),
            (f"my_slug={'a' * 65};", "slug_invalid_format", "Provide my_slug (or slug) as one 1-64 character case-sensitive ASCII path segment."),
            ("my_slug=analyst; slug=mcp-owner;", "slug_conflict", "my_slug and slug conflict; provide one exact case-sensitive value."),
        ]
        for assignments, code, clarification in cases:
            with self.subTest(assignments=assignments):
                response = api_resources.how_to_use_onto_mcp(
                    f"Bootstrap prefix realm_id={REALM_ID}; {assignments} read constitution and registry and charter",
                    "read_only",
                )
                self.assertEqual(_next_tools(response), ["get_memory_artifact_by_path", "get_memory_artifact_by_path"])
                self.assertNotIn("get_realm_agent", _next_tools(response))
                self.assertNotIn("/charter", str(response["next_calls"]))
                self.assertEqual(response["clarifying_question"], clarification)
                self.assertIn(f"Input error: {code}.", response["safety_notes"])

    def test_realm_agent_missing_realm_plus_slug_error_emits_no_calls(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Bootstrap prefix my_slug=bad_slug; read constitution and registry and charter", "read_only"
        )
        self.assertEqual(response["next_calls"], [])
        self.assertEqual(
            response["clarifying_question"],
            "Provide the exact realm_id. Also provide my_slug (or slug) as one 1-64 character case-sensitive ASCII path segment.",
        )
        self.assertIn("Input error: slug_invalid_format.", response["safety_notes"])

    def test_realm_agent_normalizes_uuid_and_preserves_exact_slug_case(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Can realm agent my_slug=QA-Agent slug=QA-Agent boot in "
            "realm_id=000BA00A-00A0-0A00-A000-000A0A0A0AA3?",
            "read_only",
        )
        self.assertEqual(_next_tools(response), ["get_realm_agent"])
        self.assertEqual(response["next_calls"][0]["params"], {"realm_id": REALM_ID, "slug": "QA-Agent"})

    def test_realm_agent_realm_id_stops_at_ordinary_en_ru_continuation(self) -> None:
        questions = [
            f"Can realm agent slug=analyst boot in realm_id={REALM_ID} and report result",
            f"Проверь, может ли агент slug=analyst загрузиться в realm_id={REALM_ID} и сообщи результат",
        ]
        for question in questions:
            with self.subTest(question=question):
                response = api_resources.how_to_use_onto_mcp(question, "read_only")
                self.assertEqual(_next_tools(response), ["get_realm_agent"])
                self.assertEqual(
                    response["next_calls"][0]["params"],
                    {"realm_id": REALM_ID, "slug": "analyst"},
                )
                self.assertNotIn("clarifying_question", response)
                self.assertNotIn("Input error: realm_id_invalid_uuid.", response["safety_notes"])

    def test_realm_agent_realm_id_continuation_does_not_truncate_malformed_neighbors(self) -> None:
        malformed_values = [
            f"{REALM_ID}x and report result",
            f"{REALM_ID}/tail and report result",
            f"{REALM_ID}_tail и сообщи результат",
            f"{REALM_ID} and",
        ]
        for realm_value in malformed_values:
            with self.subTest(realm_value=realm_value):
                response = api_resources.how_to_use_onto_mcp(
                    f"Can realm agent slug=analyst boot in realm_id={realm_value}",
                    "read_only",
                )
                self.assertEqual(response["next_calls"], [])
                self.assertEqual(
                    response["clarifying_question"],
                    "Provide a canonical hyphenated realm_id UUID without surrounding whitespace.",
                )
                self.assertIn("Input error: realm_id_invalid_uuid.", response["safety_notes"])

    def test_realm_agent_route_precedence_preserves_generic_memory_and_broad_word_negatives(self) -> None:
        memory_response = api_resources.how_to_use_onto_mcp(
            f"artifact_path=realm/agents/constitution in realm_id={REALM_ID}", "read_only"
        )
        self.assertIn("get_memory_artifact_by_path", _next_tools(memory_response))
        self.assertNotIn("get_realm_agent", _next_tools(memory_response))
        path_call = _call_for(memory_response, "get_memory_artifact_by_path")
        self.assertEqual(path_call["params"]["artifact_path"], "realm/agents/constitution")
        self.assertEqual(path_call["params"]["realm_id"], REALM_ID)

        russian_path = api_resources.how_to_use_onto_mcp(
            f"Прочти MemoryArtifact artifact_path=realm/agents/registry в realm_id={REALM_ID}", "read_only"
        )
        self.assertEqual(
            _call_for(russian_path, "get_memory_artifact_by_path")["params"]["artifact_path"],
            "realm/agents/registry",
        )
        broad_response = api_resources.how_to_use_onto_mcp("Обнови реестр продаж", "read_only")
        self.assertNotIn("get_realm_agent", _next_tools(broad_response))
        self.assertNotIn("list_realm_agents", _next_tools(broad_response))

    def test_realm_agent_plans_are_read_only_and_do_not_claim_execution(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            f"Bootstrap prefix realm_id={REALM_ID}; my_slug=analyst; read constitution, registry, identity, and charter",
            "read_only",
        )
        forbidden_prefixes = ("create_", "save_", "update_", "append_", "submit_", "accept_", "revoke_", "supersede_", "delete_")
        self.assertFalse(any(tool.startswith(forbidden_prefixes) for tool in _next_tools(response)))
        self.assertNotIn("search_agent_memory", _next_tools(response))
        self.assertNotIn("create_node_chat_message", _next_tools(response))
        self.assertIn("does not", response["answer"])
        self.assertIn("launch an executor", response["answer"])

    def test_memory_only_intent_with_workspace_context_routes_memory(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: create a MemoryArtifact in workspace realm_id=7ac494c7-fd91-47e7-bb2b-f62c8a3c7073. "
            "Known inputs: artifact_path=qa/handoff; artifact_kind=handoff; write_mode=append; "
            "body=Ready body; summary=Ready summary; source_ref=thread-1; "
            "target_kind=realm; target_id=7ac494c7-fd91-47e7-bb2b-f62c8a3c7073; role=primary. "
            "Owner-approved write intent.",
            "write_intent",
        )

        self.assertIn("create_memory_artifact_draft", _next_tools(response))
        self.assertNotIn("create_realm", _next_tools(response))
        self.assertNotIn("Which route should be used", response.get("clarifying_question", ""))
        self.assertTrue(any("non-empty array of objects" in note for note in response["safety_notes"]))
        self.assertTrue(any("Do not pass targets as a JSON string" in note for note in response["safety_notes"]))

    def test_true_workspace_and_memory_multigoal_remains_ambiguous(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Create a workspace named QA and also create a MemoryArtifact in it.",
            "write_intent",
        )

        self.assertEqual(_next_tools(response), ["list_available_realms"])
        self.assertIn("Which route should be used: memory, workspace_setup?", response["clarifying_question"])
        self.assertIn("create_memory_artifact_draft", _avoid_tools(response))
        self.assertIn("create_realm", _avoid_tools(response))

    def test_memory_artifact_read_does_not_route_to_agent_memory_tools(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: read MemoryArtifact by artifact_id=98f35632-d4c1-424d-b80b-a7f4b34610c0 "
            "in realm_id=7ac494c7-fd91-47e7-bb2b-f62c8a3c7073.",
            "read_only",
        )

        self.assertIn("get_memory_artifact", _next_tools(response))
        self.assertNotIn("search_agent_memory", _next_tools(response))
        self.assertNotIn("get_agent_memory_record", _next_tools(response))
        self.assertIn("search_agent_memory", " ".join(response["safety_notes"]))

    def test_memory_artifact_path_read_prefers_accepted_path_lookup(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: read MemoryArtifact path artifact_path=nodes/119b58b3-7d37-4474-9216-a0220aa250d7/initiative/charter "
            "in realm_id=7ac494c7-fd91-47e7-bb2b-f62c8a3c7073.",
            "read_only",
        )

        self.assertIn("search_memory_artifacts", _next_tools(response))
        self.assertIn("get_memory_artifact_by_path", _next_tools(response))
        self.assertNotIn("search_agent_memory", _next_tools(response))
        path_call = _call_for(response, "get_memory_artifact_by_path")
        self.assertIn("accepted MemoryArtifact by path", path_call["purpose"])

    def test_memory_artifact_node_target_uses_supported_entity_target_kind(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: find MemoryArtifact for realm_id=7ac494c7-fd91-47e7-bb2b-f62c8a3c7073 "
            "target_kind=node target_id=779d76ca-c037-45af-8d6b-d919f2eecbc5.",
            "read_only",
        )

        search_call = _call_for(response, "search_memory_artifacts")
        self.assertEqual(search_call["params"]["target_kind"], "entity")
        self.assertNotIn("search_agent_memory", _next_tools(response))
        self.assertTrue(any("target_kind=entity" in note for note in response["safety_notes"]))

    def test_memory_artifact_owner_approved_lifecycle_routes_dedicated_sequence(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Route: memory. Goal: create MemoryArtifact draft, submit it, and accept it. "
            "Known inputs: realm_id=7ac494c7-fd91-47e7-bb2b-f62c8a3c7073; "
            "entity_id=779d76ca-c037-45af-8d6b-d919f2eecbc5; artifact_path=rso-ui/handoff; "
            "artifact_kind=handoff; write_mode=append; body=Ready body; summary=Ready summary; "
            "source_ref=thread-1. Owner-approved write intent.",
            "lifecycle_intent",
        )

        self.assertEqual(
            _next_tools(response),
            [
                "create_memory_artifact_draft",
                "get_memory_artifact",
                "submit_memory_artifact",
                "accept_memory_artifact",
                "get_memory_artifact_by_path",
            ],
        )
        self.assertNotIn("create_memory_artifact_draft", _avoid_tools(response))
        self.assertNotIn("submit_memory_artifact", _avoid_tools(response))
        self.assertNotIn("accept_memory_artifact", _avoid_tools(response))
        create_call = _call_for(response, "create_memory_artifact_draft")
        self.assertEqual(create_call["params"]["realm_id"], "7ac494c7-fd91-47e7-bb2b-f62c8a3c7073")
        self.assertEqual(create_call["params"]["targets"][0]["target_id"], "779d76ca-c037-45af-8d6b-d919f2eecbc5")
        self.assertNotIn("supersedes_artifact_id", create_call["params"])
        self.assertNotIn("clarifying_question", response)

    def test_reviewable_successor_carries_predecessor_through_create_then_review_lifecycle(self) -> None:
        predecessor_id = "123e4567-e89b-12d3-a456-426614174001"
        response = api_resources.how_to_use_onto_mcp(
            "Route: memory. Goal: create MemoryArtifact successor draft, submit it, and accept it. "
            "Known inputs: realm_id=7ac494c7-fd91-47e7-bb2b-f62c8a3c7073; "
            "entity_id=779d76ca-c037-45af-8d6b-d919f2eecbc5; artifact_path=realm/agents/constitution; "
            "artifact_kind=decision; write_mode=replace; body=Successor body; summary=Successor summary; "
            f"source_ref=thread-2; supersedes_artifact_id={predecessor_id}. Owner-approved lifecycle intent.",
            "lifecycle_intent",
        )

        self.assertEqual(
            _next_tools(response),
            [
                "create_memory_artifact_draft",
                "get_memory_artifact",
                "submit_memory_artifact",
                "accept_memory_artifact",
                "get_memory_artifact_by_path",
            ],
        )
        create_call = _call_for(response, "create_memory_artifact_draft")
        self.assertEqual(create_call["params"]["supersedes_artifact_id"], predecessor_id)
        self.assertNotIn("supersede_memory_artifact", _next_tools(response))
        self.assertTrue(any("do not substitute supersede_memory_artifact" in note for note in response["safety_notes"]))

    def test_memory_artifact_write_prompt_stays_read_only_without_write_safety_mode(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: create MemoryArtifact draft. Known inputs: realm_id=7ac494c7-fd91-47e7-bb2b-f62c8a3c7073; "
            "entity_id=779d76ca-c037-45af-8d6b-d919f2eecbc5; artifact_path=rso-ui/handoff; "
            "artifact_kind=handoff; write_mode=append; body=Ready body; summary=Ready summary; "
            "source_ref=thread-1. Owner-approved write intent.",
            "read_only",
        )

        self.assertEqual([], _next_tools(response))
        self.assertNotIn("create_memory_artifact_draft", _next_tools(response))
        self.assertIn("create_memory_artifact_draft", _avoid_tools(response))
        self.assertIn("clarifying_question", response)
        self.assertTrue(any("Do not substitute read-only search" in note for note in response["safety_notes"]))

    def test_owner_approved_bug_lifecycle_reclassification_routes_save_entity(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: reclassify bug lifecycle state from backlog to in work. Known inputs: "
            "realm_id=000ba00a-00a0-0a00-a000-000a0a0a0aa3; "
            "entity_id=34774bea-4603-41dd-8975-401f3de4f5ca; "
            "template_id=585e5353-a97d-4854-8a0e-5f8fe318c797. Owner-approved lifecycle transition.",
            "lifecycle_intent",
        )

        self.assertEqual(_next_tools(response), ["get_entity", "save_entity", "get_entity"])
        self.assertNotIn("Which route should be used", response.get("clarifying_question", ""))
        self.assertNotIn("save_entity", _avoid_tools(response))
        self.assertNotIn("save_entities_batch", _avoid_tools(response))
        save_call = _call_for(response, "save_entity")
        self.assertEqual(save_call["params"]["realm_id"], "000ba00a-00a0-0a00-a000-000a0a0a0aa3")
        self.assertEqual(save_call["params"]["entity_id"], "34774bea-4603-41dd-8975-401f3de4f5ca")
        self.assertEqual(save_call["params"]["meta_entity_id"], "585e5353-a97d-4854-8a0e-5f8fe318c797")
        self.assertEqual(_missing_arg_sources(save_call)["name"], "get_entity")

    def test_owner_approved_defect_creation_under_existing_bug_template_routes_save_entity(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal: create defect under an existing bug template. Known inputs: "
            "realm_id=000ba00a-00a0-0a00-a000-000a0a0a0aa3; "
            "meta_entity_id=fb9915fc-5fdb-4ce8-958e-8b2e19bcb949; "
            "name=how_to_use_onto_mcp routing defect; comment=Observed ambiguous route guidance. "
            "Owner-approved write intent.",
            "write_intent",
        )

        self.assertEqual(_next_tools(response), ["get_template", "save_entity", "get_entity"])
        self.assertNotIn("Which route should be used", response.get("clarifying_question", ""))
        self.assertNotIn("save_entity", _avoid_tools(response))
        save_call = _call_for(response, "save_entity")
        self.assertEqual(save_call["params"]["realm_id"], "000ba00a-00a0-0a00-a000-000a0a0a0aa3")
        self.assertEqual(save_call["params"]["meta_entity_id"], "fb9915fc-5fdb-4ce8-958e-8b2e19bcb949")
        self.assertEqual(save_call["params"]["name"], "how_to_use_onto_mcp routing defect")
        self.assertEqual(save_call["params"]["comment"], "Observed ambiguous route guidance")
        self.assertNotIn("create_template", _next_tools(response))
        self.assertNotIn("create_entities_batch", _next_tools(response))

    def test_bug_lifecycle_and_defect_prompts_stay_read_only_in_read_only_mode(self) -> None:
        reclass_response = api_resources.how_to_use_onto_mcp(
            "Goal: reclassify bug lifecycle state. Known inputs: "
            "realm_id=000ba00a-00a0-0a00-a000-000a0a0a0aa3; "
            "entity_id=34774bea-4603-41dd-8975-401f3de4f5ca; "
            "template_id=585e5353-a97d-4854-8a0e-5f8fe318c797. Owner-approved lifecycle transition.",
            "read_only",
        )
        create_response = api_resources.how_to_use_onto_mcp(
            "Goal: create defect under an existing bug template. Known inputs: "
            "realm_id=000ba00a-00a0-0a00-a000-000a0a0a0aa3; "
            "template_id=fb9915fc-5fdb-4ce8-958e-8b2e19bcb949; "
            "name=how_to_use_onto_mcp routing defect; comment=Observed ambiguous route guidance. "
            "Owner-approved write intent.",
            "read_only",
        )

        for response in (reclass_response, create_response):
            self.assertNotIn("save_entity", _next_tools(response))
            self.assertNotIn("save_entities_batch", _next_tools(response))
            self.assertNotIn("create_entities_batch", _next_tools(response))
            self.assertIn("save_entity", _avoid_tools(response))

    def test_unclear_goal_asks_clarifying_question_and_uses_safe_discovery_only(self) -> None:
        response = api_resources.how_to_use_onto_mcp(
            "Goal unclear: do this and that. Need clarify or choose safe discovery only.",
            "write_intent",
        )

        self.assertIn("clarifying_question", response)
        self.assertEqual(_next_tools(response), ["list_available_realms"])
        self.assertIn("delete_template", _avoid_tools(response))
        self.assertIn("update_diagram", _avoid_tools(response))

    def test_general_ontology_question_is_scope_guarded(self) -> None:
        response = api_resources.how_to_use_onto_mcp("\u0447\u0442\u043e \u0442\u0430\u043a\u043e\u0435 \u043e\u043d\u0442\u043e\u043b\u043e\u0433\u0438\u044f?")

        self.assertIn("clarifying_question", response)
        self.assertEqual(response["next_calls"], [])
        self.assertNotIn("about_onto", _next_tools(response))
        self.assertIn("routes actionable Onto MCP work", response["answer"])
        self.assertNotIn("knowledge representation", response["answer"].lower())
        self.assertNotIn("\u0441\u0443\u0449\u043d\u043e\u0441\u0442", response["answer"].lower())

    def test_destructive_single_uuid_plus_confirmation_does_not_satisfy_distinct_ids(self) -> None:
        response = build_how_to_response(
            "delete diagram 11111111-1111-1111-1111-111111111111 confirmed",
            "destructive_intent",
        )

        self.assertIn("delete_diagram", _avoid_tools(response))
        self.assertNotIn("delete_diagram", _next_tools(response))
        self.assertTrue(any("bare UUID is not enough" in note for note in response["safety_notes"]))

    def test_lifecycle_single_uuid_plus_confirmation_does_not_satisfy_distinct_ids(self) -> None:
        response = build_how_to_response(
            "accept artifact 11111111-1111-1111-1111-111111111111 confirmed",
            "lifecycle_intent",
        )

        self.assertIn("accept_memory_artifact", _avoid_tools(response))
        self.assertNotIn("accept_memory_artifact", _next_tools(response))
        self.assertTrue(any("bare UUID is not enough" in note for note in response["safety_notes"]))

    def test_requirement_presence_requires_named_requirement_value(self) -> None:
        known_ids = set(get_agent_contract()["id_dependency_graph"]["ids"].keys())

        self.assertFalse(
            _requirement_present(
                "realm_id",
                "delete diagram 11111111-1111-1111-1111-111111111111 confirmed",
                known_ids,
            )
        )
        self.assertFalse(
            _requirement_present(
                "diagram_id",
                "delete diagram 11111111-1111-1111-1111-111111111111 confirmed",
                known_ids,
            )
        )
        self.assertTrue(
            _requirement_present(
                "realm_id",
                "realm_id 00000000-0000-0000-0000-000000000001 confirmed",
                known_ids,
            )
        )
        self.assertTrue(
            _requirement_present(
                "diagram_id",
                "diagram_id 11111111-1111-1111-1111-111111111111 confirmed",
                known_ids,
            )
        )


if __name__ == "__main__":
    unittest.main()
