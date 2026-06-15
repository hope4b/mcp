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
TARGET_ID = "123e4567-e89b-12d3-a456-426614174000"
RECORD_ID = "123e4567-e89b-12d3-a456-426614174001"


class AgentMemoryToolTests(unittest.TestCase):
    def test_search_agent_memory_calls_only_dedicated_endpoint_with_required_target_scope(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, timeout=30, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            captured["timeout"] = timeout
            captured["kwargs"] = kwargs
            return {
                "items": [
                    {
                        "id": RECORD_ID,
                        "schema_version": "1",
                        "realm_id": REALM_ID,
                        "memory_kind": "worklog",
                        "title": "Implementation note",
                        "summary": "Search wrapper added.",
                        "body": None,
                        "targets": [{"target_kind": "entity", "target_id": TARGET_ID, "role": "primary"}],
                        "reality": "as_is",
                        "status": "accepted",
                        "author_kind": "agent",
                        "author_id": "agent-1",
                        "source_kind": "session",
                        "source_ref": "thread-1",
                        "source_context": {},
                        "created_at": "2026-06-09T20:00:00Z",
                    }
                ],
                "total": 1,
                "first": 0,
                "offset": 100,
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.search_agent_memory(REALM_ID, "entity", TARGET_ID)

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/search")
        self.assertNotIn("/chat/", str(captured["url"]))
        self.assertEqual(
            captured["json_payload"],
            {
                "target_kind": "entity",
                "target_id": TARGET_ID,
                "first": 0,
                "offset": 100,
            },
        )
        self.assertIn("Found 1 agent memory record", result)
        self.assertIn("status: accepted", result)
        self.assertIn("reality: as_is", result)
        self.assertIn('"body": null', result)

    def test_search_agent_memory_passes_only_supplied_optional_filters(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            captured["json_payload"] = json_payload
            return {"items": [], "total": 0, "first": 25, "offset": 50}

        with patch.object(api_resources, "_request_json", side_effect=fake_request):
            api_resources.search_agent_memory(
                REALM_ID,
                "diagram",
                TARGET_ID,
                memory_kind="decision",
                status="accepted",
                reality="to_be",
                author_id="agent-1",
                source_ref="thread-1",
                branch_id="branch-a",
                query="important",
                first=25,
                offset=50,
            )

        self.assertEqual(
            captured["json_payload"],
            {
                "target_kind": "diagram",
                "target_id": TARGET_ID,
                "first": 25,
                "offset": 50,
                "memory_kind": "decision",
                "status": "accepted",
                "reality": "to_be",
                "author_id": "agent-1",
                "source_ref": "thread-1",
                "branch_id": "branch-a",
                "query": "important",
            },
        )

    def test_search_agent_memory_suppresses_search_body_if_backend_returns_one(self) -> None:
        response = {
            "items": [
                {
                    "id": RECORD_ID,
                    "memory_kind": "worklog",
                    "title": "Title",
                    "summary": "Summary",
                    "body": "must not leak in search",
                    "status": "draft",
                    "reality": "hypothesis",
                }
            ],
            "total": 1,
            "first": 0,
            "offset": 100,
        }

        with patch.object(api_resources, "_request_json", return_value=response):
            result = api_resources.search_agent_memory(REALM_ID, "template", TARGET_ID)

        self.assertIn("status: draft", result)
        self.assertIn("reality: hypothesis", result)
        self.assertIn('"body": null', result)
        self.assertNotIn("must not leak in search", result)

    def test_get_agent_memory_record_reads_full_body_from_dedicated_endpoint(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, timeout=30, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["timeout"] = timeout
            captured["kwargs"] = kwargs
            return {
                "id": RECORD_ID,
                "schema_version": "1",
                "realm_id": REALM_ID,
                "memory_kind": "worklog",
                "title": "Full record",
                "summary": "Full summary",
                "body": "full canonical body",
                "targets": [{"target_kind": "entity", "target_id": TARGET_ID, "role": "primary"}],
                "reality": "as_is",
                "status": "accepted",
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.get_agent_memory_record(REALM_ID, RECORD_ID)

        self.assertEqual(captured["method"], "GET")
        self.assertEqual(
            captured["url"],
            f"https://onto.example/api/core/realm/{REALM_ID}/agent-memory/{RECORD_ID}",
        )
        self.assertNotIn("json_payload", captured["kwargs"])
        self.assertIn("full canonical body", result)
        self.assertIn('"body": "full canonical body"', result)

    def test_rejects_invalid_inputs_before_backend_call(self) -> None:
        cases = [
            (api_resources.search_agent_memory, {"realm_id": "", "target_kind": "entity", "target_id": TARGET_ID}),
            (api_resources.search_agent_memory, {"realm_id": REALM_ID, "target_kind": "", "target_id": TARGET_ID}),
            (api_resources.search_agent_memory, {"realm_id": REALM_ID, "target_kind": "chat", "target_id": TARGET_ID}),
            (api_resources.search_agent_memory, {"realm_id": REALM_ID, "target_kind": "entity", "target_id": ""}),
            (api_resources.search_agent_memory, {"realm_id": REALM_ID, "target_kind": "entity", "target_id": "bad"}),
            (
                api_resources.search_agent_memory,
                {"realm_id": REALM_ID, "target_kind": "entity", "target_id": TARGET_ID, "first": -1},
            ),
            (
                api_resources.search_agent_memory,
                {"realm_id": REALM_ID, "target_kind": "entity", "target_id": TARGET_ID, "offset": 0},
            ),
            (api_resources.get_agent_memory_record, {"realm_id": "", "record_id": RECORD_ID}),
            (api_resources.get_agent_memory_record, {"realm_id": REALM_ID, "record_id": ""}),
            (api_resources.get_agent_memory_record, {"realm_id": REALM_ID, "record_id": "bad"}),
        ]

        for fn, kwargs in cases:
            with self.subTest(fn=fn.__name__, kwargs=kwargs), patch.object(api_resources, "_request_json") as request_json:
                result = fn(**kwargs)

                request_json.assert_not_called()
                self.assertTrue("required" in result or "must" in result)

    def test_search_agent_memory_has_no_include_body_parameter(self) -> None:
        signature = inspect.signature(api_resources.search_agent_memory)

        self.assertNotIn("include_body", signature.parameters)


if __name__ == "__main__":
    unittest.main()
