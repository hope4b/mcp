from __future__ import annotations

import hashlib
import json
import sys
import types
import unittest
from unittest.mock import patch


if "fastmcp" not in sys.modules:
    fastmcp_stub = types.ModuleType("fastmcp")
    exceptions_stub = types.ModuleType("fastmcp.exceptions")
    server_stub = types.ModuleType("fastmcp.server")
    context_stub = types.ModuleType("fastmcp.server.context")
    dependencies_stub = types.ModuleType("fastmcp.server.dependencies")

    class _FastMCP:
        def __init__(self, name: str) -> None:
            self.name = name

        def tool(self, fn):
            return fn

        def resource(self, *args, **kwargs):
            return lambda fn: fn

    class _Context:
        pass

    class _ToolError(Exception):
        pass

    fastmcp_stub.FastMCP = _FastMCP
    exceptions_stub.ToolError = _ToolError
    context_stub.Context = _Context
    dependencies_stub.get_http_request = lambda: (_ for _ in ()).throw(
        RuntimeError("no request")
    )
    sys.modules["fastmcp"] = fastmcp_stub
    sys.modules["fastmcp.exceptions"] = exceptions_stub
    sys.modules["fastmcp.server"] = server_stub
    sys.modules["fastmcp.server.context"] = context_stub
    sys.modules["fastmcp.server.dependencies"] = dependencies_stub

if "fastmcp.exceptions" not in sys.modules:
    exceptions_stub = types.ModuleType("fastmcp.exceptions")

    class _ToolError(Exception):
        pass

    exceptions_stub.ToolError = _ToolError
    sys.modules["fastmcp.exceptions"] = exceptions_stub

from fastmcp.exceptions import ToolError

from onto_mcp import api_resources
from onto_mcp.realm_declaration import RealmDeclarationError, resolve_realm_declaration


REALM_ID = "000ba00a-00a0-0a00-a000-000a0a0a0aa3"
ARTIFACT_ID = "11111111-1111-4111-8111-111111111111"
API_BASE = "https://example.invalid/api/v2/core"


def declaration_body(**updates) -> str:
    document = {
        "boundaries": ["This declaration is a navigation contract."],
        "declaration_contract_id": "realm_declaration",
        "declaration_contract_version": 1,
        "purpose": "Describe this realm through supported entry tools.",
        "realm_id": REALM_ID,
        "routes": [
            {
                "authoritative_result": "The supported result.",
                "need": "Obtain current information.",
                "stop_condition": "Stop when the result is unavailable.",
                "tool_entry_point": "list_available_realms",
            }
        ],
    }
    document.update(updates)
    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def success_payload(body: str | None = None, **updates):
    body = declaration_body() if body is None else body
    payload = {
        "realm_id": REALM_ID,
        "artifact_path": "realm/declaration",
        "artifact_id": ARTIFACT_ID,
        "artifact_kind": "decision",
        "declaration_contract_id": "realm_declaration",
        "declaration_contract_version": 1,
        "status": "accepted",
        "accepted_at": "2026-09-07T12:34:56.123456Z",
        "lifecycle": "accepted_current",
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "body": body,
    }
    payload.update(updates)
    return payload


class Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class RequestLedger:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error:
            raise self.error
        return self.response


def resolve_with(ledger: RequestLedger, realm_id: str = REALM_ID):
    return resolve_realm_declaration(
        realm_id,
        api_base=API_BASE,
        headers={"X-API-Key": "test-secret"},
        request=ledger,
    )


class RealmDeclarationTests(unittest.TestCase):
    def test_exact_success_whitelist_and_single_authenticated_get(self):
        ledger = RequestLedger(Response(success_payload()))
        result = resolve_with(ledger)

        self.assertEqual(
            set(result),
            {
                "schema_version",
                "realm_id",
                "artifact_path",
                "artifact_id",
                "artifact_kind",
                "declaration_contract_id",
                "declaration_contract_version",
                "status",
                "accepted_at",
                "body_sha256",
                "body",
            },
        )
        self.assertNotIn("lifecycle", result)
        self.assertEqual(result["body"], declaration_body())
        self.assertEqual(len(ledger.calls), 1)
        args, kwargs = ledger.calls[0]
        self.assertEqual(args, ("GET", f"{API_BASE}/realm/{REALM_ID}/declaration"))
        self.assertEqual(kwargs["headers"], {"X-API-Key": "test-secret"})
        self.assertEqual(kwargs["timeout"], 30)

    def test_noncanonical_realm_ids_are_local_errors_without_request(self):
        invalid = [
            "",
            f" {REALM_ID}",
            REALM_ID.upper(),
            REALM_ID.replace("-", ""),
            "not-a-uuid",
        ]
        for value in invalid:
            with self.subTest(value=value):
                ledger = RequestLedger(Response(success_payload()))
                with self.assertRaises(RealmDeclarationError) as caught:
                    resolve_with(ledger, value)
                self.assertEqual(caught.exception.code, "invalid_request")
                self.assertEqual(ledger.calls, [])

    def test_every_backend_outcome_maps_to_stable_public_error(self):
        expected = {
            "realm_not_accessible": "realm_not_accessible",
            "not_found": "declaration_not_found",
            "not_current": "declaration_not_current",
            "ambiguous": "declaration_ambiguous",
            "unsupported_declaration_contract": "unsupported_declaration_contract",
            "body_invalid": "declaration_body_invalid",
            "body_too_large": "declaration_body_too_large",
            "dependency_unavailable": "dependency_unavailable",
        }
        for outcome, code in expected.items():
            with self.subTest(outcome=outcome):
                with self.assertRaises(RealmDeclarationError) as caught:
                    resolve_with(RequestLedger(Response({"outcome": outcome})))
                envelope = caught.exception.envelope()
                self.assertEqual(envelope["schema_version"], "1")
                self.assertEqual(envelope["error"]["code"], code)
                self.assertEqual(
                    set(envelope["error"]),
                    {"code", "message", "correlation_id", "retryable"},
                )
                self.assertNotIn("body", envelope)
                self.assertNotIn("body", envelope["error"])
                self.assertNotIn(ARTIFACT_ID, json.dumps(envelope))

    def test_access_http_statuses_are_indistinguishable(self):
        envelopes = []
        for status in (401, 403, 404):
            with self.assertRaises(RealmDeclarationError) as caught:
                resolve_with(RequestLedger(Response({"secret": "hidden"}, status)))
            envelope = caught.exception.envelope()
            envelope["error"]["correlation_id"] = "opaque"
            envelopes.append(envelope)
        self.assertEqual(envelopes[0], envelopes[1])
        self.assertEqual(envelopes[1], envelopes[2])

    def test_transient_dependency_failures_are_retryable_without_raw_detail(self):
        for status in (429, 500, 503):
            with self.subTest(status=status):
                with self.assertRaises(RealmDeclarationError) as caught:
                    resolve_with(
                        RequestLedger(Response({"credential": "leak"}, status))
                    )
                self.assertEqual(caught.exception.code, "dependency_unavailable")
                self.assertTrue(caught.exception.envelope()["error"]["retryable"])
                self.assertNotIn("credential", caught.exception.serialized())

    def test_unknown_or_malformed_backend_shapes_fail_closed(self):
        cases = [
            {},
            {"outcome": "new_unreviewed_outcome"},
            {"outcome": "not_found", "body": "leak"},
            {**success_payload(), "owner_principal": "leak"},
            {
                key: value
                for key, value in success_payload().items()
                if key != "artifact_id"
            },
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(RealmDeclarationError) as caught:
                    resolve_with(RequestLedger(Response(payload)))
                self.assertEqual(caught.exception.code, "dependency_unavailable")

    def test_body_integrity_contract_and_currentness_fail_closed(self):
        duplicate = (
            '{"boundaries":["x"],"boundaries":["y"],"declaration_contract_id":"realm_declaration","declaration_contract_version":1,"purpose":"p","realm_id":"'
            + REALM_ID
            + '","routes":[]}'
        )
        cases = [
            (success_payload(body_sha256="0" * 64), "declaration_body_invalid"),
            (success_payload(body=duplicate), "declaration_body_invalid"),
            (
                success_payload(body=declaration_body(extra="forbidden")),
                "declaration_body_invalid",
            ),
            (
                success_payload(
                    body=declaration_body(declaration_contract_version=2),
                    declaration_contract_version=2,
                ),
                "unsupported_declaration_contract",
            ),
            (success_payload(lifecycle="superseded"), "declaration_not_current"),
            (success_payload(body="x" * 65_537), "declaration_body_too_large"),
        ]
        for payload, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(RealmDeclarationError) as caught:
                    resolve_with(RequestLedger(Response(payload)))
                self.assertEqual(caught.exception.code, code)

    def test_api_tool_uses_tool_error_channel_before_auth_or_backend(self):
        with patch.object(
            api_resources,
            "_onto_headers",
            side_effect=AssertionError("auth must not run"),
        ):
            with self.assertRaises(ToolError) as caught:
                api_resources.about_realm(REALM_ID.upper())
        envelope = json.loads(str(caught.exception))
        self.assertEqual(envelope["error"]["code"], "invalid_request")
        self.assertEqual(set(envelope), {"schema_version", "error"})

    def test_api_tool_maps_missing_credentials_without_leak(self):
        with patch.object(
            api_resources, "_onto_headers", side_effect=RuntimeError("secret-key")
        ):
            with self.assertRaises(ToolError) as caught:
                api_resources.about_realm(REALM_ID)
        self.assertNotIn("secret-key", str(caught.exception))
        self.assertEqual(
            json.loads(str(caught.exception))["error"]["code"], "realm_not_accessible"
        )


if __name__ == "__main__":
    unittest.main()
