from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

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


class SearchEntitiesByRelationsTests(unittest.TestCase):
    def test_root_only_search_maps_body_and_formats_results(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, timeout=30, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            captured["timeout"] = timeout
            return [
                {
                    "id": "entity-1",
                    "name": "Diagram 1",
                    "metaEntity": {"id": "diagram-meta", "name": "Diagram"},
                }
            ]

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.search_entities_by_relations(
                realm_id="realm-1",
                searched_meta_ids=["diagram-meta"],
            )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://onto.example/api/core/realm/realm-1/entity/search")
        self.assertEqual(captured["json_payload"], {"searchedMetaIds": ["diagram-meta"]})
        self.assertIn("Found 1 entities in realm realm-1", result)
        self.assertIn("Diagram 1", result)

    def test_predicate_search_maps_public_snake_case_to_backend_camel_case(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            captured["json_payload"] = json_payload
            return []

        with patch.object(api_resources, "_request_json", side_effect=fake_request):
            result = api_resources.search_entities_by_relations(
                realm_id="realm-1",
                searched_meta_ids=["diagram-meta"],
                predicates=[
                    {
                        "relation_type_names": ["owned_by", "maintained_by"],
                        "related_meta_ids": ["user-meta"],
                        "related_entity_ids": ["user-1", "user-2"],
                    },
                    {"related_entity_ids": ["folder-1"]},
                ],
            )

        self.assertEqual(
            captured["json_payload"],
            {
                "searchedMetaIds": ["diagram-meta"],
                "predicates": [
                    {
                        "relationTypeNames": ["owned_by", "maintained_by"],
                        "relatedMetaIds": ["user-meta"],
                        "relatedEntityIds": ["user-1", "user-2"],
                    },
                    {"relatedEntityIds": ["folder-1"]},
                ],
            },
        )
        self.assertIn("No entities found", result)

    def test_rejects_empty_searched_meta_ids_before_backend_call(self) -> None:
        with patch.object(api_resources, "_request_json") as request_json:
            result = api_resources.search_entities_by_relations(realm_id="realm-1", searched_meta_ids=[])

        request_json.assert_not_called()
        self.assertIn("searched_meta_ids", result)

    def test_rejects_backend_list_limits_before_backend_call(self) -> None:
        with patch.object(api_resources, "_request_json") as request_json:
            result = api_resources.search_entities_by_relations(
                realm_id="realm-1",
                searched_meta_ids=[f"meta-{index}" for index in range(21)],
            )

        request_json.assert_not_called()
        self.assertIn("at most 20", result)

        with patch.object(api_resources, "_request_json") as request_json:
            result = api_resources.search_entities_by_relations(
                realm_id="realm-1",
                searched_meta_ids=["diagram-meta"],
                predicates=[{"related_entity_ids": [f"entity-{index}" for index in range(21)]}],
            )

        request_json.assert_not_called()
        self.assertIn("at most 20", result)

        with patch.object(api_resources, "_request_json") as request_json:
            result = api_resources.search_entities_by_relations(
                realm_id="realm-1",
                searched_meta_ids=["diagram-meta"],
                predicates=[{"related_entity_ids": [f"entity-{index}"]} for index in range(11)],
            )

        request_json.assert_not_called()
        self.assertIn("at most 10", result)

    def test_rejects_direction_and_boolean_operator_before_backend_call(self) -> None:
        invalid_predicates = [
            {"direction": "OUT"},
            {"operator": "or"},
            {"or": [{"related_entity_ids": ["entity-1"]}]},
        ]

        for predicate in invalid_predicates:
            with self.subTest(predicate=predicate), patch.object(api_resources, "_request_json") as request_json:
                result = api_resources.search_entities_by_relations(
                    realm_id="realm-1",
                    searched_meta_ids=["diagram-meta"],
                    predicates=[predicate],
                )

                request_json.assert_not_called()
                self.assertIn("unsupported", result)

    def test_rejects_nested_predicates_before_backend_call(self) -> None:
        with patch.object(api_resources, "_request_json") as request_json:
            result = api_resources.search_entities_by_relations(
                realm_id="realm-1",
                searched_meta_ids=["diagram-meta"],
                predicates=[{"predicates": [{"related_entity_ids": ["entity-1"]}]}],
            )

        request_json.assert_not_called()
        self.assertIn("unsupported", result)

    def test_rejects_name_based_classification_inputs_before_backend_call(self) -> None:
        with patch.object(api_resources, "_request_json") as request_json:
            result = api_resources.search_entities_by_relations(
                realm_id="realm-1",
                searched_meta_ids=["diagram-meta"],
                predicates=[{"related_meta_names": ["User"]}],
            )

        request_json.assert_not_called()
        self.assertIn("unsupported field", result)


if __name__ == "__main__":
    unittest.main()
