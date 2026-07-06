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


class GetDiagramTests(unittest.TestCase):
    def test_get_diagram_preserves_counts_and_renders_representation_details(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, **kwargs):
            captured["method"] = method
            captured["url"] = url
            return {
                "diagram": {
                    "id": "diagram-1",
                    "name": "Defect intake",
                    "summary": "Bug gate",
                    "creationDate": "2026-07-06",
                },
                "representations": [
                    {
                        "id": "representation-1",
                        "nodeId": "node-1",
                        "name": "MCP get_diagram does not reveal diagram objects",
                        "type": "ENTITY",
                        "coordinates": {"x": 12, "y": -4},
                        "size": {"x": 220, "y": 80},
                        "ontoNode": {
                            "id": "node-1",
                            "name": "MCP get_diagram does not reveal diagram objects",
                            "meta": {"id": "meta-bug", "name": "Bug"},
                        },
                    },
                    {
                        "representationId": "representation-2",
                        "nodeId": "node-2",
                        "nodeName": "Second bug",
                        "representationType": "ENTITY",
                        "representationDetails": {"src": "manual"},
                    },
                ],
                "links": [{"id": "link-1"}],
                "pointOfView": {"userId": "user-1"},
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.get_diagram("realm-1", "diagram-1")

        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["url"], "https://onto.example/api/core/realm/realm-1/diagram/v2/diagram-1")
        self.assertIn("Diagram loaded successfully.", result)
        self.assertIn("Representations: 2", result)
        self.assertIn("Links: 1", result)
        self.assertIn("Point of view: present", result)
        self.assertIn("Representation details:", result)
        self.assertIn("Representation ID: representation-1", result)
        self.assertIn("Node ID: node-1", result)
        self.assertIn("Classification: Bug", result)
        self.assertIn('Coordinates: {"x": 12, "y": -4}', result)
        self.assertIn("Representation ID: representation-2", result)
        self.assertIn("Object name: Second bug", result)
        self.assertIn("Representation type: ENTITY", result)
        self.assertIn('Placement details: {"src": "manual"}', result)


if __name__ == "__main__":
    unittest.main()
