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
from onto_mcp.realm_object_clone import CloneObjectToRealmNotFound, CloneObjectToRealmResult


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
                    about_realm_tools[0].inputSchema,
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

    def test_clone_tools_have_exact_protocol_input_schemas(self) -> None:
        async def exercise():
            async with Client(server.mcp) as client:
                return {tool.name: tool.inputSchema for tool in await client.list_tools()}

        schemas = asyncio.run(exercise())
        self.assertEqual(
            schemas["clone_object_to_realm"],
            {
                "additionalProperties": False,
                "properties": {
                    "source_realm_id": {"type": "string"},
                    "source_object_id": {"type": "string"},
                    "target_realm_id": {"type": "string"},
                    "target_template_id": {"type": "string"},
                },
                "required": [
                    "source_realm_id",
                    "source_object_id",
                    "target_realm_id",
                    "target_template_id",
                ],
                "type": "object",
            },
        )
        self.assertEqual(
            schemas["get_clone_object_to_realm_result"],
            {
                "additionalProperties": False,
                "properties": {
                    "source_realm_id": {"type": "string"},
                    "source_object_id": {"type": "string"},
                    "target_realm_id": {"type": "string"},
                },
                "required": ["source_realm_id", "source_object_id", "target_realm_id"],
                "type": "object",
            },
        )
        self.assertNotIn("idempotency", json.dumps(schemas["clone_object_to_realm"]).lower())

    def test_get_entity_protocol_schema_adds_only_optional_boolean_provenance(self) -> None:
        async def exercise():
            async with Client(server.mcp) as client:
                tools = await client.list_tools()
                return tools, next(tool.inputSchema for tool in tools if tool.name == "get_entity")

        tools, schema = asyncio.run(exercise())

        self.assertEqual(len(tools), 69)
        self.assertEqual(
            list(schema["properties"]),
            [
                "realm_id",
                "entity_id",
                "related_diagrams",
                "related_entities",
                "with_empty_stickers",
                "name",
                "provenance",
            ],
        )
        self.assertEqual(schema["required"], ["realm_id", "entity_id"])
        self.assertEqual(schema["properties"]["realm_id"], {"type": "string"})
        self.assertEqual(schema["properties"]["entity_id"], {"type": "string"})
        self.assertEqual(
            schema["properties"]["provenance"],
            {"default": False, "type": "boolean"},
        )
        self.assertFalse(schema["additionalProperties"])

    def test_get_entity_protocol_projects_deterministic_provenance_and_unknowns(self) -> None:
        source_id = "11111111-1111-4111-8111-111111111111"
        source_realm_id = "22222222-2222-4222-8222-222222222222"
        copy_id = "33333333-3333-4333-8333-333333333333"
        copy_realm_id = "44444444-4444-4444-8444-444444444444"
        response = {
            "result": {
                "uuid": "entity-main",
                "name": "Главная",
                "provenance": {
                    "source": {
                        "objectId": source_id,
                        "objectName": 'Источник "A"',
                        "realmId": source_realm_id,
                        "realmName": "Пространство A",
                        "backendOnly": "omitted",
                    },
                    "directCopies": [
                        {
                            "objectId": copy_id,
                            "objectName": "Копия\\B\nline",
                            "realmId": copy_realm_id,
                            "realmName": "Пространство B",
                            "secret": "omitted",
                        }
                    ],
                    "pagination": "omitted",
                },
            }
        }

        async def exercise():
            async with Client(server.mcp) as client:
                return await client.call_tool(
                    "get_entity",
                    {"realm_id": REALM_ID, "entity_id": "entity-main", "provenance": True},
                    raise_on_error=False,
                )

        with patch.object(api_resources, "_request_json", return_value=response) as request:
            result = asyncio.run(exercise())

        expected = {
            "source": {
                "objectId": source_id,
                "objectName": 'Источник "A"',
                "realmId": source_realm_id,
                "realmName": "Пространство A",
            },
            "directCopies": [
                {
                    "objectId": copy_id,
                    "objectName": "Копия\\B\nline",
                    "realmId": copy_realm_id,
                    "realmName": "Пространство B",
                }
            ],
        }
        expected_text = (
            "Entity loaded successfully.\n"
            "ID: entity-main\n"
            "Name: Главная\n\nProvenance:\n"
            + json.dumps(expected, ensure_ascii=False, indent=2)
        )
        self.assertFalse(result.is_error)
        self.assertEqual(result.content[0].text, expected_text)
        self.assertNotIn("backendOnly", result.content[0].text)
        self.assertNotIn("secret", result.content[0].text)
        self.assertNotIn("pagination", result.content[0].text)
        request.assert_called_once()
        self.assertEqual(request.call_args.kwargs["query_params"]["provenance"], True)

    def test_get_entity_protocol_invalid_provenance_fails_with_exact_safe_error(self) -> None:
        invalid_response = {
            "result": {
                "uuid": "entity-main",
                "name": "Main",
                "provenance": {
                    "source": None,
                    "directCopies": [
                        {
                            "objectId": "invalid-secret-bearing-id",
                            "objectName": "must-not-appear",
                            "realmId": "22222222-2222-4222-8222-222222222222",
                            "realmName": "must-not-appear",
                        }
                    ],
                },
            }
        }

        async def exercise():
            async with Client(server.mcp) as client:
                return await client.call_tool(
                    "get_entity",
                    {"realm_id": REALM_ID, "entity_id": "entity-main", "provenance": True},
                    raise_on_error=False,
                )

        with patch.object(api_resources, "_request_json", return_value=invalid_response):
            result = asyncio.run(exercise())

        self.assertTrue(result.is_error)
        self.assertEqual(result.content[0].text, "Onto API returned an invalid provenance response.")
        self.assertNotIn("invalid-secret-bearing-id", result.content[0].text)
        self.assertNotIn("must-not-appear", result.content[0].text)

    def test_clone_protocol_returns_structured_five_field_success(self) -> None:
        expected = {
            "target_realm_id": REALM_ID,
            "target_object_id": "11111111-1111-4111-8111-111111111111",
            "primary_realm_id": "22222222-2222-4222-8222-222222222222",
            "primary_object_id": "33333333-3333-4333-8333-333333333333",
            "created": True,
        }

        async def exercise():
            async with Client(server.mcp) as client:
                return await client.call_tool(
                    "clone_object_to_realm",
                    {
                        "source_realm_id": expected["primary_realm_id"],
                        "source_object_id": expected["primary_object_id"],
                        "target_realm_id": expected["target_realm_id"],
                        "target_template_id": "44444444-4444-4444-8444-444444444444",
                    },
                    raise_on_error=False,
                )

        with patch.object(api_resources, "_onto_headers", return_value={"X-API-Key": "secret"}), patch.object(
            api_resources,
            "clone_object_to_realm_request",
            return_value=CloneObjectToRealmResult(**expected),
        ) as adapter:
            result = asyncio.run(exercise())

        self.assertFalse(result.is_error)
        self.assertEqual(json.loads(result.content[0].text), expected)
        adapter.assert_called_once()

    def test_clone_protocol_delivers_closed_tool_error(self) -> None:
        async def exercise():
            async with Client(server.mcp) as client:
                return await client.call_tool(
                    "clone_object_to_realm",
                    {
                        "source_realm_id": "11111111-1111-4111-8111-111111111111",
                        "source_object_id": "22222222-2222-4222-8222-222222222222",
                        "target_realm_id": "33333333-3333-4333-8333-333333333333",
                        "target_template_id": "44444444-4444-4444-8444-444444444444",
                    },
                    raise_on_error=False,
                )

        with patch.object(api_resources, "_onto_headers", return_value={"X-API-Key": "secret"}), patch.object(
            api_resources,
            "clone_object_to_realm_request",
            return_value=api_resources.clone_tool_error("clone_failed", "safe.trace-1"),
        ):
            result = asyncio.run(exercise())

        self.assertTrue(result.is_error)
        envelope = json.loads(result.content[0].text)
        self.assertEqual(envelope["schema_version"], 1)
        self.assertEqual(set(envelope), {"schema_version", "error"})
        self.assertEqual(
            envelope["error"],
            {
                "code": "clone_failed",
                "message": "Clone operation failed.",
                "correlation_id": "safe.trace-1",
                "retryable": False,
                "recovery": {"action": "none"},
            },
        )
        self.assertNotIn("secret", result.content[0].text)

    def test_clone_outer_timeout_is_non_retryable_unknown_and_discards_late_success(self) -> None:
        def delayed_clone(*args, **kwargs):
            time.sleep(0.05)
            return CloneObjectToRealmResult(
                target_realm_id=REALM_ID,
                target_object_id="11111111-1111-4111-8111-111111111111",
                primary_realm_id="22222222-2222-4222-8222-222222222222",
                primary_object_id="33333333-3333-4333-8333-333333333333",
                created=True,
            )

        async def exercise():
            async with Client(server.mcp) as client:
                return await client.call_tool(
                    "clone_object_to_realm",
                    {
                        "source_realm_id": "22222222-2222-4222-8222-222222222222",
                        "source_object_id": "33333333-3333-4333-8333-333333333333",
                        "target_realm_id": REALM_ID,
                        "target_template_id": "44444444-4444-4444-8444-444444444444",
                    },
                    raise_on_error=False,
                )

        with patch.object(api_resources, "_HTTP_MCP_TOOL_TIMEOUT_SECONDS", 0.001), patch.object(
            api_resources, "_onto_headers", return_value={"X-API-Key": "secret"}
        ), patch.object(api_resources, "clone_object_to_realm_request", side_effect=delayed_clone):
            result = asyncio.run(exercise())

        envelope = json.loads(result.content[0].text)
        self.assertTrue(result.is_error)
        self.assertEqual(envelope["error"]["code"], "outcome_unknown")
        self.assertFalse(envelope["error"]["retryable"])
        self.assertEqual(
            envelope["error"]["recovery"],
            {"action": "call_get_clone_object_to_realm_result"},
        )

    def test_result_tool_outer_timeout_is_retryable_read_only_error(self) -> None:
        def delayed_read(*args, **kwargs):
            time.sleep(0.05)
            return CloneObjectToRealmNotFound(found=False)

        async def exercise():
            async with Client(server.mcp) as client:
                return await client.call_tool(
                    "get_clone_object_to_realm_result",
                    {
                        "source_realm_id": "11111111-1111-4111-8111-111111111111",
                        "source_object_id": "22222222-2222-4222-8222-222222222222",
                        "target_realm_id": REALM_ID,
                    },
                    raise_on_error=False,
                )

        with patch.object(api_resources, "_HTTP_MCP_TOOL_TIMEOUT_SECONDS", 0.001), patch.object(
            api_resources, "_onto_headers", return_value={"X-API-Key": "secret"}
        ), patch.object(
            api_resources,
            "get_clone_object_to_realm_result_request",
            side_effect=delayed_read,
        ):
            result = asyncio.run(exercise())

        envelope = json.loads(result.content[0].text)
        self.assertTrue(result.is_error)
        self.assertEqual(envelope["error"]["code"], "result_dependency_unavailable")
        self.assertTrue(envelope["error"]["retryable"])
        self.assertEqual(
            envelope["error"]["recovery"],
            {"action": "retry_get_clone_object_to_realm_result"},
        )

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
