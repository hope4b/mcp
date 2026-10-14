from __future__ import annotations

import unittest
from unittest.mock import patch

from onto_mcp import api_resources
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

        failures = (
            lambda: ErrorResponse(),
            lambda: InvalidJsonResponse(),
            lambda: (_ for _ in ()).throw(RuntimeError(f"connection {sentinel}")),
        )
        for failure in failures:
            with self.subTest(failure=failure):
                token = set_http_api_key(sentinel.encode())
                try:
                    with patch.object(
                        api_resources, "IS_HTTP_TRANSPORT", True
                    ), patch.object(
                        api_resources.requests, "request", side_effect=failure
                    ):
                        with self.assertRaises(RuntimeError) as exc:
                            api_resources._request_json("GET", "https://onto.invalid")
                finally:
                    reset_http_api_key(token)
                self.assertNotIn(sentinel, str(exc.exception))


if __name__ == "__main__":
    unittest.main()
