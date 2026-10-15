from __future__ import annotations

from contextlib import contextmanager
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import logging
import types
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from onto_mcp import api_resources
from onto_mcp import server
from onto_mcp.http_auth import (
    InvalidHttpCredentials,
    classify_http_api_key,
    reset_http_api_key,
    set_http_api_key,
)
from onto_mcp.realm_object_clone import CloneObjectToRealmResult


class RawHttpCredentialClassifierTests(unittest.TestCase):
    def test_accepts_each_supported_name_case_insensitively_and_dual_equal(self) -> None:
        cases = (
            ([(b"X-API-Key", b"standard")], b"standard"),
            ([(b"x-OnTo-ApI-kEy", b"legacy")], b"legacy"),
            (
                [(b"X-API-Key", b" same "), (b"X-Onto-Api-Key", b" same ")],
                b" same ",
            ),
        )
        for headers, expected in cases:
            with self.subTest(headers=headers):
                self.assertEqual(classify_http_api_key(headers), expected)

    def test_absent_and_bearer_only_have_no_api_key_semantics(self) -> None:
        self.assertIsNone(classify_http_api_key([]))
        self.assertIsNone(classify_http_api_key([(b"Authorization", b"\tBEARER token")]))

    def test_rejects_every_malformed_or_ambiguous_api_key_set(self) -> None:
        cases = (
            [(b"X-API-Key", b"")],
            [(b"X-API-Key", b" \t")],
            [(b"X-API-Key", b"one,two")],
            [(b"X-API-Key", b"one"), (b"x-api-key", b"one")],
            [(b"X-Onto-Api-Key", b"one"), (b"X-Onto-Api-Key", b"two")],
            [(b"X-API-Key", b"one"), (b"X-Onto-Api-Key", b"two")],
            [(b"X-API-Key", b"one"), (b"Authorization", b"Bearer")],
            [(b"X-API-Key", b"one"), (b"Authorization", b" \tbEaReR\tvalue")],
            [
                (b"X-API-Key", b"one"),
                (b"Authorization", b"Basic abc"),
                (b"Authorization", b"Bearer token"),
            ],
        )
        for headers in cases:
            with self.subTest(headers=headers):
                with self.assertRaises(InvalidHttpCredentials):
                    classify_http_api_key(headers)

    def test_non_bearer_prefix_does_not_trigger_mixed_rejection(self) -> None:
        for authorization in (b"BearerX token", b"Bear", b"Basic token"):
            with self.subTest(authorization=authorization):
                self.assertEqual(
                    classify_http_api_key(
                        [(b"X-API-Key", b"one"), (b"Authorization", authorization)]
                    ),
                    b"one",
                )


class CanonicalProjectionTests(unittest.TestCase):
    def test_timeout_worker_preserves_validated_http_context(self) -> None:
        def probe() -> str:
            return api_resources._onto_headers()["X-API-Key"]

        wrapped = api_resources._wrap_tool_with_timeout(probe)
        token = set_http_api_key(b"client-key")
        try:
            with patch.object(api_resources, "IS_HTTP_TRANSPORT", True), patch.object(
                api_resources, "ONTO_API_KEY", "server-key-must-not-win"
            ):
                self.assertEqual(wrapped(), "client-key")
        finally:
            reset_http_api_key(token)

    def test_http_without_validated_context_never_falls_back(self) -> None:
        with patch.object(api_resources, "IS_HTTP_TRANSPORT", True), patch.object(
            api_resources, "ONTO_API_KEY", "server-key-must-not-win"
        ):
            with self.assertRaisesRegex(RuntimeError, "validated HTTP API key"):
                api_resources._onto_headers()

    def test_stdio_uses_configured_key_and_fixed_outbound_name(self) -> None:
        with patch.object(api_resources, "IS_HTTP_TRANSPORT", False), patch.object(
            api_resources, "ONTO_API_KEY", "stdio-key"
        ):
            headers = api_resources._onto_headers()
        self.assertEqual(headers["X-API-Key"], "stdio-key")
        self.assertNotIn("X-Onto-Api-Key", headers)
        self.assertNotIn("Authorization", headers)

    def test_clone_adapter_receives_only_canonical_http_header(self) -> None:
        result = CloneObjectToRealmResult(
            target_realm_id="33333333-3333-4333-8333-333333333333",
            target_object_id="55555555-5555-4555-8555-555555555555",
            primary_realm_id="11111111-1111-4111-8111-111111111111",
            primary_object_id="22222222-2222-4222-8222-222222222222",
            created=True,
        )
        token = set_http_api_key(b"caller-key")
        try:
            with patch.object(api_resources, "IS_HTTP_TRANSPORT", True), patch.object(
                api_resources, "ONTO_API_KEY", "configured-loser"
            ), patch.object(
                api_resources, "clone_object_to_realm_request", return_value=result
            ) as adapter:
                actual = api_resources.clone_object_to_realm(
                    "11111111-1111-4111-8111-111111111111",
                    "22222222-2222-4222-8222-222222222222",
                    "33333333-3333-4333-8333-333333333333",
                    "44444444-4444-4444-8444-444444444444",
                )
        finally:
            reset_http_api_key(token)

        self.assertEqual(actual, result)
        headers = adapter.call_args.kwargs["headers"]
        self.assertEqual(headers["X-API-Key"], "caller-key")
        self.assertNotIn("X-Onto-Api-Key", headers)
        self.assertNotIn("Authorization", headers)

    def test_dependency_failures_do_not_reflect_active_credential(self) -> None:
        sentinel = "unique-credential-sentinel"

        class ErrorResponse:
            status_code = 500
            text = f"upstream reflected {sentinel}"
            content = text.encode()

            def raise_for_status(self):
                raise api_resources.requests.exceptions.HTTPError(response=self)

        class InvalidJsonResponse:
            status_code = 200
            text = f"malformed {sentinel}"
            content = text.encode()

            def raise_for_status(self):
                return None

            def json(self):
                raise ValueError("invalid JSON")

        class ForbiddenResponse(ErrorResponse):
            status_code = 403

        class UnauthorizedResponse(ErrorResponse):
            status_code = 401

        timeout_type = getattr(api_resources.requests.exceptions, "Timeout", TimeoutError)
        failures = {
            "core-401": lambda: UnauthorizedResponse(),
            "core-403": lambda: ForbiddenResponse(),
            "core-500": lambda: ErrorResponse(),
            "malformed-response": lambda: InvalidJsonResponse(),
            "timeout": lambda: (_ for _ in ()).throw(
                timeout_type(f"timeout {sentinel}")
            ),
            "connection-error": lambda: (_ for _ in ()).throw(
                RuntimeError(f"connection {sentinel}")
            ),
        }
        for path, failure in failures.items():
            with self.subTest(path=path):
                stdout = io.StringIO()
                stderr = io.StringIO()
                captured_logs: list[str] = []

                class CaptureHandler(logging.Handler):
                    def emit(self, record):
                        captured_logs.append(self.format(record))

                handler = CaptureHandler()
                root_logger = logging.getLogger()
                root_logger.addHandler(handler)
                token = set_http_api_key(sentinel.encode())
                observability = {
                    "tool_name": "credential_redaction_probe",
                    "correlation_id": "safe-correlation-id",
                    "backend_request_sent": False,
                    "backend_response_received": False,
                }
                observability_token = api_resources._TOOL_OBSERVABILITY.set(
                    observability
                )
                try:
                    with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(
                        api_resources, "IS_HTTP_TRANSPORT", True
                    ), patch.object(
                        api_resources.requests, "request", side_effect=failure
                    ):
                        with self.assertRaises(RuntimeError) as exc:
                            api_resources._request_json("GET", "https://onto.invalid")
                finally:
                    api_resources._TOOL_OBSERVABILITY.reset(observability_token)
                    reset_http_api_key(token)
                    root_logger.removeHandler(handler)

                observable_channels = {
                    "exception": str(exc.exception),
                    "stdout": stdout.getvalue(),
                    "stderr": stderr.getvalue(),
                    "logs": captured_logs,
                    # This is the candidate's trace/metric source record. It
                    # deliberately contains state and correlation metadata,
                    # never request headers or credential values.
                    "observability": observability,
                }
                self.assertNotIn(
                    sentinel,
                    repr(observable_channels),
                    f"credential leaked through {path}",
                )

    def test_accepted_request_does_not_reflect_credential_in_result(self) -> None:
        sentinel = "accepted-credential-sentinel"

        class SuccessResponse:
            status_code = 200
            text = '{"result":"safe"}'
            content = text.encode()

            def raise_for_status(self):
                return None

            def json(self):
                return {"result": "safe"}

        token = set_http_api_key(sentinel.encode())
        try:
            with patch.object(
                api_resources, "IS_HTTP_TRANSPORT", True
            ), patch.object(
                api_resources.requests, "request", return_value=SuccessResponse()
            ) as request:
                result = api_resources._request_json("GET", "https://onto.invalid")
        finally:
            reset_http_api_key(token)

        self.assertEqual(result, {"result": "safe"})
        self.assertNotIn(sentinel, str(result))
        headers = request.call_args.kwargs["headers"]
        self.assertEqual(headers, {
            "X-API-Key": sentinel,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def test_production_http_boundary_keeps_sentinels_out_of_observable_channels(self) -> None:
        class Response:
            def __init__(
                self, status: int, credential: str, *, malformed: bool = False
            ) -> None:
                self.status_code = status
                self.text = f"dependency response containing {credential}"
                self.content = self.text.encode()
                self.malformed = malformed
                self.credential = credential

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise api_resources.requests.exceptions.HTTPError(response=self)

            def json(self):
                if self.malformed:
                    raise ValueError(f"malformed response containing {self.credential}")
                return {
                    "userRealmsRoles": [
                        {
                            "realmId": "11111111-1111-4111-8111-111111111111",
                            "realmName": "Safe realm",
                        }
                    ]
                }

        logger_names = (
            "fastmcp",
            "httpx",
            "httpcore",
            "mcp",
            "starlette",
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
        )

        def exercise(path: str, backend_effect) -> dict[str, object]:
            sentinel = f"credential-sentinel-{path}"
            backend_effect = backend_effect(sentinel)
            captured_logs: list[str] = []
            trace_events: list[object] = []

            class CaptureHandler(logging.Handler):
                def emit(self, record):
                    captured_logs.append(self.format(record))

            class Span:
                def set_attributes(self, attributes):
                    trace_events.append(("attributes", attributes))

            @contextmanager
            def capture_span(*args, **kwargs):
                trace_events.append(("span", args, kwargs))
                yield Span()

            handler = CaptureHandler()
            loggers = [logging.getLogger(), *(logging.getLogger(name) for name in logger_names)]
            for logger in loggers:
                logger.addHandler(handler)

            stdout = io.StringIO()
            stderr = io.StringIO()
            app = server._build_http_app()
            try:
                from fastmcp.server import server as fastmcp_server

                with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(
                    api_resources, "IS_HTTP_TRANSPORT", True
                ), patch.object(
                    api_resources.requests, "request", side_effect=backend_effect
                ), patch.object(
                    fastmcp_server, "server_span", side_effect=capture_span
                ), TestClient(app, raise_server_exceptions=False) as client:
                    base_headers = {
                        "accept": "application/json, text/event-stream",
                        "content-type": "application/json",
                        "x-api-key": sentinel,
                    }
                    initialized = client.post(
                        "/mcp",
                        headers=base_headers,
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {
                                "protocolVersion": "2025-06-18",
                                "capabilities": {},
                                "clientInfo": {"name": "sentinel-probe", "version": "1"},
                            },
                        },
                    )
                    session_headers = {
                        **base_headers,
                        "mcp-session-id": initialized.headers["mcp-session-id"],
                        "mcp-protocol-version": "2025-06-18",
                    }
                    client.post(
                        "/mcp",
                        headers=session_headers,
                        json={
                            "jsonrpc": "2.0",
                            "method": "notifications/initialized",
                            "params": {},
                        },
                    )
                    response = client.post(
                        "/mcp",
                        headers=session_headers,
                        json={
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {
                                "name": "list_available_realms",
                                "arguments": {},
                            },
                        },
                    )
            finally:
                for logger in loggers:
                    logger.removeHandler(handler)

            return {
                "response_status": response.status_code,
                "response_headers": dict(response.headers),
                "response_body": response.content,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "logs": captured_logs,
                "traces": trace_events,
            }

        timeout_type = getattr(api_resources.requests.exceptions, "Timeout", TimeoutError)
        paths = {
            "accepted": lambda credential: (
                lambda *args, **kwargs: Response(200, credential)
            ),
            "core-401": lambda credential: (
                lambda *args, **kwargs: Response(401, credential)
            ),
            "core-403": lambda credential: (
                lambda *args, **kwargs: Response(403, credential)
            ),
            "core-500": lambda credential: (
                lambda *args, **kwargs: Response(500, credential)
            ),
            "malformed": lambda credential: (
                lambda *args, **kwargs: Response(200, credential, malformed=True)
            ),
            "timeout": lambda credential: (
                lambda *args, **kwargs: (_ for _ in ()).throw(
                    timeout_type(f"timeout containing {credential}")
                )
            ),
            "connection": lambda credential: (
                lambda *args, **kwargs: (_ for _ in ()).throw(
                    RuntimeError(f"connection error containing {credential}")
                )
            ),
        }
        for path, backend_effect in paths.items():
            with self.subTest(path=path):
                channels = exercise(path, backend_effect)
                self.assertNotIn(f"credential-sentinel-{path}", repr(channels))

    def test_production_http_rejection_is_secret_free_before_fastmcp_dispatch(self) -> None:
        sentinel = "credential-sentinel-rejected"
        app = server._build_http_app()
        with patch.object(api_resources.requests, "request") as core_request, TestClient(
            app, raise_server_exceptions=False
        ) as client:
            response = client.post(
                "/mcp",
                headers=[
                    ("accept", "application/json, text/event-stream"),
                    ("content-type", "application/json"),
                    ("x-api-key", sentinel),
                    ("x-api-key", sentinel),
                ],
                content=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {},
                            "clientInfo": {"name": "rejection-probe", "version": "1"},
                        },
                    }
                ),
            )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(sentinel, repr(dict(response.headers)))
        self.assertNotIn(sentinel, response.text)
        core_request.assert_not_called()

    def test_candidate_configures_no_trace_or_metric_exporter(self) -> None:
        exporter_markers = (
            "meter_provider",
            "metric_exporter",
            "span_exporter",
            "tracer_provider",
        )
        for module in (api_resources, server):
            with self.subTest(module=module.__name__):
                exported_names = {name.lower() for name in vars(module)}
                self.assertFalse(exported_names.intersection(exporter_markers))
                exporter_objects = [
                    value
                    for value in vars(module).values()
                    if isinstance(value, types.ModuleType)
                    and value.__name__.startswith(("opentelemetry", "prometheus_client"))
                ]
                self.assertEqual(exporter_objects, [])


if __name__ == "__main__":
    unittest.main()
