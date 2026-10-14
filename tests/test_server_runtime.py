from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
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


_PUBLIC_CONTRACT_PROBE = r"""
import asyncio
from importlib import metadata
import json
import platform
import uuid

from fastmcp import Client
from onto_mcp.server import mcp


# Invalid-call envelopes include a generated correlation ID. Pin the UUID
# source so candidate and baseline probes compare the scalar value itself
# instead of comparing two unrelated random values.
uuid.uuid4 = lambda: uuid.UUID("00000000-0000-4000-8000-000000000001")


def model_dump(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=False)
    if all(hasattr(value, attribute) for attribute in ("content", "is_error")):
        return {
            "content": [model_dump(item) for item in value.content],
            "structuredContent": model_dump(
                getattr(value, "structured_content", None)
            ),
            "data": model_dump(getattr(value, "data", None)),
            "isError": value.is_error,
        }
    if isinstance(value, dict):
        return {key: model_dump(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [model_dump(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"Unsupported protocol model: {type(value)!r}")


async def capture():
    snapshot = []
    async with Client(mcp) as client:
        tools = sorted(await client.list_tools(), key=lambda tool: tool.name)
        for tool in tools:
            tool_metadata = model_dump(tool)
            input_schema = tool_metadata.get("inputSchema", {})
            invalid_arguments = (
                {} if input_schema.get("required")
                else {"__contract_probe_unknown__": True}
            )
            result = await client.call_tool(
                tool.name,
                invalid_arguments,
                raise_on_error=False,
            )
            result_envelope = model_dump(result)
            if not result_envelope.get("isError", result_envelope.get("is_error", False)):
                raise AssertionError(
                    f"Contract probe unexpectedly executed public tool {tool.name}"
                )
            snapshot.append(
                {
                    "metadata": tool_metadata,
                    "deterministic_error_envelope": result_envelope,
                }
            )
    contract = {
        "runtime": {
            "python": platform.python_version(),
            "fastmcp": metadata.version("fastmcp"),
        },
        "tools": snapshot,
    }
    print("PUBLIC_CONTRACT_SNAPSHOT=" + json.dumps(contract, sort_keys=True))


asyncio.run(capture())
"""


def _public_contract_snapshot(source_root: Path) -> object:
    environment = os.environ.copy()
    environment.update(
        {
            "MCP_TRANSPORT": "stdio",
            "ONTO_API_BASE": "https://contract-probe.invalid/api/v2/core",
            "ONTO_API_KEY": "contract-probe-key",
            "PYTHONPATH": str(source_root),
        }
    )
    completed = subprocess.run(
        [sys.executable, "-c", _PUBLIC_CONTRACT_PROBE],
        cwd=source_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "Public contract probe failed for "
            f"{source_root}: stdout={completed.stdout!r}, stderr={completed.stderr!r}"
        )
    prefix = "PUBLIC_CONTRACT_SNAPSHOT="
    snapshot_lines = [
        line[len(prefix) :]
        for line in completed.stdout.splitlines()
        if line.startswith(prefix)
    ]
    if len(snapshot_lines) != 1:
        raise AssertionError(
            f"Public contract probe emitted no unique snapshot for {source_root}"
        )
    return json.loads(snapshot_lines[0])


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

    def test_http_api_key_boundary_rejects_before_dispatch_without_secret_echo(self) -> None:
        called = False

        async def inner_app(scope, receive, send):
            nonlocal called
            called = True

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        sent: list[dict[str, object]] = []

        async def send(message):
            sent.append(message)

        sentinel = b"credential-sentinel"
        app = server.HttpApiKeyASGIApp(inner_app)
        asyncio.run(
            app(
                {
                    "type": "http",
                    "path": "/mcp",
                    "headers": [(b"x-api-key", sentinel), (b"x-api-key", sentinel)],
                },
                receive,
                send,
            )
        )

        self.assertFalse(called)
        self.assertEqual(sent[0]["status"], 400)
        self.assertNotIn(sentinel, sent[1]["body"])

    def test_http_api_key_boundary_scopes_and_cleans_validated_credential(self) -> None:
        observed: list[str] = []

        async def inner_app(scope, receive, send):
            with patch.object(api_resources, "IS_HTTP_TRANSPORT", True):
                observed.append(api_resources._onto_headers()["X-API-Key"])
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            return None

        app = server.HttpApiKeyASGIApp(inner_app)
        asyncio.run(
            app(
                {
                    "type": "http",
                    "path": "/mcp",
                    "headers": [(b"X-Onto-Api-Key", b"caller-key")],
                },
                receive,
                send,
            )
        )

        self.assertEqual(observed, ["caller-key"])
        with patch.object(api_resources, "IS_HTTP_TRANSPORT", True):
            with self.assertRaises(RuntimeError):
                api_resources._onto_headers()

    def test_http_api_key_boundary_isolates_overlapping_streaming_requests(self) -> None:
        first_chunks_sent = 0
        both_streaming = asyncio.Event()
        observed: dict[str, list[str]] = {}

        class SuccessResponse:
            status_code = 200
            content = b'{"safe":true}'

            def raise_for_status(self):
                return None

            def json(self):
                return {"safe": True}

        def core_request(method, url, **kwargs):
            request_name = url.rsplit("/", 1)[-1]
            observed.setdefault(request_name, []).append(
                kwargs["headers"]["X-API-Key"]
            )
            self.assertNotIn("X-Onto-Api-Key", kwargs["headers"])
            self.assertNotIn("Authorization", kwargs["headers"])
            return SuccessResponse()

        async def inner_app(scope, receive, send):
            nonlocal first_chunks_sent
            request_name = scope["request_name"]
            api_resources._request_json(
                "GET", f"https://core.invalid/{request_name}"
            )
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send(
                {
                    "type": "http.response.body",
                    "body": request_name.encode("ascii"),
                    "more_body": True,
                }
            )
            first_chunks_sent += 1
            if first_chunks_sent == 2:
                both_streaming.set()
            await both_streaming.wait()
            await asyncio.sleep(0)
            api_resources._request_json(
                "GET", f"https://core.invalid/{request_name}"
            )
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        sent: dict[str, list[dict[str, object]]] = {"one": [], "two": []}

        async def exercise() -> None:
            app = server.HttpApiKeyASGIApp(inner_app)

            async def invoke(name: str, credential: bytes) -> None:
                async def send(message):
                    sent[name].append(message)

                await app(
                    {
                        "type": "http",
                        "path": "/mcp",
                        "request_name": name,
                        "headers": [(b"x-api-key", credential)],
                    },
                    receive,
                    send,
                )

            await asyncio.gather(
                invoke("one", b"credential-one"),
                invoke("two", b"credential-two"),
            )

        with patch.object(api_resources, "IS_HTTP_TRANSPORT", True), patch.object(
            api_resources.requests, "request", side_effect=core_request
        ):
            asyncio.run(exercise())

        self.assertEqual(observed["one"], ["credential-one", "credential-one"])
        self.assertEqual(observed["two"], ["credential-two", "credential-two"])
        self.assertTrue(sent["one"][1]["more_body"])
        self.assertTrue(sent["two"][1]["more_body"])
        self.assertNotIn(b"credential-one", repr(sent["one"]).encode())
        self.assertNotIn(b"credential-two", repr(sent["two"]).encode())
        with patch.object(api_resources, "IS_HTTP_TRANSPORT", True):
            with self.assertRaises(RuntimeError):
                api_resources._onto_headers()

    def test_public_tool_contract_matches_read_only_pre_change_baseline(self) -> None:
        baseline_value = os.environ.get("GENERIC_QA_BASELINE_ROOT", "")
        self.assertTrue(
            baseline_value,
            "GENERIC_QA_BASELINE_ROOT is required for the public contract oracle",
        )
        baseline_root = Path(baseline_value).resolve()
        candidate_root = Path(__file__).resolve().parents[1]
        self.assertTrue((baseline_root / "onto_mcp" / "server.py").is_file())
        self.assertEqual(
            os.environ.get("GENERIC_QA_BASE_SHA"),
            "636577f6375bf4aa3c910ff821bb4083e5c71857",
        )

        baseline = _public_contract_snapshot(baseline_root)
        candidate = _public_contract_snapshot(candidate_root)
        self.assertEqual(candidate["runtime"], baseline["runtime"])
        baseline_tools = {
            item["metadata"]["name"]: item for item in baseline["tools"]
        }
        candidate_tools = {
            item["metadata"]["name"]: item for item in candidate["tools"]
        }
        self.assertEqual(candidate_tools.keys(), baseline_tools.keys())
        for tool_name in sorted(baseline_tools):
            with self.subTest(tool_name=tool_name):
                self.assertEqual(
                    candidate_tools[tool_name],
                    baseline_tools[tool_name],
                    "Public MCP metadata, output schema, protocol metadata, or "
                    "deterministic error envelope changed. Only JSON object-key "
                    "order is normalized; arrays and scalar values are preserved.",
                )

    def test_rejected_http_credentials_have_no_dispatch_or_core_side_effects(self) -> None:
        dispatches = 0

        async def inner_app(scope, receive, send):
            nonlocal dispatches
            dispatches += 1

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        sent: list[dict[str, object]] = []

        async def send(message):
            sent.append(message)

        app = server.HttpApiKeyASGIApp(inner_app)
        with patch.object(api_resources.requests, "request") as core_request:
            asyncio.run(
                app(
                    {
                        "type": "http",
                        "path": "/mcp",
                        "headers": [
                            (b"x-api-key", b"credential-one"),
                            (b"x-api-key", b"credential-two"),
                        ],
                    },
                    receive,
                    send,
                )
            )

        self.assertEqual(dispatches, 0)
        core_request.assert_not_called()
        self.assertEqual(sent[0]["status"], 400)

    def test_http_api_key_boundary_leaves_unrelated_routes_unchanged(self) -> None:
        observed: list[str] = []

        async def inner_app(scope, receive, send):
            observed.append(scope["path"])
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            return None

        app = server.HttpApiKeyASGIApp(inner_app)
        asyncio.run(
            app(
                {
                    "type": "http",
                    "path": "/unrelated",
                    "headers": [(b"x-api-key", b"one"), (b"x-api-key", b"two")],
                },
                receive,
                send,
            )
        )
        self.assertEqual(observed, ["/unrelated"])

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
