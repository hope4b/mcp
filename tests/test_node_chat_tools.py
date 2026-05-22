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


class NodeChatToolTests(unittest.TestCase):
    def test_get_node_chat_messages_calls_only_node_chat_endpoint_and_formats_metadata(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, timeout=30, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["timeout"] = timeout
            captured["kwargs"] = kwargs
            return [
                {
                    "id": "message-1",
                    "text": "hello node",
                    "timeStamp": "2026-05-23T10:00:00Z",
                    "my": True,
                    "user": {
                        "userId": "user-1",
                        "userName": "Alice",
                        "comment": "qa user",
                    },
                }
            ]

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.get_node_chat_messages("realm-1", "node-1")

        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["url"], "https://onto.example/api/core/realm/realm-1/chat/node-1")
        self.assertNotIn("json_payload", captured["kwargs"])
        self.assertIn("Found 1 object/node chat message", result)
        self.assertIn("hello node", result)
        self.assertIn("user.userId: user-1", result)
        self.assertIn('"timeStamp": "2026-05-23T10:00:00Z"', result)

    def test_get_node_chat_messages_returns_explicit_empty_result(self) -> None:
        with patch.object(api_resources, "_request_json", return_value=[]):
            result = api_resources.get_node_chat_messages("realm-1", "node-1")

        self.assertIn("No node chat messages found", result)

    def test_create_node_chat_message_posts_text_to_node_chat_endpoint(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, timeout=30, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            captured["timeout"] = timeout
            return {"status": "OK", "message": "saved"}

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.create_node_chat_message("realm-1", "node-1", "  hello node  ")

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://onto.example/api/core/realm/realm-1/chat/node-1")
        self.assertEqual(captured["json_payload"], {"text": "hello node"})
        self.assertIn("Status: OK", result)
        self.assertIn("Message: saved", result)

    def test_rejects_empty_inputs_before_backend_call(self) -> None:
        cases = [
            (api_resources.get_node_chat_messages, {"realm_id": "", "node_id": "node-1"}),
            (api_resources.get_node_chat_messages, {"realm_id": "realm-1", "node_id": ""}),
            (api_resources.create_node_chat_message, {"realm_id": "", "node_id": "node-1", "text": "hello"}),
            (api_resources.create_node_chat_message, {"realm_id": "realm-1", "node_id": "", "text": "hello"}),
            (api_resources.create_node_chat_message, {"realm_id": "realm-1", "node_id": "node-1", "text": "   "}),
        ]

        for fn, kwargs in cases:
            with self.subTest(fn=fn.__name__, kwargs=kwargs), patch.object(api_resources, "_request_json") as request_json:
                result = fn(**kwargs)

                request_json.assert_not_called()
                self.assertIn("required", result)


if __name__ == "__main__":
    unittest.main()
