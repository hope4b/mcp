from __future__ import annotations

import json
import sys
import types
import unittest
import uuid
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
    fastmcp_exceptions_stub = types.ModuleType("fastmcp.exceptions")

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

    class _ToolError(Exception):
        pass

    def _default_get_http_request():
        raise RuntimeError("no request")

    fastmcp_stub.FastMCP = _FastMCP
    fastmcp_exceptions_stub.ToolError = _ToolError
    fastmcp_server_context_stub.Context = _Context
    fastmcp_server_dependencies_stub.get_http_request = _default_get_http_request
    sys.modules["fastmcp"] = fastmcp_stub
    sys.modules["fastmcp.server"] = fastmcp_server_stub
    sys.modules["fastmcp.server.context"] = fastmcp_server_context_stub
    sys.modules["fastmcp.server.dependencies"] = fastmcp_server_dependencies_stub
    sys.modules["fastmcp.exceptions"] = fastmcp_exceptions_stub

if "fastmcp.exceptions" not in sys.modules:
    try:
        import fastmcp.exceptions  # noqa: F401
    except ImportError:
        fastmcp_exceptions_stub = types.ModuleType("fastmcp.exceptions")

        class _ToolError(Exception):
            pass

        fastmcp_exceptions_stub.ToolError = _ToolError
        sys.modules["fastmcp.exceptions"] = fastmcp_exceptions_stub

from onto_mcp import api_resources


class GetEntityRelatedEntitiesTests(unittest.TestCase):
    SOURCE_ID = "11111111-1111-4111-8111-111111111111"
    SOURCE_REALM_ID = "22222222-2222-4222-8222-222222222222"
    COPY_B_ID = "33333333-3333-4333-8333-333333333333"
    COPY_B_REALM_ID = "44444444-4444-4444-8444-444444444444"
    COPY_C_ID = "55555555-5555-4555-8555-555555555555"
    COPY_C_REALM_ID = "66666666-6666-4666-8666-666666666666"

    def test_get_entity_formats_related_entity_details(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, query_params=None, timeout=30, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["query_params"] = query_params
            captured["timeout"] = timeout
            return {
                "result": {
                    "uuid": "entity-main",
                    "name": "Main Entity",
                    "related_entities": [
                        {
                            "relationName": "owned_by",
                            "direction": "OUT",
                            "incomingRole": "owner",
                            "outgoingRole": "asset",
                            "entity": {
                                "uuid": "entity-user",
                                "name": "User One",
                                "metaEntity": {
                                    "uuid": "meta-user",
                                    "name": "User",
                                },
                            },
                        },
                        {
                            "relationName": "located_in",
                            "direction": "IN",
                            "entity": {
                                "uuid": "entity-folder",
                                "name": "Folder One",
                            },
                        },
                    ],
                }
            }

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.get_entity("realm-1", "entity-main", related_entities=True)

        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["url"], "https://onto.example/api/core/realm/realm-1/entity/entity-main")
        self.assertEqual(captured["query_params"]["relatedEntities"], True)
        self.assertIn("Related entities: 2", result)
        self.assertIn("1. User One (entity-user)", result)
        self.assertIn("relation=owned_by", result)
        self.assertIn("direction=OUT", result)
        self.assertIn("incomingRole=owner", result)
        self.assertIn("outgoingRole=asset", result)
        self.assertIn("template=User (meta-user)", result)
        self.assertIn("2. Folder One (entity-folder)", result)
        self.assertIn("relation=located_in", result)

    def test_get_entity_omitted_and_false_provenance_are_byte_identical(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, *, query_params=None, **kwargs):
            calls.append({"method": method, "url": url, "query_params": dict(query_params)})
            return {"result": {"uuid": "entity-main", "name": "Main Entity"}}

        with patch.object(api_resources, "_request_json", side_effect=fake_request):
            omitted = api_resources.get_entity("realm-1", "entity-main")
            explicit_false = api_resources.get_entity("realm-1", "entity-main", provenance=False)

        self.assertEqual(omitted.encode("utf-8"), explicit_false.encode("utf-8"))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("provenance" not in call["query_params"] for call in calls))

    def test_get_entity_provenance_projects_exact_fields_and_preserves_order(self) -> None:
        calls: list[dict[str, object]] = []
        backend_provenance = {
            "source": {
                "objectId": self.SOURCE_ID,
                "objectName": 'Источник "A"\\root\nline',
                "realmId": self.SOURCE_REALM_ID,
                "realmName": "Пространство\tA",
                "secretExtension": "must-not-leak",
            },
            "directCopies": [
                {
                    "objectId": self.COPY_C_ID,
                    "objectName": "Копия C",
                    "realmId": self.COPY_C_REALM_ID,
                    "realmName": "Realm C",
                    "future": {"private": True},
                },
                {
                    "objectId": self.COPY_B_ID,
                    "objectName": "Копия B",
                    "realmId": self.COPY_B_REALM_ID,
                    "realmName": "Realm B",
                    "future": "ignored",
                },
            ],
            "nextPage": "ignored",
        }

        def fake_request(method: str, url: str, *, query_params=None, **kwargs):
            calls.append({"method": method, "url": url, "query_params": dict(query_params)})
            return {
                "result": {
                    "uuid": "entity-main",
                    "name": "Main Entity",
                    "fields": [{"name": "Code", "value": "A-1"}],
                    "related_diagrams": [{"uuid": "diagram-1"}],
                    "related_entities": [
                        {
                            "relationName": "copied_from",
                            "direction": "OUT",
                            "entity": {"uuid": "entity-related", "name": "Related"},
                        }
                    ],
                    "provenance": backend_provenance,
                    "unknownContainerMember": "ignored",
                },
                "unknownEnvelopeMember": "ignored",
            }

        with patch.object(api_resources, "_request_json", side_effect=fake_request):
            result = api_resources.get_entity(
                "realm-1",
                "entity-main",
                related_diagrams=True,
                related_entities=True,
                provenance=True,
            )

        expected_projection = {
            "source": {
                "objectId": self.SOURCE_ID,
                "objectName": 'Источник "A"\\root\nline',
                "realmId": self.SOURCE_REALM_ID,
                "realmName": "Пространство\tA",
            },
            "directCopies": [
                {
                    "objectId": self.COPY_C_ID,
                    "objectName": "Копия C",
                    "realmId": self.COPY_C_REALM_ID,
                    "realmName": "Realm C",
                },
                {
                    "objectId": self.COPY_B_ID,
                    "objectName": "Копия B",
                    "realmId": self.COPY_B_REALM_ID,
                    "realmName": "Realm B",
                },
            ],
        }
        entity_text, separator, provenance_text = result.partition("\n\nProvenance:\n")
        self.assertEqual(separator, "\n\nProvenance:\n")
        self.assertIn("Entity loaded successfully.", entity_text)
        self.assertIn("Fields: 1", entity_text)
        self.assertIn("Related diagrams: 1", entity_text)
        self.assertIn("Related entities: 1", entity_text)
        self.assertEqual(provenance_text, json.dumps(expected_projection, ensure_ascii=False, indent=2))
        self.assertEqual(json.loads(provenance_text), expected_projection)
        self.assertNotIn("secretExtension", result)
        self.assertNotIn("future", result)
        self.assertNotIn("nextPage", result)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["method"], "GET")
        self.assertEqual(calls[0]["query_params"]["provenance"], True)

    def test_get_entity_provenance_accepts_null_source_and_empty_copies(self) -> None:
        response = {
            "result": {
                "uuid": "entity-main",
                "name": "Main Entity",
                "provenance": {"source": None, "directCopies": [], "unknown": True},
            }
        }
        with patch.object(api_resources, "_request_json", return_value=response):
            result = api_resources.get_entity("realm-1", "entity-main", provenance=True)

        self.assertTrue(result.endswith('\n\nProvenance:\n{\n  "source": null,\n  "directCopies": []\n}'))

    def test_get_entity_provenance_rejects_every_invalid_required_shape_safely(self) -> None:
        valid_record = {
            "objectId": self.SOURCE_ID,
            "objectName": "Source",
            "realmId": self.SOURCE_REALM_ID,
            "realmName": "Realm",
        }
        invalid_provenance_values = [
            None,
            {},
            {"source": None},
            {"source": None, "directCopies": None},
            {"source": None, "directCopies": {}},
            {"source": "misplaced", "directCopies": []},
            {"source": {**valid_record, "objectId": "not-a-uuid"}, "directCopies": []},
            {"source": {**valid_record, "objectId": uuid.UUID(self.SOURCE_ID)}, "directCopies": []},
            {"source": {**valid_record, "realmId": "not-a-uuid"}, "directCopies": []},
            {"source": {key: value for key, value in valid_record.items() if key != "realmName"}, "directCopies": []},
            {"source": {**valid_record, "realmName": None}, "directCopies": []},
            {"source": None, "directCopies": [{**valid_record, "objectName": 7}]},
            {"source": None, "directCopies": [None]},
        ]
        from fastmcp.exceptions import ToolError

        invalid_responses = [None, {}, {"provenance": {"source": None, "directCopies": []}}]
        invalid_responses.extend(
            {"result": {"uuid": "entity-main", "name": "Main", "provenance": value}}
            for value in invalid_provenance_values
        )
        for response in invalid_responses:
            with self.subTest(response=response), patch.object(api_resources, "_request_json", return_value=response):
                with self.assertRaisesRegex(
                    ToolError,
                    r"^Onto API returned an invalid provenance response\.$",
                ):
                    api_resources.get_entity("realm-1", "entity-main", provenance=True)

    def test_get_entity_provenance_retains_transport_failure_text(self) -> None:
        with patch.object(api_resources, "_request_json", side_effect=RuntimeError("existing safe transport error")):
            result = api_resources.get_entity("realm-1", "entity-main", provenance=True)

        self.assertEqual(result, "existing safe transport error")


if __name__ == "__main__":
    unittest.main()
