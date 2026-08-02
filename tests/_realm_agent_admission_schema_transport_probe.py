from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

from fastmcp import Client

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from onto_mcp import api_resources

REALM_ID = "11111111-1111-4111-8111-111111111111"
OTHER_REALM_ID = "99999999-9999-4999-8999-999999999999"
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


async def main() -> None:
    requests: list[dict] = []

    def capture_request(method, url, **kwargs):
        requests.append({"method": method, "url": url, **kwargs})
        return _Response()

    async with Client(api_resources.mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        admission_tool = tools["admit_realm_agent"]

        with patch.object(
            api_resources,
            "_onto_headers",
            return_value={"X-API-Key": "<redacted>"},
        ), patch.object(
            api_resources,
            "ONTO_API_BASE",
            "http://localhost:8080/api/core",
        ), patch.object(
            api_resources.requests, "request", side_effect=capture_request
        ):
            valid = await client.call_tool(
                "admit_realm_agent",
                {"realm_id": REALM_ID, "candidate": _candidate()},
                raise_on_error=False,
            )

            invalid_payloads = []
            extra = _candidate()
            extra["confirm"] = True
            invalid_payloads.append({"realm_id": REALM_ID, "candidate": extra})
            missing = _candidate()
            missing.pop("slug")
            invalid_payloads.append({"realm_id": REALM_ID, "candidate": missing})
            null_nested = _candidate()
            null_nested["charter_document"] = None
            invalid_payloads.append({"realm_id": REALM_ID, "candidate": null_nested})
            invalid_payloads.append(
                {
                    "realm_id": REALM_ID,
                    "candidate": _candidate(),
                    "confirm": True,
                }
            )
            invalid = [
                await client.call_tool(
                    "admit_realm_agent",
                    payload,
                    raise_on_error=False,
                )
                for payload in invalid_payloads
            ]
            mismatch = await client.call_tool(
                "admit_realm_agent",
                {"realm_id": OTHER_REALM_ID, "candidate": _candidate()},
                raise_on_error=False,
            )

    evidence = {
        "tool_count": len(tools),
        "admission_registration_count": list(tools).count("admit_realm_agent"),
        "input_schema": admission_tool.inputSchema,
        "output_schema": getattr(admission_tool, "outputSchema", None),
        "valid_is_error": valid.is_error,
        "invalid_is_error": [result.is_error for result in invalid],
        "mismatch_is_error": mismatch.is_error,
        "requests": requests,
    }
    print(repr(evidence))


if __name__ == "__main__":
    asyncio.run(main())
