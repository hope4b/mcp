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


class GetEntityRelatedEntitiesTests(unittest.TestCase):
    def test_get_entity_formats_related_entity_details(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, query_params=None, timeout=30, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["query_params"] = query_params
            captured["timeout"] = timeout
            return {
                "result": {
                    "uuid": "entity-main",
                    "name": "Main Entity",
                    "related_entities": [
                        {
                            "relationName": "owned_by",
                            "direction": "OUT",
                            "incomingRole": "owner",
                            "outgoingRole": "asset",
                            "entity": {
                                "uuid": "entity-user",
                                "name": "User One",
                                "metaEntity": {
                                    "uuid": "meta-user",
                                    "name": "User",
                                },
                            },
                        },
                        {
                            "relationName": "located_in",
                            "direction": "IN",
                            "entity": {
                                "uuid": "entity-folder",
                                "name": "Folder One",
                            },
                        },
                    ],
                }
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.get_entity("realm-1", "entity-main", related_entities=True)

        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["url"], "https://onto.example/api/core/realm/realm-1/entity/entity-main")
        self.assertEqual(captured["query_params"]["relatedEntities"], True)
        self.assertIn("Related entities: 2", result)
        self.assertIn("1. User One (entity-user)", result)
        self.assertIn("relation=owned_by", result)
        self.assertIn("direction=OUT", result)
        self.assertIn("incomingRole=owner", result)
        self.assertIn("outgoingRole=asset", result)
        self.assertIn("template=User (meta-user)", result)
        self.assertIn("2. Folder One (entity-folder)", result)
        self.assertIn("relation=located_in", result)


if __name__ == "__main__":
    unittest.main()
