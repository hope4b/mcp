from __future__ import annotations

import asyncio
from unittest.mock import patch

from fastmcp import Client

from onto_mcp import api_resources


REALM_ID = "000ba00a-00a0-0a00-a000-000a0a0a0aa3"
ARTIFACT_ID = "123e4567-e89b-12d3-a456-426614174001"
TARGETS = [
    {"target_kind": "realm", "target_id": REALM_ID, "role": "primary"},
    {
        "target_kind": "entity",
        "target_id": "123e4567-e89b-12d3-a456-426614174003",
        "role": "context",
    },
]


def _array_schema(targets_schema: dict) -> dict:
    if targets_schema.get("type") == "array":
        return targets_schema
    return next(option for option in targets_schema["anyOf"] if option.get("type") == "array")


def _artifact_response() -> dict:
    return {
        "artifact_id": ARTIFACT_ID,
        "realm_id": REALM_ID,
        "artifact_path": "qa/redacted",
        "artifact_kind": "worklog",
        "write_mode": "append",
        "scope_kind": "realm",
        "scope_id": REALM_ID,
        "status": "draft",
        "body": "<redacted>",
        "summary": "<redacted>",
        "targets": TARGETS,
    }


async def main() -> None:
    evidence: dict[str, object] = {}
    boundary_types: list[str] = []
    backend_shapes: list[dict[str, object]] = []
    original_normalize = api_resources._normalize_memory_artifact_targets

    def capture_normalize(value):
        boundary_types.append(type(value).__name__)
        return original_normalize(value)

    def capture_request(method, url, **kwargs):
        payload = kwargs["json_payload"]
        targets = payload["targets"]
        backend_shapes.append(
            {
                "targets_type": type(targets).__name__,
                "target_item_types": [type(target).__name__ for target in targets],
                "targets_count": len(targets),
            }
        )
        return _artifact_response()

    async with Client(api_resources.mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        schemas = {}
        for tool_name in (
            "create_memory_artifact_draft",
            "update_memory_artifact_draft",
            "supersede_memory_artifact",
        ):
            tool_schema = tools[tool_name].inputSchema
            array_schema = _array_schema(tool_schema["properties"]["targets"])
            schemas[tool_name] = {
                "container_type": array_schema["type"],
                "min_items": array_schema["minItems"],
                "item_schema": array_schema["items"],
                "targets_required": "targets" in tool_schema["required"],
                "supersedes_artifact_id_schema": tool_schema["properties"].get("supersedes_artifact_id"),
                "supersedes_artifact_id_required": "supersedes_artifact_id" in tool_schema["required"],
            }
        evidence["schemas"] = schemas

        with patch.object(
            api_resources,
            "_normalize_memory_artifact_targets",
            side_effect=capture_normalize,
        ), patch.object(api_resources, "_request_json", side_effect=capture_request):
            successful_results = [
                await client.call_tool(
                    "create_memory_artifact_draft",
                    {
                        "realm_id": REALM_ID,
                        "artifact_path": "qa/redacted",
                        "artifact_kind": "worklog",
                        "write_mode": "append",
                        "body": "<redacted>",
                        "summary": "<redacted>",
                        "source_ref": "qa",
                        "targets": TARGETS,
                    },
                ),
                await client.call_tool(
                    "update_memory_artifact_draft",
                    {"realm_id": REALM_ID, "artifact_id": ARTIFACT_ID, "targets": TARGETS},
                ),
                await client.call_tool(
                    "supersede_memory_artifact",
                    {
                        "realm_id": REALM_ID,
                        "artifact_id": ARTIFACT_ID,
                        "artifact_path": "qa/redacted",
                        "artifact_kind": "decision",
                        "write_mode": "replace",
                        "body": "<redacted>",
                        "summary": "<redacted>",
                        "source_ref": "qa",
                        "targets": TARGETS,
                    },
                ),
            ]

        empty_results = [
            await client.call_tool(
                "create_memory_artifact_draft",
                {
                    "realm_id": REALM_ID,
                    "artifact_path": "qa/redacted",
                    "artifact_kind": "worklog",
                    "write_mode": "append",
                    "body": "<redacted>",
                    "summary": "<redacted>",
                    "source_ref": "qa",
                    "targets": [],
                },
                raise_on_error=False,
            ),
            await client.call_tool(
                "update_memory_artifact_draft",
                {"realm_id": REALM_ID, "artifact_id": ARTIFACT_ID, "targets": []},
                raise_on_error=False,
            ),
            await client.call_tool(
                "supersede_memory_artifact",
                {
                    "realm_id": REALM_ID,
                    "artifact_id": ARTIFACT_ID,
                    "artifact_path": "qa/redacted",
                    "artifact_kind": "decision",
                    "write_mode": "replace",
                    "body": "<redacted>",
                    "summary": "<redacted>",
                    "source_ref": "qa",
                    "targets": [],
                },
                raise_on_error=False,
            ),
        ]

    evidence["successful_calls"] = [not result.is_error for result in successful_results]
    evidence["boundary_types"] = boundary_types
    evidence["backend_shapes"] = backend_shapes
    evidence["empty_array_errors"] = [result.is_error for result in empty_results]
    print(repr(evidence))


if __name__ == "__main__":
    asyncio.run(main())
