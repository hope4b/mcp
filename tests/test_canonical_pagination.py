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


class CanonicalPaginationTests(unittest.TestCase):
    def test_search_entities_maps_first_offset_to_backend_pagination(self) -> None:
        captured_payloads: list[dict] = []

        def fake_request(_method: str, _url: str, *, json_payload=None, **_kwargs):
            captured_payloads.append(json_payload)
            return []

        with patch.object(api_resources, "_request_json", side_effect=fake_request):
            api_resources.search_entities("realm-1", first=20, offset=50)
            api_resources.search_entities_with_related_meta("realm-1", first=40, offset=25)

        self.assertEqual(captured_payloads[0]["pagination"], {"first": 20, "offset": 50})
        self.assertEqual(captured_payloads[1]["pagination"], {"first": 40, "offset": 25})

    def test_search_objects_uses_first_and_offset_for_first_page(self) -> None:
        captured_payloads: list[dict] = []

        def fake_request(_method: str, _url: str, *, json_payload=None, **_kwargs):
            captured_payloads.append(json_payload)
            return []

        with patch.object(api_resources, "_request_json", side_effect=fake_request):
            api_resources.search_objects("realm-1", first=30, offset=10)

        self.assertEqual(captured_payloads[0]["pagination"], {"first": 30, "offset": 10})

    def test_page_based_tools_map_first_offset_to_page_size(self) -> None:
        captured_urls: list[str] = []

        def fake_request(_method: str, url: str, **_kwargs):
            captured_urls.append(url)
            return {"totalResults": 0, "totalPages": 0, "page": 3, "size": 20, "results": []}

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            api_resources.search_diagrams("realm-1", first=40, offset=20)
            api_resources.search_context_tags("realm-1", first=40, offset=20)

        self.assertEqual(captured_urls[0], "https://onto.example/api/core/realm/realm-1/diagram/v2/page/3/size/20")
        self.assertEqual(
            captured_urls[1],
            "https://onto.example/api/core/realm/realm-1/entity/tags/name/*/page/3/size/20",
        )

    def test_rejects_invalid_canonical_pagination_before_backend_call(self) -> None:
        cases = [
            (api_resources.search_objects, {"realm_id": "realm-1", "first": -1, "offset": 100}),
            (api_resources.search_entities, {"realm_id": "realm-1", "first": 0, "offset": 0}),
            (api_resources.search_entities_with_related_meta, {"realm_id": "realm-1", "first": -1, "offset": 100}),
            (api_resources.search_diagrams, {"realm_id": "realm-1", "first": 10, "offset": 20}),
            (api_resources.search_context_tags, {"realm_id": "realm-1", "first": 0, "offset": 0}),
        ]

        for fn, kwargs in cases:
            with self.subTest(fn=fn.__name__, kwargs=kwargs), patch.object(api_resources, "_request_json") as request_json:
                result = fn(**kwargs)

                request_json.assert_not_called()
                self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
