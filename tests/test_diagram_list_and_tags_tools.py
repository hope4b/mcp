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


class DiagramListAndTagsToolTests(unittest.TestCase):
    def test_search_diagrams_maps_filter_body_and_formats_page_metadata(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            return {
                "totalResults": 1,
                "totalPages": 1,
                "page": 1,
                "size": 20,
                "results": [
                    {
                        "id": "diagram-1",
                        "name": "Diagram A",
                        "summary": "summary",
                        "creationDate": "2026-05-26",
                        "stared": False,
                        "tags": [{"id": "tag-1", "name": "Tag A"}],
                    }
                ],
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.search_diagrams(
                realm_id="realm-1",
                name_part="Diagram",
                tag_ids=["tag-1"],
                page=1,
                size=20,
            )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://onto.example/api/core/realm/realm-1/diagram/v2/page/1/size/20")
        self.assertEqual(captured["json_payload"], {"namePart": "Diagram", "tags": ["tag-1"]})
        self.assertIn("totalResults: 1", result)
        self.assertIn("diagram-1", result)
        self.assertIn("tag-1", result)

    def test_search_context_tags_maps_empty_name_part_to_star_and_encodes_names(self) -> None:
        captured_urls: list[str] = []

        def fake_request(method: str, url: str, **kwargs):
            captured_urls.append(url)
            return {"totalResults": 0, "totalPages": 0, "page": 1, "size": 20, "results": []}

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            empty_result = api_resources.search_context_tags("realm-1")
            api_resources.search_context_tags("realm-1", name_part="tag/name")

        self.assertEqual(
            captured_urls[0],
            "https://onto.example/api/core/realm/realm-1/entity/tags/name/*/page/1/size/20",
        )
        self.assertEqual(
            captured_urls[1],
            "https://onto.example/api/core/realm/realm-1/entity/tags/name/tag%2Fname/page/1/size/20",
        )
        self.assertIn("No context tags found", empty_result)

    def test_create_context_tag_from_object_loads_existing_entity_and_sets_is_tag(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, *, json_payload=None, query_params=None, **kwargs):
            calls.append({"method": method, "url": url, "json_payload": json_payload, "query_params": query_params})
            if method == "GET":
                return {
                    "result": {
                        "id": "entity-1",
                        "name": "Tag Source",
                        "comment": "comment",
                        "metaEntity": {"uuid": "meta-1", "name": "Meta"},
                    }
                }
            return {"status": "OK", "message": "saved"}

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.create_context_tag_from_object("realm-1", "entity-1")

        self.assertEqual(calls[0]["method"], "GET")
        self.assertEqual(calls[0]["url"], "https://onto.example/api/core/realm/realm-1/entity/entity-1")
        self.assertEqual(calls[1]["method"], "POST")
        self.assertEqual(calls[1]["url"], "https://onto.example/api/core/realm/realm-1/entity")
        self.assertEqual(
            calls[1]["json_payload"],
            {
                "id": "entity-1",
                "name": "Tag Source",
                "comment": "comment",
                "metaEntityId": "meta-1",
                "isTag": True,
            },
        )
        self.assertIn("Status: OK", result)

    def test_add_diagram_tag_preserves_existing_tags_and_metadata(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            calls.append({"method": method, "url": url, "json_payload": json_payload})
            if method == "GET":
                return {
                    "diagram": {
                        "id": "diagram-1",
                        "name": "Diagram A",
                        "summary": "summary",
                        "tags": [{"id": "tag-1", "name": "Tag 1"}],
                    }
                }
            return {"status": "OK", "message": "Diagram updated."}

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.add_diagram_tag("realm-1", "diagram-1", "tag-2")

        self.assertEqual([call["method"] for call in calls], ["GET", "PUT"])
        self.assertEqual(calls[1]["url"], "https://onto.example/api/core/realm/realm-1/diagram/v2/diagram-1")
        self.assertEqual(calls[1]["json_payload"], {"name": "Diagram A", "comment": "summary", "tags": ["tag-1", "tag-2"]})
        self.assertIn("Final tag count: 2", result)

    def test_add_diagram_tag_is_noop_when_already_assigned(self) -> None:
        with patch.object(
            api_resources,
            "_request_json",
            return_value={"diagram": {"id": "diagram-1", "name": "Diagram A", "tags": [{"id": "tag-1"}]}},
        ) as request_json:
            result = api_resources.add_diagram_tag("realm-1", "diagram-1", "tag-1")

        self.assertEqual(request_json.call_count, 1)
        self.assertIn("already has context tag tag-1", result)

    def test_remove_diagram_tag_preserves_remaining_tags_and_metadata(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            calls.append({"method": method, "url": url, "json_payload": json_payload})
            if method == "GET":
                return {
                    "diagram": {
                        "id": "diagram-1",
                        "name": "Diagram A",
                        "summary": "summary",
                        "tags": [{"id": "tag-1"}, {"id": "tag-2"}],
                    }
                }
            return {"status": "OK", "message": "Diagram updated."}

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.remove_diagram_tag("realm-1", "diagram-1", "tag-1")

        self.assertEqual([call["method"] for call in calls], ["GET", "PUT"])
        self.assertEqual(calls[1]["json_payload"], {"name": "Diagram A", "comment": "summary", "tags": ["tag-2"]})
        self.assertIn("Final tag count: 1", result)

    def test_remove_diagram_tag_is_noop_when_absent(self) -> None:
        with patch.object(
            api_resources,
            "_request_json",
            return_value={"diagram": {"id": "diagram-1", "name": "Diagram A", "tags": [{"id": "tag-1"}]}},
        ) as request_json:
            result = api_resources.remove_diagram_tag("realm-1", "diagram-1", "tag-2")

        self.assertEqual(request_json.call_count, 1)
        self.assertIn("does not have context tag tag-2", result)

    def test_rejects_invalid_inputs_before_backend_call(self) -> None:
        cases = [
            (api_resources.search_diagrams, {"realm_id": "", "page": 1, "size": 20}),
            (api_resources.search_diagrams, {"realm_id": "realm-1", "page": 0, "size": 20}),
            (api_resources.search_diagrams, {"realm_id": "realm-1", "tag_ids": [""]}),
            (api_resources.search_context_tags, {"realm_id": "realm-1", "page": 1, "size": 0}),
            (api_resources.create_context_tag_from_object, {"realm_id": "realm-1", "entity_id": ""}),
            (api_resources.add_diagram_tag, {"realm_id": "realm-1", "diagram_id": "", "tag_id": "tag-1"}),
            (api_resources.remove_diagram_tag, {"realm_id": "realm-1", "diagram_id": "diagram-1", "tag_id": ""}),
        ]

        for fn, kwargs in cases:
            with self.subTest(fn=fn.__name__, kwargs=kwargs), patch.object(api_resources, "_request_json") as request_json:
                result = fn(**kwargs)

                request_json.assert_not_called()
                self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
