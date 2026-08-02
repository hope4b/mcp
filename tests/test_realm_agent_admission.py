from __future__ import annotations

import inspect
import threading
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from onto_mcp import api_resources
from onto_mcp.realm_agent_admission import (
    RealmAgentAdmissionCandidateV1,
    RealmAgentAdmissionError,
    admit_realm_agent_result,
)

REALM_ID = "11111111-1111-4111-8111-111111111111"
CONSTITUTION_ID = "22222222-2222-4222-8222-222222222222"
REGISTRY_ID = "33333333-3333-4333-8333-333333333333"
CHARTER_ID = "44444444-4444-4444-8444-444444444444"
SUCCESSOR_REGISTRY_ID = "55555555-5555-4555-8555-555555555555"
CORRELATION_ID = "66666666-6666-4666-8666-666666666666"
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


class _Response:
    def __init__(self, status_code: int, payload) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _candidate_payload() -> dict:
    return {
        "contract_id": "realm_agent_admission_candidate_v1",
        "contract_version": 1,
        "realm_id": REALM_ID,
        "expected_constitution_artifact_id": CONSTITUTION_ID,
        "expected_registry_artifact_id": REGISTRY_ID,
        "slug": "qa-reviewer",
        "charter_body": "# Charter: QA Reviewer\n",
        "charter_body_sha256": HASH_A,
        "charter_document": {
            "document_kind": "resident_charter",
            "slug": "qa-reviewer",
            "charter_path": "realm/agents/qa-reviewer/charter",
            "constitution_path": "realm/agents/constitution",
            "registry_path": "realm/agents/registry",
            "purpose": "Verify changes",
            "territory": "Change verification",
            "mode": "execution",
        },
        "registry_entry": {
            "slug": "qa-reviewer",
            "purpose": "Verify changes",
            "territory": "Change verification",
            "mode": "execution",
            "charter_path": "realm/agents/qa-reviewer/charter",
            "state": "active",
        },
        "proposed_registry_body_sha256": HASH_B,
    }


def _success_payload(result: str = "admitted") -> dict:
    return {
        "result": result,
        "candidate_fingerprint": HASH_C,
        "predecessor_snapshot": {
            "constitution_artifact_id": CONSTITUTION_ID,
            "registry_artifact_id": REGISTRY_ID,
        },
        "charter": {
            "artifact_id": CHARTER_ID,
            "artifact_path": "realm/agents/qa-reviewer/charter",
            "status": "accepted",
            "body_sha256": HASH_A,
        },
        "registry": {
            "artifact_id": SUCCESSOR_REGISTRY_ID,
            "artifact_path": "realm/agents/registry",
            "status": "accepted",
            "body_sha256": HASH_B,
            "predecessor_artifact_id": REGISTRY_ID,
        },
        "resident": {
            "slug": "qa-reviewer",
            "state": "active",
            "validity": "valid_active_resident",
            "boot_allowed": True,
        },
        "writes_performed": result == "admitted",
        "strict_readback_passed": True,
    }


def _backend_error(code: str, status: int, retryable: bool, details: dict) -> dict:
    return {
        "error": {
            "code": code,
            "http_status": status,
            "retryable": retryable,
            "correlation_id": CORRELATION_ID,
            "details": details,
        }
    }


class RealmAgentAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = RealmAgentAdmissionCandidateV1.model_validate(
            _candidate_payload()
        )

    def _call(self, response: _Response):
        return admit_realm_agent_result(
            REALM_ID,
            self.candidate,
            api_base="https://onto.example/api/v2/core",
            headers=lambda: {"X-API-Key": "<redacted>"},
            request=lambda *args, **kwargs: response,
            observability={"correlation_id": CORRELATION_ID},
        )

    def test_public_signature_has_exactly_realm_id_and_candidate(self) -> None:
        signature = inspect.signature(api_resources.admit_realm_agent)
        self.assertEqual(list(signature.parameters), ["realm_id", "candidate"])
        self.assertNotIn("confirm", signature.parameters)
        self.assertNotIn("candidate_fingerprint", signature.parameters)

    def test_candidate_schema_is_recursively_closed_and_required(self) -> None:
        schema = RealmAgentAdmissionCandidateV1.model_json_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["required"],
            list(_candidate_payload()),
        )
        for definition in (
            "RealmAgentCharterDocumentV1",
            "RealmAgentRegistryEntryV1",
        ):
            self.assertFalse(schema["$defs"][definition]["additionalProperties"])

        for mutation in ("extra", "missing", "null"):
            payload = _candidate_payload()
            if mutation == "extra":
                payload["confirm"] = True
            elif mutation == "missing":
                payload.pop("slug")
            else:
                payload["charter_document"] = None
            with self.subTest(mutation=mutation), self.assertRaises(ValidationError):
                RealmAgentAdmissionCandidateV1.model_validate(payload)

    def test_exact_post_path_and_bare_candidate_body(self) -> None:
        captured = {}

        def request(method, url, **kwargs):
            captured.update(method=method, url=url, **kwargs)
            return _Response(200, _success_payload())

        result = admit_realm_agent_result(
            REALM_ID,
            self.candidate,
            api_base="https://onto.example/api/v2/core",
            headers=lambda: {"X-API-Key": "<redacted>"},
            request=request,
            observability={"correlation_id": CORRELATION_ID},
        )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(
            captured["url"],
            f"https://onto.example/api/v2/core/realm/{REALM_ID}/agent-population/admissions",
        )
        self.assertEqual(captured["json"], _candidate_payload())
        self.assertEqual(set(captured["json"]), set(_candidate_payload()))
        self.assertNotIn("candidate", captured["json"])
        self.assertNotIn("confirm", captured["json"])
        self.assertNotIn("candidate_fingerprint", captured["json"])
        self.assertEqual(result.result, "admitted")

    def test_local_realm_mismatch_has_exact_zero_call_error(self) -> None:
        calls = []
        result = admit_realm_agent_result(
            "99999999-9999-4999-8999-999999999999",
            self.candidate,
            api_base="https://onto.example/api/v2/core",
            headers=lambda: calls.append("headers") or {},
            request=lambda *args, **kwargs: calls.append("request"),
            observability={"correlation_id": CORRELATION_ID},
        )

        self.assertEqual(calls, [])
        self.assertEqual(
            result.model_dump(mode="json"),
            {
                "code": "realm_id_mismatch",
                "backend_http_status": None,
                "retryable": False,
                "correlation_id": CORRELATION_ID,
                "request_sent": False,
                "response_received": False,
                "details": {
                    "field": "candidate.realm_id",
                    "violation": "must_equal_tool_realm_id",
                },
            },
        )

    def test_both_exact_success_contracts_are_accepted(self) -> None:
        fresh = self._call(_Response(200, _success_payload("admitted")))
        retry = self._call(_Response(200, _success_payload("already_admitted_exact")))
        self.assertEqual(fresh.result, "admitted")
        self.assertTrue(fresh.writes_performed)
        self.assertEqual(retry.result, "already_admitted_exact")
        self.assertFalse(retry.writes_performed)
        self.assertTrue(fresh.strict_readback_passed)
        self.assertTrue(retry.strict_readback_passed)

    def test_all_closed_backend_errors_map_without_raw_content(self) -> None:
        cases = {
            "malformed_resident_slug": (
                400,
                False,
                {"field": "slug", "rule": "lower_ascii_kebab_v1"},
            ),
            "candidate_schema_invalid": (
                400,
                False,
                {"field": "realm_id", "violation": "must_equal_path_realm_id"},
            ),
            "charter_registry_mismatch": (
                400,
                False,
                {"charter_field": "purpose", "registry_field": "purpose"},
            ),
            "registry_delta_invalid": (
                400,
                False,
                {"violation": "not_exactly_one_append"},
            ),
            "unsupported_agent_admission_policy": (
                409,
                False,
                {
                    "actual_contract": "missing",
                    "actual_version": "missing",
                    "actual_policy": "missing",
                },
            ),
            "stale_governance_snapshot": (
                409,
                True,
                {
                    "expected_constitution_artifact_id": CONSTITUTION_ID,
                    "current_constitution_artifact_id": CHARTER_ID,
                    "expected_registry_artifact_id": REGISTRY_ID,
                    "current_registry_artifact_id": SUCCESSOR_REGISTRY_ID,
                },
            ),
            "resident_slug_already_registered": (409, False, {"slug": "qa-reviewer"}),
            "resident_charter_path_occupied": (
                409,
                False,
                {"charter_path": "realm/agents/qa-reviewer/charter"},
            ),
            "agent_admission_partial_state_conflict": (
                409,
                False,
                {
                    "slug": "qa-reviewer",
                    "charter_path": "realm/agents/qa-reviewer/charter",
                    "charter_present": True,
                    "registry_entry_present": False,
                },
            ),
            "unauthenticated": (401, False, {}),
            "forbidden": (403, False, {}),
            "agent_admission_dependency_unavailable": (
                503,
                True,
                {"dependency": "neo4j", "phase": "admission"},
            ),
            "agent_admission_strict_readback_failed": (
                500,
                False,
                {"phase": "strict_readback"},
            ),
        }
        for code, (status, retryable, details) in cases.items():
            with self.subTest(code=code):
                result = self._call(
                    _Response(status, _backend_error(code, status, retryable, details))
                )
                self.assertIsInstance(result, RealmAgentAdmissionError)
                self.assertEqual(result.code, code)
                self.assertEqual(result.backend_http_status, status)
                self.assertEqual(result.retryable, retryable)
                self.assertTrue(result.request_sent)
                self.assertTrue(result.response_received)
                self.assertNotIn("raw", str(result.model_dump(mode="json")).lower())

    def test_invalid_backend_response_never_retains_raw_body_or_secret(self) -> None:
        result = self._call(
            _Response(
                200,
                {
                    **_success_payload(),
                    "raw_backend_body": "TOP SECRET CHARTER BODY",
                },
            )
        )
        dumped = result.model_dump(mode="json")
        self.assertEqual(dumped["code"], "invalid_backend_response")
        self.assertEqual(dumped["backend_http_status"], 200)
        self.assertEqual(
            dumped["details"],
            {"violation": "closed_contract_mismatch"},
        )
        self.assertNotIn("SECRET", str(dumped))

    def test_transport_exception_is_exact_outcome_unknown(self) -> None:
        def request(*args, **kwargs):
            raise TimeoutError("SECRET backend timeout details")

        result = admit_realm_agent_result(
            REALM_ID,
            self.candidate,
            api_base="https://onto.example/api/v2/core",
            headers=lambda: {"X-API-Key": "<redacted>"},
            request=request,
            observability={"correlation_id": CORRELATION_ID},
        )
        self.assertEqual(
            result.model_dump(mode="json"),
            {
                "code": "outcome_unknown",
                "backend_http_status": None,
                "retryable": True,
                "correlation_id": CORRELATION_ID,
                "request_sent": True,
                "response_received": False,
                "details": {"recovery": "retry_exact_admission"},
            },
        )

    def test_outer_timeout_after_dispatch_is_exact_outcome_unknown(self) -> None:
        request_started = threading.Event()
        release_request = threading.Event()

        def request(*args, **kwargs):
            request_started.set()
            release_request.wait(timeout=1)
            return _Response(200, _success_payload())

        try:
            with patch.object(
                api_resources, "_HTTP_MCP_TOOL_TIMEOUT_SECONDS", 0.05
            ), patch.object(
                api_resources,
                "ONTO_API_BASE",
                "https://onto.example/api/v2/core",
            ), patch.object(
                api_resources,
                "_onto_headers",
                return_value={"X-API-Key": "<redacted>"},
            ), patch.object(
                api_resources.requests, "request", side_effect=request
            ):
                result = api_resources.admit_realm_agent(REALM_ID, self.candidate)
            self.assertTrue(request_started.is_set())
            self.assertEqual(result.code, "outcome_unknown")
            self.assertTrue(result.request_sent)
            self.assertFalse(result.response_received)
            self.assertEqual(result.details.recovery, "retry_exact_admission")
        finally:
            release_request.set()


if __name__ == "__main__":
    unittest.main()
