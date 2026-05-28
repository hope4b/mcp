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


class AddExistingNodesToDiagramTests(unittest.TestCase):
    def test_maps_nodes_to_existing_representation_batch_payload(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            return {
                "successful": [
                    {
                        "representationId": "representation-1",
                        "nodeId": "node-1",
                    }
                ],
                "failed": [],
                "message": "ok",
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.add_existing_nodes_to_diagram(
                "realm-1",
                "diagram-1",
                [
                    {"existing_node_id": "node-1", "x": -480, "y": 80.5},
                    {"existing_node_id": "node-2", "x": 0, "y": 0, "type": "TEMPLATE"},
                ],
            )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(
            captured["url"],
            "https://onto.example/api/core/realm/realm-1/diagram/v2/diagram-1/representation/create/existing_nodes/batch",
        )
        self.assertEqual(
            captured["json_payload"],
            {
                "representations": [
                    {
                        "existingNodeId": "node-1",
                        "representation": {
                            "type": "ENTITY",
                            "coordinates": {"x": -480, "y": 80.5},
                        },
                    },
                    {
                        "existingNodeId": "node-2",
                        "representation": {
                            "type": "TEMPLATE",
                            "coordinates": {"x": 0, "y": 0},
                        },
                    },
                ]
            },
        )
        self.assertIn("Successful: 1", result)
        self.assertIn("Representation ID: representation-1", result)
        self.assertIn("Response data:", result)

    def test_preserves_partial_success_details(self) -> None:
        with patch.object(
            api_resources,
            "_request_json",
            return_value={
                "successful": [{"representationId": "representation-1", "nodeId": "node-1"}],
                "failed": [{"existingNodeId": "node-2", "error": "duplicate"}],
                "message": "partial",
            },
        ):
            result = api_resources.add_existing_nodes_to_diagram(
                "realm-1",
                "diagram-1",
                [{"existing_node_id": "node-1", "x": 1, "y": 2}],
            )

        self.assertIn("Successful: 1", result)
        self.assertIn("Failed: 1", result)
        self.assertIn("Node ID: node-1", result)
        self.assertIn("Existing node ID: node-2", result)
        self.assertIn("Error: duplicate", result)

    def test_rejects_invalid_inputs_before_backend_call(self) -> None:
        invalid_nodes = [{"existing_node_id": f"node-{index}", "x": index, "y": index} for index in range(21)]
        cases = [
            {"realm_id": "", "diagram_id": "diagram-1", "nodes": [{"existing_node_id": "node-1", "x": 0, "y": 0}]},
            {"realm_id": "realm-1", "diagram_id": "", "nodes": [{"existing_node_id": "node-1", "x": 0, "y": 0}]},
            {"realm_id": "realm-1", "diagram_id": "diagram-1", "nodes": []},
            {"realm_id": "realm-1", "diagram_id": "diagram-1", "nodes": invalid_nodes},
            {"realm_id": "realm-1", "diagram_id": "diagram-1", "nodes": [{"existing_node_id": "", "x": 0, "y": 0}]},
            {"realm_id": "realm-1", "diagram_id": "diagram-1", "nodes": [{"existing_node_id": "node-1", "y": 0}]},
            {"realm_id": "realm-1", "diagram_id": "diagram-1", "nodes": [{"existing_node_id": "node-1", "x": "0", "y": 0}]},
            {
                "realm_id": "realm-1",
                "diagram_id": "diagram-1",
                "nodes": [{"existing_node_id": "node-1", "x": 0, "y": 0, "type": "UNKNOWN"}],
            },
        ]

        for kwargs in cases:
            with self.subTest(kwargs=kwargs), patch.object(api_resources, "_request_json") as request_json:
                result = api_resources.add_existing_nodes_to_diagram(**kwargs)

                request_json.assert_not_called()
                self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
