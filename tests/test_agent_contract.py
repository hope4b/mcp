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
        self.assertNotIn("clarifying_question", response)

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
