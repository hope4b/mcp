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


class GetTemplateFieldsTests(unittest.TestCase):
    def test_get_template_renders_template_field_details(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, query_params=None, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["query_params"] = query_params
            return {
                "result": {
                    "id": "template-1",
                    "name": "Cat",
                    "comment": "Template comment",
                    "describerFields": [{"id": "field-1"}],
                    "fields": [
                        {
                            "id": "field-1",
                            "name": "Age",
                            "fieldTypeName": "T_STRING",
                            "comment": "Cat age",
                            "abilities": ["SEARCHABLE"],
                            "usableAsReference": True,
                        },
                        {
                            "uuid": "field-2",
                            "name": "Color",
                            "type": {"name": "T_STRING"},
                            "abilities": [],
                        },
                    ],
                }
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.get_template("realm-1", "template-1")

        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["url"], "https://onto.example/api/core/realm/realm-1/meta/template-1")
        self.assertEqual(captured["query_params"], {"children": False, "parents": False})
        self.assertIn("Fields: 2", result)
        self.assertIn("1. Age", result)
        self.assertIn("ID: field-1", result)
        self.assertIn("Type: T_STRING", result)
        self.assertIn("Comment: Cat age", result)
        self.assertIn("Abilities: SEARCHABLE", result)
        self.assertIn("Usable as reference: True", result)
        self.assertIn("2. Color", result)
        self.assertIn("ID: field-2", result)
        self.assertIn("Abilities: none", result)


if __name__ == "__main__":
    unittest.main()
