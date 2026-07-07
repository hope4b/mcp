from __future__ import annotations

import asyncio
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
            self.http_app_calls: list[dict[str, object]] = []

        def tool(self, fn):
            return fn

        def resource(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

        def run(self):
            return None

        def http_app(self, **kwargs):
            self.http_app_calls.append(kwargs)

            async def app(scope, receive, send):
                await send({"type": "http.response.start", "status": 204, "headers": []})
                await send({"type": "http.response.body", "body": b""})

            return app

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

from onto_mcp import server


class ServerRuntimeTests(unittest.TestCase):
    def test_startup_message_contains_runtime_evidence_without_legacy_banner(self) -> None:
        with patch.object(server, "MCP_REF", "runtime-sha"), patch.object(
            server, "_package_version", side_effect=lambda name: {"onto-mcp-server": "0.1.0", "fastmcp": "3.4.3"}[name]
        ):
            message = server._startup_message()

        self.assertIn("app=Onto MCP Server", message)
        self.assertIn("transport=", message)
        self.assertIn("port=", message)
        self.assertIn("mcp_ref=runtime-sha", message)
        self.assertIn("fastmcp_version=3.4.3", message)
        self.assertNotIn("vOAUTH", message)

    def test_health_check_asgi_app_returns_ok_without_calling_mcp_app(self) -> None:
        called = False

        async def inner_app(scope, receive, send):
            nonlocal called
            called = True
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        sent: list[dict[str, object]] = []

        async def send(message):
            sent.append(message)

        app = server.HealthCheckASGIApp(inner_app)
        asyncio.run(app({"type": "http", "path": "/healthz"}, receive, send))

        self.assertFalse(called)
        self.assertEqual(sent[0]["status"], 200)
        self.assertIn(b'"status": "ok"', sent[1]["body"])

    def test_build_http_app_passes_configured_allowed_hosts_to_fastmcp(self) -> None:
        class _MCP:
            def __init__(self) -> None:
                self.http_app_calls: list[dict[str, object]] = []

            def http_app(self, **kwargs):
                self.http_app_calls.append(kwargs)

                async def app(scope, receive, send):
                    await send({"type": "http.response.start", "status": 204, "headers": []})
                    await send({"type": "http.response.body", "body": b""})

                return app

        mcp = _MCP()
        with patch.object(server, "mcp", mcp), patch.object(
            server, "MCP_ALLOWED_HOSTS", "preprod.ontonet.ru, localhost"
        ), patch.object(server, "MCP_ALLOWED_ORIGINS", "https://preprod.ontonet.ru"):
            server._build_http_app()

        self.assertEqual(
            mcp.http_app_calls[-1],
            {
                "allowed_hosts": ["preprod.ontonet.ru", "localhost"],
                "allowed_origins": ["https://preprod.ontonet.ru"],
            },
        )


if __name__ == "__main__":
    unittest.main()
