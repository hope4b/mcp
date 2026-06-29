from __future__ import annotations

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


class SearchEntitiesByFieldsTests(unittest.TestCase):
    def test_maps_field_filters_to_v2_meta_field_filters_and_renders_values(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(method: str, url: str, *, json_payload=None, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["json_payload"] = json_payload
            return [
                {
                    "meta": {"id": "meta-1", "name": "Vendor"},
                    "entities": [
                        {
                            "id": "entity-1",
                            "name": "Vendor A",
                            "metaEntity": {"id": "meta-1", "name": "Vendor"},
                            "fields": {
                                "field-inn": {
                                    "id": "value-1",
                                    "name": "rso:inn",
                                    "metaFieldId": "field-inn",
                                    "value": "1215156909",
                                    "type": {"class": "java.lang.String"},
                                }
                            },
                        }
                    ],
                }
            ]

        with patch.object(api_resources, "ONTO_API_BASE", "https://onto.example/api/core"), patch.object(
            api_resources, "_request_json", side_effect=fake_request
        ):
            result = api_resources.search_entities_by_fields(
                realm_id="realm-1",
                meta_entity_id="meta-1",
                field_filters=[{"field_id": "field-inn", "value": "1215156909"}],
                first=0,
                offset=100,
            )

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://onto.example/api/core/realm/realm-1/entity/find/v2")
        self.assertEqual(
            captured["json_payload"],
            {
                "name": "",
                "comment": "",
                "metaFieldFilters": [{"uuid": "field-inn", "value": "1215156909"}],
                "pagination": {"first": 0, "offset": 100},
                "metaEntityRequest": {"uuid": "meta-1"},
            },
        )
        self.assertIn("Vendor A", result)
        self.assertIn("rso:inn", result)
        self.assertIn("Value: 1215156909", result)
        self.assertIn("Meta field ID: field-inn", result)

    def test_get_entity_renders_field_values_from_map(self) -> None:
        with patch.object(
            api_resources,
            "_request_json",
            return_value={
                "result": {
                    "id": "entity-1",
                    "name": "Vendor A",
                    "fields": {
                        "field-ogrn": {
                            "id": "value-2",
                            "name": "rso:ogrn",
                            "metaFieldId": "field-ogrn",
                            "value": "1111215003460",
                            "type": {"class": "java.lang.String"},
                        }
                    },
                }
            },
        ):
            result = api_resources.get_entity("realm-1", "entity-1")

        self.assertIn("Fields: 1", result)
        self.assertIn("rso:ogrn", result)
        self.assertIn("Value: 1111215003460", result)
        self.assertIn("Meta field ID: field-ogrn", result)

    def test_rejects_invalid_input_before_backend_call(self) -> None:
        cases = [
            {"realm_id": "", "field_filters": [{"field_id": "field-1", "value": "x"}]},
            {"realm_id": "realm-1", "field_filters": []},
            {"realm_id": "realm-1", "field_filters": [{"field_id": "", "value": "x"}]},
            {"realm_id": "realm-1", "field_filters": [{"field_id": "field-1"}]},
            {"realm_id": "realm-1", "field_filters": [{"field_id": "field-1", "value": ""}]},
            {"realm_id": "realm-1", "field_filters": [{"field_id": "field-1", "value": "x"}], "first": -1},
            {"realm_id": "realm-1", "field_filters": [{"field_id": "field-1", "value": "x"}], "offset": 0},
        ]

        for kwargs in cases:
            with self.subTest(kwargs=kwargs), patch.object(api_resources, "_request_json") as request_json:
                result = api_resources.search_entities_by_fields(**kwargs)

                request_json.assert_not_called()
                self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
