from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from onto_mcp import api_resources, server

REALM_ID = "11111111-1111-4111-8111-111111111111"
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def _candidate() -> dict:
    return {
        "contract_id": "realm_agent_admission_candidate_v1",
        "contract_version": 1,
        "realm_id": REALM_ID,
        "expected_constitution_artifact_id": "22222222-2222-4222-8222-222222222222",
        "expected_registry_artifact_id": "33333333-3333-4333-8333-333333333333",
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


class _Response:
    status_code = 200

    def json(self) -> dict:
        return {
            "result": "admitted",
            "candidate_fingerprint": HASH_C,
            "predecessor_snapshot": {
                "constitution_artifact_id": "22222222-2222-4222-8222-222222222222",
                "registry_artifact_id": "33333333-3333-4333-8333-333333333333",
            },
            "charter": {
                "artifact_id": "44444444-4444-4444-8444-444444444444",
                "artifact_path": "realm/agents/qa-reviewer/charter",
                "status": "accepted",
                "body_sha256": HASH_A,
            },
            "registry": {
                "artifact_id": "55555555-5555-4555-8555-555555555555",
                "artifact_path": "realm/agents/registry",
                "status": "accepted",
                "body_sha256": HASH_B,
                "predecessor_artifact_id": "33333333-3333-4333-8333-333333333333",
            },
            "resident": {
                "slug": "qa-reviewer",
                "state": "active",
                "validity": "valid_active_resident",
                "boot_allowed": True,
            },
            "writes_performed": True,
            "strict_readback_passed": True,
        }


def _json_rpc_payload(response) -> dict:
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        for line in response.content.splitlines():
            if line.startswith(b"data: "):
                return json.loads(line[6:])
        raise AssertionError("SSE response did not contain a JSON-RPC data event")
    return response.json()


def _post(
    client: TestClient,
    headers: dict[str, str],
    request_id: int,
    name: str,
    arguments: dict,
):
    return client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )


def main() -> None:
    tool_body_calls: list[dict] = []
    backend_calls: list[dict] = []
    original_tool_body = api_resources.admit_realm_agent_result

    def observed_tool_body(*args, **kwargs):
        tool_body_calls.append({"realm_id": args[0]})
        return original_tool_body(*args, **kwargs)

    def observed_backend(method, url, **kwargs):
        backend_calls.append({"method": method, "url": url})
        return _Response()

    base_headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
    }
    app = server._build_http_app()
    with patch.object(
        api_resources, "admit_realm_agent_result", side_effect=observed_tool_body
    ), patch.object(
        api_resources, "_onto_headers", return_value={"X-API-Key": "<redacted>"}
    ), patch.object(
        api_resources, "ONTO_API_BASE", "http://localhost:8080/api/core"
    ), patch.object(
        api_resources.requests, "request", side_effect=observed_backend
    ), TestClient(
        app
    ) as client:
        initialized = client.post(
            "/mcp",
            headers=base_headers,
            json={
                "jsonrpc": "2.0",
                "id": 100,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "http-invalid-params-probe", "version": "1"},
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

        extra_candidate = _candidate()
        extra_candidate["confirm"] = True
        missing_candidate = _candidate()
        missing_candidate.pop("slug")
        null_candidate = _candidate()
        null_candidate["charter_document"] = None
        invalid_arguments = [
            {"realm_id": REALM_ID, "candidate": extra_candidate},
            {"realm_id": REALM_ID, "candidate": missing_candidate},
            {"realm_id": REALM_ID, "candidate": null_candidate},
            {"realm_id": REALM_ID, "candidate": _candidate(), "confirm": True},
        ]
        invalid_responses = [
            _post(client, session_headers, request_id, "admit_realm_agent", arguments)
            for request_id, arguments in enumerate(invalid_arguments, start=1)
        ]
        invalid_payloads = [
            _json_rpc_payload(response) for response in invalid_responses
        ]
        calls_after_invalid = {
            "tool_body": len(tool_body_calls),
            "backend": len(backend_calls),
        }

        other_tool_response = _post(
            client,
            session_headers,
            10,
            "about_onto",
            {"focus": "", "confirm": True},
        )
        other_tool_payload = _json_rpc_payload(other_tool_response)

        valid_response = _post(
            client,
            session_headers,
            11,
            "admit_realm_agent",
            {"realm_id": REALM_ID, "candidate": _candidate()},
        )
        valid_payload = _json_rpc_payload(valid_response)

    print(
        repr(
            {
                "initialize_status": initialized.status_code,
                "invalid_statuses": [
                    response.status_code for response in invalid_responses
                ],
                "invalid_content_types": [
                    response.headers.get("content-type", "")
                    for response in invalid_responses
                ],
                "invalid_payloads": invalid_payloads,
                "calls_after_invalid": calls_after_invalid,
                "other_tool_payload": other_tool_payload,
                "valid_payload": valid_payload,
                "final_tool_body_calls": len(tool_body_calls),
                "final_backend_calls": len(backend_calls),
            }
        )
    )


if __name__ == "__main__":
    main()
