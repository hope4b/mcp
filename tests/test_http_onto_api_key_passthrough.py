from __future__ import annotations

import contextvars
import sys
import types
import unittest
from contextlib import ExitStack
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
from onto_mcp.realm_object_clone import CloneObjectToRealmNotFound, CloneObjectToRealmResult


class _Request:
    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


class HttpOntoApiKeyPassthroughTests(unittest.TestCase):
    def test_tool_timeout_wrapper_preserves_http_request_context(self) -> None:
        request_context: contextvars.ContextVar[_Request | None] = contextvars.ContextVar(
            "test_http_request",
            default=None,
        )

        def context_request() -> _Request:
            request = request_context.get()
            if request is None:
                raise RuntimeError("no request")
            return request

        @api_resources.mcp.tool
        def passthrough_probe() -> str:
            return api_resources._onto_headers()["X-API-Key"]

        token = request_context.set(_Request({"X-Onto-Api-Key": "client-key"}))
        try:
            with patch.object(api_resources, "IS_HTTP_TRANSPORT", True), patch.object(
                api_resources, "ONTO_API_KEY", ""
            ), patch.object(api_resources, "ONTO_API_KEY_HEADER", "X-API-Key"), patch.object(
                api_resources, "ONTO_API_KEY_PASSTHROUGH_HEADER", "X-Onto-Api-Key"
            ), patch.object(api_resources, "get_http_request", side_effect=context_request):
                result = passthrough_probe()
        finally:
            request_context.reset(token)

        self.assertEqual(result, "client-key")

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

    def test_clone_post_and_result_get_forward_http_caller_key_as_x_api_key(self) -> None:
        clone_result = CloneObjectToRealmResult(
            target_realm_id="33333333-3333-4333-8333-333333333333",
            target_object_id="55555555-5555-4555-8555-555555555555",
            primary_realm_id="11111111-1111-4111-8111-111111111111",
            primary_object_id="22222222-2222-4222-8222-222222222222",
            created=True,
        )
        with patch.object(api_resources, "IS_HTTP_TRANSPORT", True), patch.object(
            api_resources, "ONTO_API_KEY", "configured-key-must-not-win"
        ), patch.object(api_resources, "ONTO_API_KEY_HEADER", "X-API-Key"), patch.object(
            api_resources, "ONTO_API_KEY_PASSTHROUGH_HEADER", "X-Onto-Api-Key"
        ), patch.object(
            api_resources,
            "get_http_request",
            return_value=_Request({"X-Onto-Api-Key": "caller-key"}),
        ), patch.object(
            api_resources, "clone_object_to_realm_request", return_value=clone_result
        ) as post_adapter, patch.object(
            api_resources,
            "get_clone_object_to_realm_result_request",
            return_value=CloneObjectToRealmNotFound(found=False),
        ) as get_adapter:
            write_value = api_resources.clone_object_to_realm(
                "11111111-1111-4111-8111-111111111111",
                "22222222-2222-4222-8222-222222222222",
                "33333333-3333-4333-8333-333333333333",
                "44444444-4444-4444-8444-444444444444",
            )
            read_value = api_resources.get_clone_object_to_realm_result(
                "11111111-1111-4111-8111-111111111111",
                "22222222-2222-4222-8222-222222222222",
                "33333333-3333-4333-8333-333333333333",
            )

        self.assertEqual(write_value, clone_result)
        self.assertEqual(read_value.model_dump(), {"found": False})
        for adapter in (post_adapter, get_adapter):
            self.assertEqual(adapter.call_args.kwargs["headers"]["X-API-Key"], "caller-key")
            self.assertNotIn("X-Onto-Api-Key", adapter.call_args.kwargs["headers"])
            self.assertNotIn("caller-key", repr(adapter.return_value))

    def test_clone_operations_use_configured_fallback_in_http_and_stdio_modes(self) -> None:
        scenarios = ((True, _Request({})), (False, None))
        for is_http, request in scenarios:
            with self.subTest(is_http=is_http):
                with ExitStack() as stack:
                    stack.enter_context(patch.object(api_resources, "IS_HTTP_TRANSPORT", is_http))
                    stack.enter_context(patch.object(api_resources, "ONTO_API_KEY", "configured-key"))
                    stack.enter_context(patch.object(api_resources, "ONTO_API_KEY_HEADER", "X-API-Key"))
                    stack.enter_context(
                        patch.object(
                            api_resources,
                            "ONTO_API_KEY_PASSTHROUGH_HEADER",
                            "X-Onto-Api-Key",
                        )
                    )
                    post_adapter = stack.enter_context(
                        patch.object(
                            api_resources,
                            "clone_object_to_realm_request",
                            return_value=CloneObjectToRealmResult(
                                target_realm_id="33333333-3333-4333-8333-333333333333",
                                target_object_id="55555555-5555-4555-8555-555555555555",
                                primary_realm_id="11111111-1111-4111-8111-111111111111",
                                primary_object_id="22222222-2222-4222-8222-222222222222",
                                created=False,
                            ),
                        )
                    )
                    get_adapter = stack.enter_context(
                        patch.object(
                            api_resources,
                            "get_clone_object_to_realm_result_request",
                            return_value=CloneObjectToRealmNotFound(found=False),
                        )
                    )
                    stack.enter_context(
                        patch.object(
                            api_resources,
                            "get_http_request",
                            return_value=request,
                        )
                        if is_http
                        else patch.object(
                            api_resources,
                            "get_http_request",
                            side_effect=AssertionError("stdio must not read HTTP context"),
                        )
                    )

                    api_resources.clone_object_to_realm(
                        "11111111-1111-4111-8111-111111111111",
                        "22222222-2222-4222-8222-222222222222",
                        "33333333-3333-4333-8333-333333333333",
                        "44444444-4444-4444-8444-444444444444",
                    )
                    api_resources.get_clone_object_to_realm_result(
                        "11111111-1111-4111-8111-111111111111",
                        "22222222-2222-4222-8222-222222222222",
                        "33333333-3333-4333-8333-333333333333",
                    )

                self.assertEqual(post_adapter.call_args.kwargs["headers"]["X-API-Key"], "configured-key")
                self.assertEqual(get_adapter.call_args.kwargs["headers"]["X-API-Key"], "configured-key")
                self.assertNotIn("configured-key", repr(post_adapter.return_value))
                self.assertNotIn("configured-key", repr(get_adapter.return_value))


if __name__ == "__main__":
    unittest.main()
