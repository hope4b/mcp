from __future__ import annotations

import inspect
import json
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


class CreateExistingLinkRepresentationTests(unittest.TestCase):
    def test_public_signature_has_exact_required_flat_arguments(self) -> None:
        signature = inspect.signature(api_resources.create_existing_link_representation)

        self.assertEqual(
            list(signature.parameters),
            [
                "realm_id",
                "diagram_id",
                "start_representation_id",
                "end_representation_id",
                "onto_nodes_link_type_name",
            ],
        )
        annotations = inspect.get_annotations(
            api_resources.create_existing_link_representation,
            eval_str=True,
        )
        self.assertTrue(all(annotations[name] is str for name in signature.parameters))
        self.assertTrue(
            all(
                parameter.default is inspect.Parameter.empty
                for parameter in signature.parameters.values()
            )
        )
        self.assertIn(
            "backend may create the subject relation when absent",
            api_resources.create_existing_link_representation.__doc__,
        )

    def test_each_blank_argument_fails_before_request(self) -> None:
        valid = {
            "realm_id": "realm-1",
            "diagram_id": "diagram-1",
            "start_representation_id": "start-1",
            "end_representation_id": "end-1",
            "onto_nodes_link_type_name": "context",
        }

        for argument_name in valid:
            for blank in ("", "   "):
                inputs = dict(valid)
                inputs[argument_name] = blank
                with self.subTest(
                    argument_name=argument_name, blank=blank
                ), patch.object(api_resources, "_request_json") as request_json:
                    result = api_resources.create_existing_link_representation(**inputs)

                    request_json.assert_not_called()
                    self.assertEqual(
                        result,
                        f"Parameter '{argument_name}' is required and cannot be empty.",
                    )

    def test_valid_call_posts_once_with_exact_normalized_url_payload_and_output(
        self,
    ) -> None:
        response = {
            "id": "link-representation-1",
            "startRepresentationId": "start-1",
            "endRepresentationId": "end-1",
            "type": "контекст",
            "color": None,
        }
        with patch.object(
            api_resources, "ONTO_API_BASE", "https://onto.example/api/core"
        ), patch.object(
            api_resources,
            "_request_json",
            return_value=response,
        ) as request_json:
            result = api_resources.create_existing_link_representation(
                " realm-1 ",
                " diagram-1 ",
                " start-1 ",
                " end-1 ",
                " контекст ",
            )

        request_json.assert_called_once_with(
            "POST",
            "https://onto.example/api/core/realm/realm-1/diagram/v2/diagram-1/representation/link/existing",
            json_payload={
                "startRepresentationId": "start-1",
                "endRepresentationId": "end-1",
                "ontoNodesLinkTypeName": "контекст",
            },
            timeout=30,
        )
        expected = (
            "Link representation created or resolved on diagram diagram-1.\n"
            "The backend may create the subject relation when it is absent.\n"
            "ID: link-representation-1\n"
            "Start representation ID: start-1\n"
            "End representation ID: end-1\n"
            "Type: контекст\n\n"
            "Response data:\n"
            f"{json.dumps(response, ensure_ascii=False, indent=2)}"
        )
        self.assertEqual(result, expected)
        self.assertTrue(
            result.endswith(json.dumps(response, ensure_ascii=False, indent=2))
        )

    def test_runtime_errors_are_returned_without_success_or_second_request(
        self,
    ) -> None:
        failures = (
            "Onto API request failed with HTTP 500: backend failure",
            "Onto API request timed out.",
            "Onto API returned invalid JSON.",
        )
        for failure in failures:
            with self.subTest(failure=failure), patch.object(
                api_resources,
                "_request_json",
                side_effect=RuntimeError(failure),
            ) as request_json:
                result = api_resources.create_existing_link_representation(
                    "realm-1",
                    "diagram-1",
                    "start-1",
                    "end-1",
                    "context",
                )

                request_json.assert_called_once()
                self.assertEqual(result, failure)
                self.assertNotIn("Link representation created", result)
                self.assertNotIn("Response data:", result)

    def test_source_contains_only_the_canonical_transport_path(self) -> None:
        source = inspect.getsource(api_resources.create_existing_link_representation)

        self.assertIn('"/representation/link/existing"', source)
        self.assertNotIn("representation/link/batch", source)
        self.assertNotIn("create/representation/existing_link", source)
        self.assertNotIn("create_relation(", source)
        self.assertNotIn("relationId", source)
        self.assertNotIn("retry", source.lower())
        self.assertNotIn("preflight", source.lower())


if __name__ == "__main__":
    unittest.main()
