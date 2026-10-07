from __future__ import annotations

import json
import threading
import time
import unittest
from unittest.mock import patch

import requests

from onto_mcp import realm_object_clone as clone


SOURCE_REALM_ID = "11111111-1111-4111-8111-111111111111"
SOURCE_OBJECT_ID = "22222222-2222-4222-8222-222222222222"
TARGET_REALM_ID = "33333333-3333-4333-8333-333333333333"
TARGET_TEMPLATE_ID = "44444444-4444-4444-8444-444444444444"
TARGET_OBJECT_ID = "55555555-5555-4555-8555-555555555555"
INVOCATION_ID = "66666666-6666-4666-8666-666666666666"
API_BASE = "https://onto.invalid/api/v2/core"
HEADERS = {"X-API-Key": "test-secret", "Accept": "application/json"}


class _Response:
    def __init__(self, status_code: int, body: object, *, json_error: Exception | None = None) -> None:
        self.status_code = status_code
        self._body = body
        self._json_error = json_error

    def json(self) -> object:
        if self._json_error is not None:
            raise self._json_error
        return self._body


def _wire_result(*, created: bool, **overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "targetRealmId": TARGET_REALM_ID,
        "targetObjectId": TARGET_OBJECT_ID,
        "primaryRealmId": SOURCE_REALM_ID,
        "primaryObjectId": SOURCE_OBJECT_ID,
        "created": created,
    }
    result.update(overrides)
    return result


def _backend_error(
    code: str,
    status: int,
    retryable: bool,
    *,
    correlation_id: object = "backend.trace-1",
    details: object | None = None,
) -> _Response:
    return _Response(
        status,
        {
            "error": {
                "code": code,
                "httpStatus": status,
                "retryable": retryable,
                "correlationId": correlation_id,
                "details": {} if details is None else details,
            }
        },
    )


def _write(request) -> clone.CloneObjectToRealmResult | clone.CloneToolError:
    return clone.clone_object_to_realm_request(
        source_realm_id=SOURCE_REALM_ID,
        source_object_id=SOURCE_OBJECT_ID,
        target_realm_id=TARGET_REALM_ID,
        target_template_id=TARGET_TEMPLATE_ID,
        api_base=API_BASE,
        headers=HEADERS,
        invocation_correlation_id=INVOCATION_ID,
        request=request,
    )


def _read(request) -> clone.CloneObjectToRealmLookupResult | clone.CloneToolError:
    return clone.get_clone_object_to_realm_result_request(
        source_realm_id=SOURCE_REALM_ID,
        source_object_id=SOURCE_OBJECT_ID,
        target_realm_id=TARGET_REALM_ID,
        api_base=API_BASE,
        headers=HEADERS,
        invocation_correlation_id=INVOCATION_ID,
        request=request,
    )


class CloneObjectToRealmTests(unittest.TestCase):
    def assert_tool_error(
        self,
        value: object,
        code: str,
        message: str,
        retryable: bool,
        action: str,
        *,
        correlation_id: str = INVOCATION_ID,
    ) -> None:
        self.assertIsInstance(value, clone.CloneToolError)
        payload = json.loads(value.serialized())
        self.assertEqual(set(payload), {"schema_version", "error"})
        self.assertIs(type(payload["schema_version"]), int)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(
            set(payload["error"]),
            {"code", "message", "correlation_id", "retryable", "recovery"},
        )
        self.assertEqual(
            payload["error"],
            {
                "code": code,
                "message": message,
                "correlation_id": correlation_id,
                "retryable": retryable,
                "recovery": {"action": action},
            },
        )

    def test_normal_write_is_exactly_one_post_with_closed_wire_shape(self) -> None:
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def request(*args, **kwargs):
            calls.append((args, kwargs))
            return _Response(201, _wire_result(created=True))

        with patch.object(clone.uuid, "uuid4", side_effect=AssertionError("no UUID generation")):
            result = _write(request)

        self.assertEqual(
            result.model_dump(),
            {
                "target_realm_id": TARGET_REALM_ID,
                "target_object_id": TARGET_OBJECT_ID,
                "primary_realm_id": SOURCE_REALM_ID,
                "primary_object_id": SOURCE_OBJECT_ID,
                "created": True,
            },
        )
        self.assertEqual(len(calls), 1)
        args, kwargs = calls[0]
        self.assertEqual(
            args,
            ("POST", f"{API_BASE}/realm/{TARGET_REALM_ID}/entity/clone-from-realm"),
        )
        self.assertEqual(
            kwargs,
            {
                "json": {
                    "sourceRealmId": SOURCE_REALM_ID,
                    "sourceObjectId": SOURCE_OBJECT_ID,
                    "targetTemplateId": TARGET_TEMPLATE_ID,
                },
                "headers": HEADERS,
                "allow_redirects": False,
                "timeout": (10, 25),
            },
        )
        self.assertNotIn("idempotency", json.dumps(kwargs).lower())

    def test_success_status_and_created_are_a_closed_pair(self) -> None:
        accepted = ((201, True), (200, False))
        for status, created in accepted:
            with self.subTest(status=status, created=created):
                result = _write(lambda *args, **kwargs: _Response(status, _wire_result(created=created)))
                self.assertIsInstance(result, clone.CloneObjectToRealmResult)
                self.assertEqual(result.created, created)

        rejected = ((201, False), (200, True), (202, True))
        for status, created in rejected:
            with self.subTest(status=status, created=created):
                result = _write(lambda *args, **kwargs: _Response(status, _wire_result(created=created)))
                self.assert_tool_error(
                    result,
                    "outcome_unknown",
                    "Clone outcome is unknown.",
                    False,
                    "call_get_clone_object_to_realm_result",
                )

    def test_success_requires_exact_five_fields_canonical_uuids_and_requested_identities(self) -> None:
        malformed = [
            {**_wire_result(created=True), "extra": "forbidden"},
            {key: value for key, value in _wire_result(created=True).items() if key != "created"},
            _wire_result(created=True, targetObjectId="AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"),
            _wire_result(created=True, targetRealmId=SOURCE_REALM_ID),
            _wire_result(created=True, primaryRealmId=TARGET_REALM_ID),
            _wire_result(created=True, primaryObjectId=TARGET_OBJECT_ID),
            _wire_result(created=1),
        ]
        for body in malformed:
            with self.subTest(body=body):
                result = _write(lambda *args, **kwargs: _Response(201, body))
                self.assert_tool_error(
                    result,
                    "outcome_unknown",
                    "Clone outcome is unknown.",
                    False,
                    "call_get_clone_object_to_realm_result",
                )

    def test_result_read_is_one_exact_get_and_never_posts(self) -> None:
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def request(*args, **kwargs):
            calls.append((args, kwargs))
            return _Response(200, {"found": True, "result": _wire_result(created=False)})

        result = _read(request)

        self.assertIsInstance(result, clone.CloneObjectToRealmResult)
        self.assertFalse(result.created)
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0],
            (
                ("GET", f"{API_BASE}/realm/{TARGET_REALM_ID}/entity/clone-from-realm/result"),
                {
                    "params": {
                        "sourceRealmId": SOURCE_REALM_ID,
                        "sourceObjectId": SOURCE_OBJECT_ID,
                    },
                    "headers": HEADERS,
                    "allow_redirects": False,
                    "timeout": (3, 7),
                },
            ),
        )
        self.assertNotIn("POST", repr(calls))

    def test_result_read_found_false_is_a_closed_lookup_result(self) -> None:
        result = _read(lambda *args, **kwargs: _Response(200, {"found": False}))
        self.assertIsInstance(result, clone.CloneObjectToRealmNotFound)
        self.assertEqual(result.model_dump(), {"found": False})

    def test_result_read_rejects_malformed_or_non_immediate_source_results(self) -> None:
        bodies = [
            {"found": False, "result": None},
            {"found": True},
            {"found": True, "result": _wire_result(created=True)},
            {"found": True, "result": _wire_result(created=False, primaryObjectId=TARGET_OBJECT_ID)},
            {"found": True, "result": {**_wire_result(created=False), "extra": 1}},
        ]
        for body in bodies:
            with self.subTest(body=body):
                result = _read(lambda *args, **kwargs: _Response(200, body))
                self.assert_tool_error(
                    result,
                    "invalid_backend_response",
                    "Clone service returned an invalid response.",
                    False,
                    "none",
                )

    def test_dispatched_connection_loss_permits_one_get_and_returns_found_as_created_false(self) -> None:
        methods: list[str] = []

        def request(method, url, **kwargs):
            methods.append(method)
            if method == "POST":
                raise requests.exceptions.ConnectionError("secret exception text")
            return _Response(200, {"found": True, "result": _wire_result(created=False)})

        result = _write(request)

        self.assertIsInstance(result, clone.CloneObjectToRealmResult)
        self.assertFalse(result.created)
        self.assertEqual(methods, ["POST", "GET"])

    def test_non_dispatched_post_failures_never_issue_result_get(self) -> None:
        failures = (
            requests.exceptions.ConnectTimeout("connect did not complete"),
            requests.exceptions.InvalidURL("invalid URL"),
            requests.exceptions.InvalidSchema("invalid schema"),
            requests.exceptions.MissingSchema("missing schema"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                methods: list[str] = []

                def request(method, url, **kwargs):
                    methods.append(method)
                    raise failure

                result = _write(request)

                self.assertEqual(methods, ["POST"])
                self.assert_tool_error(
                    result,
                    "clone_dependency_unavailable",
                    "Clone dependency is temporarily unavailable.",
                    True,
                    "retry_clone_object_to_realm",
                )

    def test_unresolved_ambiguous_write_never_reposts_and_returns_safe_outcome_unknown(self) -> None:
        recovery_outcomes = (
            _Response(200, {"found": False}),
            _Response(200, {"found": True, "result": {"malformed": True}}),
            requests.exceptions.Timeout("credential=test-secret backend-body=secret"),
        )
        for recovery_outcome in recovery_outcomes:
            with self.subTest(recovery_outcome=recovery_outcome):
                methods: list[str] = []

                def request(method, url, **kwargs):
                    methods.append(method)
                    if method == "POST":
                        raise requests.exceptions.Timeout("post dispatched")
                    if isinstance(recovery_outcome, Exception):
                        raise recovery_outcome
                    return recovery_outcome

                result = _write(request)
                self.assertEqual(methods, ["POST", "GET"])
                self.assert_tool_error(
                    result,
                    "outcome_unknown",
                    "Clone outcome is unknown.",
                    False,
                    "call_get_clone_object_to_realm_result",
                )
                serialized = result.serialized()
                self.assertNotIn("test-secret", serialized)
                self.assertNotIn("backend-body", serialized)
                self.assertNotIn("post dispatched", serialized)

    def test_other_potentially_dispatched_failures_use_read_only_recovery(self) -> None:
        failures = (
            requests.exceptions.ChunkedEncodingError("response interrupted"),
            requests.exceptions.TooManyRedirects("redirect limit reached"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                methods: list[str] = []

                def request(method, url, **kwargs):
                    methods.append(method)
                    if method == "POST":
                        raise failure
                    return _Response(200, {"found": False})

                result = _write(request)

                self.assertEqual(methods, ["POST", "GET"])
                self.assert_tool_error(
                    result,
                    "outcome_unknown",
                    "Clone outcome is unknown.",
                    False,
                    "call_get_clone_object_to_realm_result",
                )

    def test_standalone_result_transport_failure_is_retryable_read_only_error(self) -> None:
        calls = 0

        def request(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise requests.exceptions.Timeout("do not expose")

        result = _read(request)
        self.assertEqual(calls, 1)
        self.assert_tool_error(
            result,
            "result_dependency_unavailable",
            "Clone result service is temporarily unavailable.",
            True,
            "retry_get_clone_object_to_realm_result",
        )
        self.assertNotIn("do not expose", result.serialized())

    def test_post_backend_error_table_is_exact_and_safe(self) -> None:
        table = {
            "invalid_request": (400, False, "Clone request is invalid.", "none"),
            "unauthenticated": (401, False, "Authentication is required.", "none"),
            "source_access_denied": (403, False, "Source realm access is denied.", "none"),
            "target_create_denied": (403, False, "Target realm create access is denied.", "none"),
            "source_realm_not_found": (404, False, "Source realm was not found.", "none"),
            "target_realm_not_found": (404, False, "Target realm was not found.", "none"),
            "source_object_not_found": (404, False, "Source object was not found.", "none"),
            "target_template_not_found": (404, False, "Target template was not found.", "none"),
            "clone_failed": (500, False, "Clone operation failed.", "none"),
            "clone_dependency_unavailable": (
                503,
                True,
                "Clone dependency is temporarily unavailable.",
                "retry_clone_object_to_realm",
            ),
        }
        for code, (status, retryable, message, action) in table.items():
            with self.subTest(code=code):
                result = _write(lambda *args, response=_backend_error(code, status, retryable), **kwargs: response)
                self.assert_tool_error(
                    result,
                    code,
                    message,
                    retryable,
                    action,
                    correlation_id="backend.trace-1",
                )

    def test_result_backend_error_table_and_503_translation_are_exact(self) -> None:
        table = {
            "invalid_request": (400, "invalid_request", "Clone request is invalid."),
            "unauthenticated": (401, "unauthenticated", "Authentication is required."),
            "source_access_denied": (403, "source_access_denied", "Source realm access is denied."),
            "target_read_denied": (403, "target_read_denied", "Target realm read access is denied."),
            "source_realm_not_found": (404, "source_realm_not_found", "Source realm was not found."),
            "target_realm_not_found": (404, "target_realm_not_found", "Target realm was not found."),
            "source_object_not_found": (404, "source_object_not_found", "Source object was not found."),
            "clone_failed": (500, "clone_failed", "Clone operation failed."),
            "clone_dependency_unavailable": (
                503,
                "result_dependency_unavailable",
                "Clone result service is temporarily unavailable.",
            ),
        }
        for backend_code, (status, public_code, message) in table.items():
            with self.subTest(code=backend_code):
                retryable = backend_code == "clone_dependency_unavailable"
                result = _read(
                    lambda *args, response=_backend_error(backend_code, status, retryable), **kwargs: response
                )
                self.assert_tool_error(
                    result,
                    public_code,
                    message,
                    retryable,
                    "retry_get_clone_object_to_realm_result" if retryable else "none",
                    correlation_id="backend.trace-1",
                )

    def test_cross_operation_and_mismatched_backend_errors_fail_closed(self) -> None:
        cases = [
            ("post", _backend_error("target_read_denied", 403, False)),
            ("result", _backend_error("target_create_denied", 403, False)),
            ("result", _backend_error("target_template_not_found", 404, False)),
            ("post", _backend_error("clone_dependency_unavailable", 500, True)),
            ("post", _backend_error("clone_dependency_unavailable", 503, False)),
            ("post", _backend_error("unknown_code", 418, False)),
        ]
        for operation, response in cases:
            with self.subTest(operation=operation, body=response._body):
                result = (
                    _write(lambda *args, **kwargs: response)
                    if operation == "post"
                    else _read(lambda *args, **kwargs: response)
                )
                self.assert_tool_error(
                    result,
                    "invalid_backend_response",
                    "Clone service returned an invalid response.",
                    False,
                    "none",
                )

    def test_backend_error_envelope_is_closed_and_backend_content_is_never_trusted(self) -> None:
        valid = _backend_error("clone_failed", 500, False)._body
        variants = [
            {**valid, "schema_version": 1},
            {"error": {**valid["error"], "message": "unsafe"}},
            {"error": {**valid["error"], "recovery": {"action": "retry"}}},
            {"error": {**valid["error"], "details": {"secret": "source content"}}},
            {"error": {key: value for key, value in valid["error"].items() if key != "code"}},
            {"error": "not-an-object"},
            [valid],
        ]
        for body in variants:
            with self.subTest(body=body):
                result = _write(lambda *args, **kwargs: _Response(500, body))
                self.assert_tool_error(
                    result,
                    "invalid_backend_response",
                    "Clone service returned an invalid response.",
                    False,
                    "none",
                )
                self.assertNotIn("unsafe", result.serialized())
                self.assertNotIn("source content", result.serialized())

    def test_correlation_id_is_preserved_only_for_ascii_frozen_predicate(self) -> None:
        valid_values = ("A", "trace.id:part_2-3", "x" * 128)
        invalid_values = ("", "x" * 129, "ümlaut", "line\nbreak", None, 7)
        for correlation_id in valid_values:
            with self.subTest(valid=correlation_id):
                result = _write(
                    lambda *args, response=_backend_error(
                        "clone_failed", 500, False, correlation_id=correlation_id
                    ), **kwargs: response
                )
                self.assertEqual(result.error.correlation_id, correlation_id)
        for correlation_id in invalid_values:
            with self.subTest(invalid=correlation_id):
                result = _write(
                    lambda *args, response=_backend_error(
                        "clone_failed", 500, False, correlation_id=correlation_id
                    ), **kwargs: response
                )
                self.assertEqual(result.error.correlation_id, INVOCATION_ID)
                if correlation_id:
                    self.assertNotIn(str(correlation_id), result.serialized())

    def test_invalid_inputs_make_no_network_call(self) -> None:
        def forbidden(*args, **kwargs):
            raise AssertionError("network must not be called")

        result = clone.clone_object_to_realm_request(
            source_realm_id="AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
            source_object_id=SOURCE_OBJECT_ID,
            target_realm_id=TARGET_REALM_ID,
            target_template_id=TARGET_TEMPLATE_ID,
            api_base=API_BASE,
            headers=HEADERS,
            invocation_correlation_id=INVOCATION_ID,
            request=forbidden,
        )
        self.assert_tool_error(
            result,
            "invalid_request",
            "Clone request is invalid.",
            False,
            "none",
        )

    def test_post_total_deadline_is_monotonic_and_discards_late_success(self) -> None:
        release_post = threading.Event()
        post_finished = threading.Event()
        methods: list[str] = []

        def request(method, url, **kwargs):
            methods.append(method)
            if method == "POST":
                release_post.wait(1)
                post_finished.set()
                return _Response(201, _wire_result(created=True))
            return _Response(200, {"found": False})

        started_at = time.monotonic()
        with patch.object(clone, "CLONE_POST_TIMEOUT_SECONDS", 0.01):
            result = _write(request)
        elapsed = time.monotonic() - started_at

        self.assertLess(elapsed, 0.2)
        self.assertEqual(methods, ["POST", "GET"])
        self.assert_tool_error(
            result,
            "outcome_unknown",
            "Clone outcome is unknown.",
            False,
            "call_get_clone_object_to_realm_result",
        )
        release_post.set()
        self.assertTrue(post_finished.wait(0.2))

    def test_result_total_deadline_is_monotonic_and_returns_read_only_error(self) -> None:
        release_request = threading.Event()
        request_finished = threading.Event()

        def request(*args, **kwargs):
            release_request.wait(1)
            request_finished.set()
            return _Response(200, {"found": True, "result": _wire_result(created=False)})

        started_at = time.monotonic()
        with patch.object(clone, "CLONE_RESULT_TIMEOUT_SECONDS", 0.01):
            result = _read(request)
        elapsed = time.monotonic() - started_at

        self.assertLess(elapsed, 0.2)
        self.assert_tool_error(
            result,
            "result_dependency_unavailable",
            "Clone result service is temporarily unavailable.",
            True,
            "retry_get_clone_object_to_realm_result",
        )
        release_request.set()
        self.assertTrue(request_finished.wait(0.2))

    def test_timeout_budgets_leave_margin_below_outer_wrapper(self) -> None:
        self.assertEqual(clone.CLONE_POST_TIMEOUT_SECONDS, 35)
        self.assertEqual(clone.CLONE_RESULT_TIMEOUT_SECONDS, 10)
        self.assertEqual(
            clone.CLONE_POST_CONNECT_TIMEOUT_SECONDS + clone.CLONE_POST_READ_TIMEOUT_SECONDS,
            clone.CLONE_POST_TIMEOUT_SECONDS,
        )
        self.assertEqual(
            clone.CLONE_RESULT_CONNECT_TIMEOUT_SECONDS + clone.CLONE_RESULT_READ_TIMEOUT_SECONDS,
            clone.CLONE_RESULT_TIMEOUT_SECONDS,
        )
        self.assertLessEqual(
            clone.CLONE_POST_TIMEOUT_SECONDS + clone.CLONE_RESULT_TIMEOUT_SECONDS + 10,
            60,
        )


if __name__ == "__main__":
    unittest.main()
