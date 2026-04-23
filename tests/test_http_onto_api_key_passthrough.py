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


class _Request:
    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


class HttpOntoApiKeyPassthroughTests(unittest.TestCase):
    def test_prefers_incoming_http_passthrough_header(self) -> None:
        with patch.object(api_resources, "IS_HTTP_TRANSPORT", True), patch.object(
            api_resources, "ONTO_API_KEY", "server-env-key"
        ), patch.object(api_resources, "ONTO_API_KEY_HEADER", "X-API-Key"), patch.object(
            api_resources, "ONTO_API_KEY_PASSTHROUGH_HEADER", "X-Onto-Api-Key"
        ), patch.object(
            api_resources, "get_http_request", return_value=_Request({"X-Onto-Api-Key": "client-key"})
        ):
            headers = api_resources._onto_headers()

        self.assertEqual(headers["X-API-Key"], "client-key")

    def test_falls_back_to_server_env_key_when_passthrough_header_missing(self) -> None:
        with patch.object(api_resources, "IS_HTTP_TRANSPORT", True), patch.object(
            api_resources, "ONTO_API_KEY", "server-env-key"
        ), patch.object(api_resources, "ONTO_API_KEY_HEADER", "X-API-Key"), patch.object(
            api_resources, "ONTO_API_KEY_PASSTHROUGH_HEADER", "X-Onto-Api-Key"
        ), patch.object(api_resources, "get_http_request", return_value=_Request({})):
            headers = api_resources._onto_headers()

        self.assertEqual(headers["X-API-Key"], "server-env-key")

    def test_http_mode_requires_passthrough_or_server_env_key(self) -> None:
        with patch.object(api_resources, "IS_HTTP_TRANSPORT", True), patch.object(
            api_resources, "ONTO_API_KEY", ""
        ), patch.object(api_resources, "ONTO_API_KEY_PASSTHROUGH_HEADER", "X-Onto-Api-Key"), patch.object(
            api_resources, "get_http_request", return_value=_Request({})
        ):
            with self.assertRaises(RuntimeError) as exc:
                api_resources._onto_headers()

        self.assertIn("X-Onto-Api-Key", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
