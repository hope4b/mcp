from __future__ import annotations

import sys
import types
import unittest
from typing import Any
from unittest.mock import patch

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _HTTPError(Exception):
        def __init__(self, response: Any = None) -> None:
            super().__init__("stub http error")
            self.response = response

    class _RequestsExceptions:
        HTTPError = _HTTPError

    def _unexpected_request(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("requests.request should not be called in these tests")

    requests_stub.exceptions = _RequestsExceptions()
    requests_stub.request = _unexpected_request
    sys.modules["requests"] = requests_stub

if "fastmcp" not in sys.modules:
    fastmcp_stub = types.ModuleType("fastmcp")
    fastmcp_server_stub = types.ModuleType("fastmcp.server")
    fastmcp_server_context_stub = types.ModuleType("fastmcp.server.context")

    class _FastMCP:
        def __init__(self, name: str) -> None:
            self.name = name

        def tool(self, fn: Any) -> Any:
            return fn

        def resource(self, *args: Any, **kwargs: Any) -> Any:
            def decorator(fn: Any) -> Any:
                return fn

            return decorator

    class _Context:
        pass

    fastmcp_stub.FastMCP = _FastMCP
    fastmcp_server_context_stub.Context = _Context
    sys.modules["fastmcp"] = fastmcp_stub
    sys.modules["fastmcp.server"] = fastmcp_server_stub
    sys.modules["fastmcp.server.context"] = fastmcp_server_context_stub

from onto_mcp import api_resources


class SearchRelationTemplatesTests(unittest.TestCase):
    def test_rejects_when_no_filters(self) -> None:
        with patch.object(api_resources, "_request_json") as request_mock:
            result = api_resources.search_relation_templates(realm_id="R1")

        self.assertEqual(
            result,
            "At least one filter must be provided: 'relation_type_name' or 'meta_ids'.",
        )
        request_mock.assert_not_called()

    def test_rejects_when_meta_ids_length_is_greater_than_two(self) -> None:
        with patch.object(api_resources, "_request_json") as request_mock:
            result = api_resources.search_relation_templates(
                realm_id="R1",
                meta_ids=["T1", "T2", "T3"],
            )

        self.assertEqual(result, "Parameter 'meta_ids' must contain exactly 1 or 2 IDs.")
        request_mock.assert_not_called()

    def test_relation_type_only(self) -> None:
        response: Any = {
            "result": [
                {
                    "id": "REL-1",
                    "type": {"name": "Владеет"},
                    "startMeta": {"id": "T1"},
                    "endMeta": {"id": "T2"},
                }
            ]
        }

        with patch.object(api_resources, "_request_json", return_value=response) as request_mock:
            result = api_resources.search_relation_templates(
                realm_id="R1",
                relation_type_name="Владеет",
            )

        request_mock.assert_called_once_with(
            "POST",
            f"{api_resources.ONTO_API_BASE}/realm/R1/meta/relation/find",
            json_payload={"relationTypeName": "Владеет"},
            timeout=15,
        )
        self.assertIn("Found 1 relation template(s) for relation_type_name='Владеет':", result)
        self.assertIn("1. Владеет", result)
        self.assertIn("Meta IDs: T1, T2", result)

    def test_relation_type_and_single_meta_id(self) -> None:
        response: Any = [{"id": "REL-1", "relationTypeName": "Владеет", "metaIds": ["T1"]}]

        with patch.object(api_resources, "_request_json", return_value=response) as request_mock:
            result = api_resources.search_relation_templates(
                realm_id="R1",
                relation_type_name="Владеет",
                meta_ids=["T1"],
            )

        request_mock.assert_called_once_with(
            "POST",
            f"{api_resources.ONTO_API_BASE}/realm/R1/meta/relation/find",
            json_payload={"relationTypeName": "Владеет", "metaIds": ["T1"]},
            timeout=15,
        )
        self.assertIn(
            "Found 1 relation template(s) for relation_type_name='Владеет', meta_ids=['T1']:",
            result,
        )

    def test_relation_type_and_pair_meta_ids(self) -> None:
        response: Any = [{"id": "REL-1", "type": {"name": "Владеет"}, "metaIds": ["T1", "T2"]}]

        with patch.object(api_resources, "_request_json", return_value=response) as request_mock:
            result = api_resources.search_relation_templates(
                realm_id="R1",
                relation_type_name="Владеет",
                meta_ids=["T1", "T2"],
            )

        request_mock.assert_called_once_with(
            "POST",
            f"{api_resources.ONTO_API_BASE}/realm/R1/meta/relation/find",
            json_payload={"relationTypeName": "Владеет", "metaIds": ["T1", "T2"]},
            timeout=15,
        )
        self.assertIn(
            "Found 1 relation template(s) for relation_type_name='Владеет', meta_ids=['T1', 'T2']:",
            result,
        )

    def test_single_meta_id_only(self) -> None:
        response: Any = [{"id": "REL-1", "relationTypeName": "Владеет", "metaIds": ["T1"]}]

        with patch.object(api_resources, "_request_json", return_value=response) as request_mock:
            result = api_resources.search_relation_templates(
                realm_id="R1",
                meta_ids=["T1"],
            )

        request_mock.assert_called_once_with(
            "POST",
            f"{api_resources.ONTO_API_BASE}/realm/R1/meta/relation/find",
            json_payload={"metaIds": ["T1"]},
            timeout=15,
        )
        self.assertIn("Found 1 relation template(s) for meta_ids=['T1']:", result)

    def test_pair_meta_ids_only(self) -> None:
        response: Any = [{"id": "REL-1", "relationTypeName": "Владеет", "metaIds": ["T1", "T2"]}]

        with patch.object(api_resources, "_request_json", return_value=response) as request_mock:
            result = api_resources.search_relation_templates(
                realm_id="R1",
                meta_ids=["T1", "T2"],
            )

        request_mock.assert_called_once_with(
            "POST",
            f"{api_resources.ONTO_API_BASE}/realm/R1/meta/relation/find",
            json_payload={"metaIds": ["T1", "T2"]},
            timeout=15,
        )
        self.assertIn("Found 1 relation template(s) for meta_ids=['T1', 'T2']:", result)


    def test_uses_top_level_name_from_live_backend_payload(self) -> None:
        response: Any = [
            {
                "id": "REL-1",
                "name": "qa-mcp-rel-26981cc8",
                "startMeta": {"id": "T1"},
                "endMeta": {"id": "T2"},
            }
        ]

        with patch.object(api_resources, "_request_json", return_value=response):
            result = api_resources.search_relation_templates(
                realm_id="R1",
                relation_type_name="qa-mcp-rel-26981cc8",
            )

        self.assertIn("1. qa-mcp-rel-26981cc8", result)
        self.assertNotIn("1. N/A", result)


if __name__ == "__main__":
    unittest.main()
