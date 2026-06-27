from __future__ import annotations

import inspect
import sys
import types
import unittest
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


REALM_ID = "000ba00a-00a0-0a00-a000-000a0a0a0aa3"
ARTIFACT_ID = "123e4567-e89b-12d3-a456-426614174001"
SUCCESSOR_ID = "123e4567-e89b-12d3-a456-426614174002"
TARGET_ID = "123e4567-e89b-12d3-a456-426614174003"
ARTIFACT_PATH = "docs/agents/WORKLOG.md"


def _artifact_response(
    artifact_id: str = ARTIFACT_ID,
    *,
    body: str | None = "Full body",
    append_entries: list[dict] | None = None,
) -> dict:
    return {
        "artifact_id": artifact_id,
        "realm_id": REALM_ID,
        "artifact_path": ARTIFACT_PATH,
        "artifact_kind": "worklog",
        "write_mode": "append",
        "scope_kind": "realm",
        "scope_id": REALM_ID,
        "status": "draft",
        "body": body,
        "summary": "Summary",
        "owner_principal": "agent-1",
        "created_by_principal": "agent-1",
        "source_ref": "thread-1",
        "source_context": {"runtime_agent_key": "codex"},
        "review_destination": "docs/capabilities/agent-memory/REVIEW_LOG.md",
        "schema_version": "1",
        "created_at": "2026-06-11T00:00:00Z",
        "updated_at": "2026-06-11T00:00:00Z",
        "accepted_at": None,
        "superseded_at": None,
        "revoked_at": None,
        "supersedes_artifact_id": None,
        "targets": [{"target_kind": "entity", "target_id": TARGET_ID, "role": "primary"}],
        "append_entries": append_entries if append_entries is not None else [],
        "audit_summary": {"last_event": "created", "last_event_at": "2026-06-11T00:00:00Z"},
    }


class MemoryArtifactToolTests(unittest.TestCase):
    def test_create_memory_artifact_draft_calls_only_dedicated_draft_endpoint(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, timeout=30, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            captured["timeout"] = timeout
            captured["kwargs"] = kwargs
            return _artifact_response()

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.create_memory_artifact_draft(
                REALM_ID,
                ARTIFACT_PATH,
                "worklog",
                "append",
                "Body",
                "Summary",
                "thread-1",
                source_context={"runtime_agent_key": "codex"},
                review_destination="docs/capabilities/agent-memory/REVIEW_LOG.md",
                agent_principal="agent-1",
                targets=[{"target_kind": "entity", "target_id": TARGET_ID, "role": "primary"}],
            )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/artifact/draft")
        self.assertNotIn("/entity", str(captured["url"]))
        self.assertNotIn("/chat/", str(captured["url"]))
        self.assertEqual(
            captured["json_payload"],
            {
                "artifact_path": ARTIFACT_PATH,
                "artifact_kind": "worklog",
                "write_mode": "append",
                "body": "Body",
                "summary": "Summary",
                "source_ref": "thread-1",
                "source_context": {"runtime_agent_key": "codex"},
                "review_destination": "docs/capabilities/agent-memory/REVIEW_LOG.md",
                "targets": [{"target_kind": "entity", "target_id": TARGET_ID, "role": "primary"}],
                "agent_principal": "agent-1",
            },
        )
        self.assertIn("Memory artifact draft created", result)
        self.assertIn('"body": "Full body"', result)

    def test_update_memory_artifact_draft_calls_dedicated_update_endpoint_with_supplied_fields_only(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            return _artifact_response(body="Updated body")

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.update_memory_artifact_draft(
                REALM_ID,
                ARTIFACT_ID,
                body="Updated body",
                agent_principal="agent-1",
            )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(
            captured["url"],
            f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/artifact/{ARTIFACT_ID}/draft",
        )
        self.assertEqual(captured["json_payload"], {"body": "Updated body", "agent_principal": "agent-1"})
        self.assertIn("Updated body", result)

    def test_append_memory_artifact_calls_dedicated_append_endpoint(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            return _artifact_response(
                body="Full body",
                append_entries=[
                    {
                        "entry_id": "append-1",
                        "sequence": 1,
                        "body": "Append body",
                        "summary": "Append summary",
                    }
                ],
            )

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.append_memory_artifact(
                REALM_ID,
                ARTIFACT_ID,
                "Append body",
                "thread-2",
                summary="Append summary",
                source_context={"turn": 2},
            )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(
            captured["url"],
            f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/artifact/{ARTIFACT_ID}/append",
        )
        self.assertEqual(
            captured["json_payload"],
            {
                "body": "Append body",
                "source_ref": "thread-2",
                "source_context": {"turn": 2},
                "summary": "Append summary",
            },
        )
        self.assertIn("append_entries: 1", result)
        self.assertIn("Append body", result)

    def test_lifecycle_tools_call_dedicated_backend_authorized_routes_without_payload(self) -> None:
        cases = [
            (api_resources.submit_memory_artifact, "submit", "Memory artifact submitted."),
            (api_resources.accept_memory_artifact, "accept", "Memory artifact accepted."),
            (api_resources.revoke_memory_artifact, "revoke", "Memory artifact revoked."),
        ]

        for fn, route_suffix, expected_text in cases:
            captured: dict[str, object] = {}

            def fake_request(method: str, url: str, *, timeout=30, **kwargs):
                captured["method"] = method
                captured["url"] = url
                captured["kwargs"] = kwargs
                return _artifact_response()

            with self.subTest(route_suffix=route_suffix), patch.object(
                api_resources, "ONTO_API_BASE", "https://onto.example/api/core"
            ), patch.object(api_resources, "_request_json", side_effect=fake_request):
                result = fn(REALM_ID, ARTIFACT_ID)

            self.assertEqual(captured["method"], "POST")
            self.assertEqual(
                captured["url"],
                f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/artifact/{ARTIFACT_ID}/{route_suffix}",
            )
            self.assertNotIn("json_payload", captured["kwargs"])
            self.assertIn(expected_text, result)

    def test_supersede_memory_artifact_uses_create_payload_on_supersede_route(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            return {
                **_artifact_response(SUCCESSOR_ID, body="Replacement body"),
                "artifact_kind": "decision",
                "write_mode": "replace",
                "status": "accepted",
                "supersedes_artifact_id": ARTIFACT_ID,
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.supersede_memory_artifact(
                REALM_ID,
                ARTIFACT_ID,
                ARTIFACT_PATH,
                "decision",
                "replace",
                "Replacement body",
                "Replacement summary",
                "thread-3",
                source_context={"turn": 3},
                targets=[{"target_kind": "realm", "target_id": REALM_ID, "role": "primary"}],
            )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(
            captured["url"],
            f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/artifact/{ARTIFACT_ID}/supersede",
        )
        self.assertEqual(captured["json_payload"]["artifact_kind"], "decision")
        self.assertEqual(captured["json_payload"]["write_mode"], "replace")
        self.assertEqual(captured["json_payload"]["source_context"], {"turn": 3})
        self.assertIn(SUCCESSOR_ID, result)
        self.assertIn('"supersedes_artifact_id": "' + ARTIFACT_ID + '"', result)

    def test_read_tools_use_dedicated_id_and_path_routes(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            calls.append({"method": method, "url": url, "json_payload": json_payload})
            return _artifact_response()

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            by_id = api_resources.get_memory_artifact(REALM_ID, ARTIFACT_ID)
            by_path = api_resources.get_memory_artifact_by_path(REALM_ID, ARTIFACT_PATH)
            own = api_resources.get_own_memory_artifact_draft_by_path(REALM_ID, ARTIFACT_PATH, "agent-1")

        self.assertEqual(calls[0]["method"], "GET")
        self.assertEqual(
            calls[0]["url"],
            f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/artifact/{ARTIFACT_ID}",
        )
        self.assertEqual(calls[1]["method"], "POST")
        self.assertEqual(calls[1]["url"], f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/artifact/path")
        self.assertEqual(calls[1]["json_payload"], {"artifact_path": ARTIFACT_PATH})
        self.assertEqual(calls[2]["method"], "POST")
        self.assertEqual(calls[2]["url"], f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/artifact/own/path")
        self.assertEqual(calls[2]["json_payload"], {"artifact_path": ARTIFACT_PATH, "agent_principal": "agent-1"})
        self.assertIn("Memory artifact loaded", by_id)
        self.assertIn("Accepted memory artifact loaded by path", by_path)
        self.assertIn("Own draft/proposed memory artifact loaded by path", own)

    def test_search_memory_artifacts_is_compact_and_uses_only_supplied_filters(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            return {
                "items": [
                    {
                        **_artifact_response(body="must not leak", append_entries=[{"entry_id": "append-1"}]),
                        "status": "accepted",
                    }
                ],
                "total": 1,
                "first": 0,
                "offset": 50,
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.search_memory_artifacts(
                REALM_ID,
                artifact_kind="worklog",
                write_mode="append",
                artifact_path=ARTIFACT_PATH,
                target_kind="entity",
                target_id=TARGET_ID,
                first=0,
                offset=50,
            )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/artifact/search")
        self.assertEqual(
            captured["json_payload"],
            {
                "first": 0,
                "offset": 50,
                "artifact_kind": "worklog",
                "write_mode": "append",
                "artifact_path": ARTIFACT_PATH,
                "target_kind": "entity",
                "target_id": TARGET_ID,
            },
        )
        self.assertIn("Found 1 memory artifact", result)
        self.assertIn('"body": null', result)
        self.assertIn('"append_entries": null', result)
        self.assertNotIn("must not leak", result)

    def test_search_memory_artifacts_empty_page_does_not_claim_no_results_when_total_exists(self) -> None:
        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            return {
                "items": [],
                "total": 6,
                "first": 20,
                "offset": 100,
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.search_memory_artifacts(REALM_ID, first=20, offset=100)

        self.assertIn("No memory artifacts on the requested page", result)
        self.assertIn("total: 6", result)
        self.assertIn("Use first=0 and offset=<page size>", result)
        self.assertNotIn("No memory artifacts found", result)

    def test_rejects_invalid_inputs_before_backend_call(self) -> None:
        cases = [
            (api_resources.create_memory_artifact_draft, {"realm_id": "", "artifact_path": ARTIFACT_PATH, "artifact_kind": "worklog", "write_mode": "append", "body": "Body", "summary": "Summary", "source_ref": "thread-1", "targets": [{"target_kind": "entity", "target_id": TARGET_ID}]}),
            (api_resources.create_memory_artifact_draft, {"realm_id": REALM_ID, "artifact_path": "", "artifact_kind": "worklog", "write_mode": "append", "body": "Body", "summary": "Summary", "source_ref": "thread-1", "targets": [{"target_kind": "entity", "target_id": TARGET_ID}]}),
            (api_resources.create_memory_artifact_draft, {"realm_id": REALM_ID, "artifact_path": ARTIFACT_PATH, "artifact_kind": "decision", "write_mode": "append", "body": "Body", "summary": "Summary", "source_ref": "thread-1", "targets": [{"target_kind": "entity", "target_id": TARGET_ID}]}),
            (api_resources.create_memory_artifact_draft, {"realm_id": REALM_ID, "artifact_path": ARTIFACT_PATH, "artifact_kind": "worklog", "write_mode": "append", "body": "Body", "summary": "Summary", "source_ref": "thread-1", "targets": []}),
            (api_resources.update_memory_artifact_draft, {"realm_id": REALM_ID, "artifact_id": ARTIFACT_ID}),
            (api_resources.append_memory_artifact, {"realm_id": REALM_ID, "artifact_id": ARTIFACT_ID, "body": "", "source_ref": "thread-1"}),
            (api_resources.submit_memory_artifact, {"realm_id": REALM_ID, "artifact_id": "bad"}),
            (api_resources.get_memory_artifact_by_path, {"realm_id": REALM_ID, "artifact_path": ""}),
            (api_resources.get_own_memory_artifact_draft_by_path, {"realm_id": REALM_ID, "artifact_path": ARTIFACT_PATH, "agent_principal": ""}),
            (api_resources.search_memory_artifacts, {"realm_id": REALM_ID, "target_id": TARGET_ID}),
            (api_resources.search_memory_artifacts, {"realm_id": REALM_ID, "offset": 501}),
            (api_resources.supersede_memory_artifact, {"realm_id": REALM_ID, "artifact_id": ARTIFACT_ID, "artifact_path": ARTIFACT_PATH, "artifact_kind": "worklog", "write_mode": "append", "body": "Body", "summary": "Summary", "source_ref": "thread-1", "targets": [{"target_kind": "realm", "target_id": REALM_ID}]}),
        ]

        for fn, kwargs in cases:
            with self.subTest(fn=fn.__name__, kwargs=kwargs), patch.object(api_resources, "_request_json") as request_json:
                result = fn(**kwargs)

                request_json.assert_not_called()
                self.assertTrue(result)

    def test_no_full_audit_tool_is_exposed(self) -> None:
        self.assertFalse(hasattr(api_resources, "get_memory_artifact_audit"))
        self.assertFalse(hasattr(api_resources, "read_memory_artifact_audit"))

    def test_existing_agent_memory_read_tools_are_not_repurposed(self) -> None:
        self.assertIn("target_kind", inspect.signature(api_resources.search_agent_memory).parameters)
        self.assertIn("record_id", inspect.signature(api_resources.get_agent_memory_record).parameters)
        self.assertNotIn("artifact_path", inspect.signature(api_resources.search_agent_memory).parameters)


if __name__ == "__main__":
    unittest.main()
