from __future__ import annotations

import asyncio
import json
import sys
import time
import types
import unittest
import uuid
from unittest.mock import patch

try:
    import requests  # noqa: F401
except ImportError:
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

try:
    import fastmcp  # noqa: F401
except ImportError:
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

try:
    from fastmcp import Client
except ImportError:
    Client = None

from onto_mcp import api_resources, server


REALM_ID = "000ba00a-00a0-0a00-a000-000a0a0a0aa3"


def _error_envelope(result) -> dict:
    return json.loads(result.content[0].text)


def _assert_stable_error(
    test: unittest.TestCase,
    result,
    *,
    code: str,
    message: str,
    retryable: bool,
) -> None:
    test.assertTrue(result.is_error)
    test.assertEqual(len(result.content), 1)
    envelope = _error_envelope(result)
    test.assertEqual(set(envelope), {"schema_version", "error"})
    test.assertEqual(envelope["schema_version"], "1")
    test.assertEqual(
        set(envelope["error"]),
        {"code", "message", "correlation_id", "retryable"},
    )
    test.assertEqual(envelope["error"]["code"], code)
    test.assertEqual(envelope["error"]["message"], message)
    test.assertEqual(envelope["error"]["retryable"], retryable)
    uuid.UUID(envelope["error"]["correlation_id"])


class ServerRuntimeTests(unittest.TestCase):
    @unittest.skipIf(Client is None, "real FastMCP client is unavailable")
    def test_about_realm_protocol_normalizes_every_invalid_input_shape(self) -> None:
        async def exercise():
            async with Client(server.mcp) as client:
                tools = await client.list_tools()
                about_realm_tools = [
                    tool for tool in tools if tool.name == "about_realm"
                ]
                self.assertEqual(len(about_realm_tools), 1)
                self.assertEqual(
                    about_realm_tools[0].input_schema,
                    {
                        "additionalProperties": False,
                        "properties": {"realm_id": {"type": "string"}},
                        "required": ["realm_id"],
                        "type": "object",
                    },
                )
                invalid_results = []
                for arguments in (
                    {},
                    {"realm_id": None},
                    {"realm_id": 123},
                    {"realm_id": "BAD"},
                    {"realm_id": REALM_ID, "extra": "forbidden"},
                ):
                    invalid_results.append(
                        await client.call_tool(
                            "about_realm",
                            arguments,
                            raise_on_error=False,
                        )
                    )
                valid_result = await client.call_tool(
                    "about_realm",
                    {"realm_id": REALM_ID},
                    raise_on_error=False,
                )
                return invalid_results, valid_result

        success = {
            "schema_version": "1",
            "realm_id": REALM_ID,
            "artifact_path": "realm/declaration",
            "artifact_id": "11111111-1111-4111-8111-111111111111",
            "artifact_kind": "decision",
            "declaration_contract_id": "realm_declaration",
            "declaration_contract_version": 1,
            "status": "accepted",
            "accepted_at": "2026-09-07T12:34:56Z",
            "body_sha256": "0" * 64,
            "body": "{}",
        }
        with patch.object(
            api_resources,
            "_onto_headers",
            side_effect=lambda: {"X-API-Key": "test-only"},
        ) as headers, patch.object(
            api_resources,
            "resolve_realm_declaration",
            return_value=success,
        ) as resolver:
            invalid_results, valid_result = asyncio.run(exercise())

        for result in invalid_results:
            _assert_stable_error(
                self,
                result,
                code="invalid_request",
                message="Invalid request.",
                retryable=False,
            )
        self.assertFalse(valid_result.is_error)
        self.assertEqual(headers.call_count, 1)
        resolver.assert_called_once()

    @unittest.skipIf(Client is None, "real FastMCP client is unavailable")
    def test_about_realm_outer_timeout_is_dependency_tool_error(self) -> None:
        def delayed_resolver(*args, **kwargs):
            time.sleep(0.05)
            raise AssertionError("timed-out result must not be emitted")

        async def exercise():
            async with Client(server.mcp) as client:
                return await client.call_tool(
                    "about_realm",
                    {"realm_id": REALM_ID},
                    raise_on_error=False,
                )

        with patch.object(
            api_resources, "_HTTP_MCP_TOOL_TIMEOUT_SECONDS", 0.001
        ), patch.object(
            api_resources,
            "_onto_headers",
            return_value={"X-API-Key": "test-only"},
        ), patch.object(
            api_resources,
            "resolve_realm_declaration",
            side_effect=delayed_resolver,
        ):
            result = asyncio.run(exercise())

        _assert_stable_error(
            self,
            result,
            code="dependency_unavailable",
            message="Realm declaration dependency is unavailable.",
            retryable=True,
        )
        self.assertNotIn("timeout_ms", result.content[0].text)
        self.assertNotIn("tool_name", result.content[0].text)

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
