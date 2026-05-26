from __future__ import annotations

import json
import re
import uuid
from typing import Any
from urllib.parse import quote

import requests
from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.server.dependencies import get_http_request

from .about_content import ABOUT_ONTO_FULL, ABOUT_ONTO_TOPICS
from .session_state_client import (
    SessionStateError,
    get_session_state,
    is_session_state_configured,
    merge_session_state,
)
from .settings import (
    IS_HTTP_TRANSPORT,
    ONTO_API_BASE,
    ONTO_API_KEY,
    ONTO_API_KEY_HEADER,
    ONTO_API_KEY_PASSTHROUGH_HEADER,
)
from .utils import safe_print

mcp = FastMCP(name="Onto MCP Server")


def _onto_headers() -> dict[str, str]:
    api_key = ""

    if IS_HTTP_TRANSPORT:
        try:
            request = get_http_request()
        except RuntimeError:
            request = None

        if request is not None:
            api_key = (request.headers.get(ONTO_API_KEY_PASSTHROUGH_HEADER) or "").strip()

    if not api_key:
        api_key = ONTO_API_KEY

    if not api_key:
        if IS_HTTP_TRANSPORT:
            raise RuntimeError(
                "No Onto API key found. Provide the incoming HTTP header "
                f"'{ONTO_API_KEY_PASSTHROUGH_HEADER}' or configure ONTO_API_KEY on the server."
            )
        raise RuntimeError("ONTO_API_KEY is not configured.")

    return {
        ONTO_API_KEY_HEADER: api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request_json(
    method: str,
    url: str,
    *,
    json_payload: dict[str, Any] | None = None,
    query_params: dict[str, Any] | None = None,
    timeout: int = 30,
) -> Any:
    try:
        response = requests.request(
            method,
            url,
            json=json_payload,
            params=query_params,
            headers=_onto_headers(),
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code
        snippet = exc.response.text[:300] if exc.response is not None and exc.response.text else ""
        raise RuntimeError(f"Onto API error {status}: {snippet}") from exc
    except Exception as exc:
        raise RuntimeError(f"Onto API request failed: {exc}") from exc

    if not response.content:
        return {}

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"Invalid JSON response from Onto API: {response.text[:300]}") from exc


def _get_current_user_data() -> dict[str, Any]:
    data = _request_json("GET", f"{ONTO_API_BASE}/user/v2/current", timeout=10)
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected user payload type: {type(data)}")
    return data


def _get_user_spaces_data() -> list[dict]:
    try:
        data = _get_current_user_data()
    except RuntimeError as exc:
        return [{"error": str(exc)}]

    roles = data.get("userRealmsRoles", [])
    if not isinstance(roles, list):
        return [{"error": "Unexpected Onto API response: userRealmsRoles is not a list."}]

    return [
        {"id": role.get("realmId", "N/A"), "name": role.get("realmName", "N/A")}
        for role in roles
        if isinstance(role, dict)
    ]


def _resolve_realm_id(realm_id: str | None) -> str:
    if realm_id and realm_id.strip():
        return realm_id.strip()

    spaces = _get_user_spaces_data()
    if not spaces or "error" in spaces[0]:
        raise RuntimeError("Failed to resolve a default realm from the configured API key.")
    return str(spaces[0]["id"])


def _format_status_response(action: str, data: Any) -> str:
    if isinstance(data, dict):
        message = data.get("message")
        status = data.get("status")
        lines = [action]
        if status:
            lines.append(f"Status: {status}")
        if message:
            lines.append(f"Message: {message}")
        return "\n".join(lines)
    return action


def _format_template_summary(
    prefix: str,
    template: dict[str, Any],
    fallback_name: str = "",
) -> str:
    template_id = _extract_uuid_from_message(template.get("message"))
    if template_id == "N/A":
        template_id = template.get("uuid") or template.get("id") or "N/A"
    template_name = template.get("name") or fallback_name or "N/A"
    result = [
        prefix,
        f"ID: {template_id}",
        f"Name: {template_name}",
    ]
    comment = template.get("comment")
    if comment:
        result.append(f"Comment: {comment}")
    return "\n".join(result)


def _extract_uuid_from_message(message: Any) -> str:
    if not isinstance(message, str):
        return "N/A"
    match = re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        message,
    )
    if not match:
        return "N/A"
    return match.group(0)


def _build_entity_payload(
    *,
    name: str,
    comment: str = "",
    entity_id: str = "",
    meta_entity_id: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name.strip(),
        "comment": comment or "",
    }
    if entity_id.strip():
        payload["id"] = entity_id.strip()
    if meta_entity_id.strip():
        payload["metaEntityId"] = meta_entity_id.strip()
    return payload


def _format_entity_summary(prefix: str, entity: dict[str, Any], fallback_name: str = "") -> str:
    entity_id = _extract_uuid_from_message(entity.get("message"))
    if entity_id == "N/A":
        entity_id = entity.get("uuid") or entity.get("id") or "N/A"
    entity_name = entity.get("name") or fallback_name or "N/A"
    result = [
        prefix,
        f"ID: {entity_id}",
        f"Name: {entity_name}",
    ]
    comment = entity.get("comment")
    if comment:
        result.append(f"Comment: {comment}")

    meta_entity = entity.get("metaEntity") or {}
    if isinstance(meta_entity, dict) and (meta_entity.get("name") or meta_entity.get("id") or meta_entity.get("uuid")):
        result.append(
            "Template: "
            f"{meta_entity.get('name', 'N/A')} "
            f"({meta_entity.get('id', meta_entity.get('uuid', 'N/A'))})"
        )
    return "\n".join(result)


def _unwrap_search_response(data: Any) -> Any:
    if isinstance(data, dict) and "result" in data:
        return data["result"]
    return data


def _extract_entities_from_search_response(data: Any) -> list[dict[str, Any]]:
    data = _unwrap_search_response(data)
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        data = data["items"]

    if not isinstance(data, list):
        raise RuntimeError(f"Expected list response, got: {type(data)}")

    entities: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("entities"), list):
            entities.extend([entity for entity in item["entities"] if isinstance(entity, dict)])
        elif isinstance(item, dict):
            entities.append(item)
    return entities


def _extract_entity_search_page_metadata(data: Any) -> dict[str, Any]:
    data = _unwrap_search_response(data)
    if not isinstance(data, dict):
        return {}
    if not isinstance(data.get("items"), list):
        return {}
    return {
        key: data[key]
        for key in ("total", "first", "offset")
        if isinstance(data.get(key), int)
    }


def _format_entities_summary(
    prefix: str,
    realm_id: str,
    entities: list[dict[str, Any]],
    page_metadata: dict[str, Any] | None = None,
) -> str:
    if not entities:
        if page_metadata:
            total = page_metadata.get("total")
            return f"No entities found in realm {realm_id}. Total: {total if total is not None else 0}."
        return f"No entities found in realm {realm_id}."

    header = f"{prefix} {len(entities)} entities in realm {realm_id}:"
    if page_metadata:
        metadata_parts = [
            f"{key}: {page_metadata[key]}"
            for key in ("total", "first", "offset")
            if key in page_metadata
        ]
        if metadata_parts:
            header = f"{header[:-1]} ({', '.join(metadata_parts)}):"

    result_lines = [header, ""]
    for index, entity in enumerate(entities[:50], 1):
        result_lines.append(f"{index}. {entity.get('name', 'N/A')}")
        result_lines.append(f"   UUID: {entity.get('id', entity.get('uuid', 'N/A'))}")
        meta_entity = entity.get("metaEntity") or {}
        if isinstance(meta_entity, dict) and meta_entity.get("name"):
            result_lines.append(
                f"   Template: {meta_entity.get('name')} ({meta_entity.get('id', meta_entity.get('uuid', 'N/A'))})"
            )
        comment = entity.get("comment")
        if comment:
            display_comment = comment[:100] + "..." if len(comment) > 100 else comment
            result_lines.append(f"   Comment: {display_comment}")
        result_lines.append("")

    if len(entities) > 50:
        result_lines.append(f"... and {len(entities) - 50} more entities.")
    return "\n".join(result_lines)


def _unwrap_result_dict(data: Any) -> Any:
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        return data["result"]
    return data


def _build_entity_relation_payload(
    *,
    start_entity_id: str,
    end_entity_id: str,
    relation_type_name: str,
    start_role: str = "",
    end_role: str = "",
    additional_properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "startRelatedEntity": {"id": start_entity_id.strip(), "role": start_role or ""},
        "endRelatedEntity": {"id": end_entity_id.strip(), "role": end_role or ""},
        "type": relation_type_name.strip(),
    }
    if additional_properties:
        payload["additionalProperties"] = additional_properties
    return payload


def _build_meta_relation_payload(
    *,
    start_meta_id: str,
    end_meta_id: str,
    relation_type_name: str,
    start_min: int = 0,
    start_max: int = 1,
    end_min: int = 0,
    end_max: int = 1,
    equal: bool = False,
) -> dict[str, Any]:
    return {
        "startMeta": {"id": start_meta_id.strip(), "min": start_min, "max": start_max},
        "endMeta": {"id": end_meta_id.strip(), "min": end_min, "max": end_max},
        "type": {"name": relation_type_name.strip(), "equal": equal},
    }


def _normalize_relation_template_meta_ids(meta_ids: list[str] | None) -> list[str]:
    if meta_ids is None:
        return []
    if not isinstance(meta_ids, list):
        raise RuntimeError("Parameter 'meta_ids' must be a list of 1 or 2 non-empty IDs.")

    normalized_ids = [str(meta_id).strip() for meta_id in meta_ids if str(meta_id).strip()]
    if len(normalized_ids) != len(meta_ids):
        raise RuntimeError("Parameter 'meta_ids' must contain only non-empty IDs.")
    if len(normalized_ids) not in {1, 2}:
        raise RuntimeError("Parameter 'meta_ids' must contain exactly 1 or 2 IDs.")
    return normalized_ids


def _extract_relation_template_name(relation_template: dict[str, Any]) -> str:
    relation_type = relation_template.get("type")
    if isinstance(relation_type, dict) and relation_type.get("name"):
        return str(relation_type["name"])
    if isinstance(relation_type, str) and relation_type.strip():
        return relation_type.strip()

    relation_name = relation_template.get("name")
    if isinstance(relation_name, str) and relation_name.strip():
        return relation_name.strip()

    relation_type_name = relation_template.get("relationTypeName")
    if isinstance(relation_type_name, str) and relation_type_name.strip():
        return relation_type_name.strip()

    return "N/A"


def _extract_relation_template_meta_participants(relation_template: dict[str, Any]) -> list[str]:
    participants: list[str] = []

    def add_participant(value: Any) -> None:
        if not value:
            return
        participant_id = str(value).strip()
        if participant_id and participant_id not in participants:
            participants.append(participant_id)

    for key in ("metaIds", "meta_ids"):
        raw_ids = relation_template.get(key)
        if isinstance(raw_ids, list):
            for raw_id in raw_ids:
                add_participant(raw_id)

    for key in ("startMeta", "endMeta", "start_meta", "end_meta"):
        raw_meta = relation_template.get(key)
        if isinstance(raw_meta, dict):
            add_participant(raw_meta.get("id") or raw_meta.get("uuid"))

    for key in ("startMetaId", "endMetaId", "start_meta_id", "end_meta_id"):
        add_participant(relation_template.get(key))

    return participants


def _save_template_impl(realm_id: str, name: str, comment: str = "", template_id: str = "") -> str:
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not name or not name.strip():
        return "Parameter 'name' is required and cannot be empty."

    payload = {
        "id": template_id.strip() or str(uuid.uuid4()),
        "name": name.strip(),
        "comment": comment or "",
    }
    try:
        saved = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{realm_id}/meta",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    if not isinstance(saved, dict):
        return f"Template saved, but response format is unexpected: {type(saved)}"

    action = "Template updated successfully." if template_id.strip() else "Template created successfully."
    return _format_template_summary(
        action,
        saved,
        fallback_name=name.strip(),
    )


def _save_entities_batch_impl(realm_id: str, entities: list[dict]) -> str:
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not entities or not isinstance(entities, list):
        return "Parameter 'entities' must be a non-empty list."

    for index, entity in enumerate(entities, 1):
        if not isinstance(entity, dict):
            return f"Entity #{index} is not a dict."
        if not entity.get("name") or not str(entity["name"]).strip():
            return f"Entity #{index} is missing required 'name'."
        if entity.get("meta_entity_id") is not None and entity.get("metaEntityId") is not None:
            snake = str(entity.get("meta_entity_id", "")).strip()
            camel = str(entity.get("metaEntityId", "")).strip()
            if snake != camel:
                return (
                    f"Entity #{index} provides both 'meta_entity_id' and 'metaEntityId' "
                    "with different values."
                )

    payload_entities = [
        _build_entity_payload(
            name=str(entity["name"]).strip(),
            comment=str(entity.get("comment", "")),
            entity_id="" if entity.get("id") is None else str(entity.get("id", "")).strip(),
            meta_entity_id=(
                ""
                if entity.get("meta_entity_id") is None and entity.get("metaEntityId") is None
                else str(
                    entity.get("meta_entity_id")
                    if entity.get("meta_entity_id") is not None
                    else entity.get("metaEntityId", "")
                ).strip()
            ),
        )
        for entity in entities
    ]

    try:
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{realm_id}/entity/batch",
            json_payload={"entities": payload_entities},
            timeout=60,
        )
    except RuntimeError as exc:
        return str(exc)

    saved = data.get("createdEntities", []) if isinstance(data, dict) else []
    result_lines = [f"Successfully saved {len(saved)} entities in realm {realm_id}.", ""]
    for index, entity in enumerate(saved, 1):
        if not isinstance(entity, dict):
            result_lines.append(f"{index}. {entity}")
            result_lines.append("")
            continue
        result_lines.append(f"{index}. {entity.get('name', 'N/A')}")
        result_lines.append(f"   UUID: {entity.get('uuid', entity.get('id', 'N/A'))}")
        comment = entity.get("comment")
        if comment:
            result_lines.append(f"   Comment: {comment}")
        meta = entity.get("metaEntity") or {}
        if isinstance(meta, dict) and meta.get("name"):
            result_lines.append(
                f"   Template: {meta.get('name')} ({meta.get('uuid', meta.get('id', 'N/A'))})"
            )
        result_lines.append("")
    return "\n".join(result_lines)


def _build_entity_fields_payload(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_fields: list[dict[str, Any]] = []
    for index, field in enumerate(fields, 1):
        if not isinstance(field, dict):
            raise RuntimeError(f"Field #{index} is not a dict.")
        if not field.get("name") or not str(field["name"]).strip():
            raise RuntimeError(f"Field #{index} is missing required 'name'.")
        field_type_name = "" if field.get("fieldTypeName") is None else str(field.get("fieldTypeName", "")).strip()
        if field_type_name and field_type_name != "T_STRING":
            raise RuntimeError(
                f"Field #{index} has unsupported 'fieldTypeName'. "
                "The confirmed Onto contract currently accepts only 'T_STRING' for entity fields."
            )

        payload_field: dict[str, Any] = {
            "id": str(field.get("id", "")).strip() or str(uuid.uuid4()),
            "name": str(field["name"]).strip(),
            "value": "" if field.get("value") is None else str(field.get("value", "")),
            "comment": "" if field.get("comment") is None else str(field.get("comment", "")),
            "fieldTypeName": "T_STRING",
        }
        if field.get("metaFieldUuid"):
            payload_field["metaFieldUuid"] = str(field["metaFieldUuid"]).strip()
        normalized_fields.append(payload_field)
    return normalized_fields


def _build_template_fields_payload(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_fields: list[dict[str, Any]] = []
    for index, field in enumerate(fields, 1):
        if not isinstance(field, dict):
            raise RuntimeError(f"Field #{index} is not a dict.")
        if not field.get("name") or not str(field["name"]).strip():
            raise RuntimeError(f"Field #{index} is missing required 'name'.")
        field_type_name = "" if field.get("fieldTypeName") is None else str(field.get("fieldTypeName", "")).strip()
        if field_type_name and field_type_name != "T_STRING":
            raise RuntimeError(
                f"Field #{index} has unsupported 'fieldTypeName'. "
                "The confirmed Onto contract currently accepts only 'T_STRING' for template fields."
            )

        payload_field: dict[str, Any] = {
            "uuid": str(field.get("uuid", "")).strip() or str(uuid.uuid4()),
            "name": str(field["name"]).strip(),
            "fieldTypeName": "T_STRING",
            "comment": "" if field.get("comment") is None else str(field.get("comment", "")),
            "usableAsReference": bool(field.get("usableAsReference", False)),
        }
        normalized_fields.append(payload_field)
    return normalized_fields


def _normalize_non_empty_ids(values: list[str], label: str) -> list[str]:
    if not values or not isinstance(values, list):
        raise RuntimeError(f"Parameter '{label}' must be a non-empty list.")

    normalized: list[str] = []
    for index, value in enumerate(values, 1):
        text = "" if value is None else str(value).strip()
        if not text:
            raise RuntimeError(f"Parameter '{label}' contains an empty item at index {index}.")
        normalized.append(text)
    return normalized


_RELATION_SEARCH_PREDICATE_KEYS = {
    "relation_type_names": "relationTypeNames",
    "related_meta_ids": "relatedMetaIds",
    "related_entity_ids": "relatedEntityIds",
}

_RELATION_SEARCH_FORBIDDEN_KEYS = {"direction", "operator", "and", "or", "predicates"}
_RELATION_SEARCH_MAX_SEARCHED_META_IDS = 20
_RELATION_SEARCH_MAX_PREDICATES = 10
_RELATION_SEARCH_MAX_SELECTOR_VALUES = 20
_RELATION_SEARCH_MAX_OFFSET = 500
_RELATION_SEARCH_SORT_FIELDS = {"name", "uuid"}
_RELATION_SEARCH_SORT_DIRECTIONS = {"asc", "desc"}


def _normalize_relation_search_predicates(predicates: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if predicates is None:
        return []
    if not isinstance(predicates, list):
        raise RuntimeError("Parameter 'predicates' must be a flat array.")
    if len(predicates) > _RELATION_SEARCH_MAX_PREDICATES:
        raise RuntimeError(f"Parameter 'predicates' must contain at most {_RELATION_SEARCH_MAX_PREDICATES} items.")

    normalized_predicates: list[dict[str, Any]] = []
    for index, predicate in enumerate(predicates, 1):
        if not isinstance(predicate, dict):
            raise RuntimeError(f"Predicate #{index} must be an object.")

        unknown_keys = set(predicate) - set(_RELATION_SEARCH_PREDICATE_KEYS)
        forbidden_keys = unknown_keys & _RELATION_SEARCH_FORBIDDEN_KEYS
        if forbidden_keys:
            names = ", ".join(sorted(forbidden_keys))
            raise RuntimeError(f"Predicate #{index} contains unsupported structural key(s): {names}.")
        if unknown_keys:
            names = ", ".join(sorted(unknown_keys))
            raise RuntimeError(f"Predicate #{index} contains unsupported field(s): {names}.")

        normalized_predicate: dict[str, Any] = {}
        for public_key, backend_key in _RELATION_SEARCH_PREDICATE_KEYS.items():
            if public_key not in predicate:
                continue
            value = predicate[public_key]
            if not isinstance(value, list):
                raise RuntimeError(f"Predicate #{index} field '{public_key}' must be a list of non-empty strings.")
            normalized_values = [str(item).strip() for item in value if str(item).strip()]
            if len(normalized_values) != len(value):
                raise RuntimeError(f"Predicate #{index} field '{public_key}' must contain only non-empty values.")
            if not normalized_values:
                raise RuntimeError(f"Predicate #{index} field '{public_key}' must contain at least one non-empty value.")
            if len(normalized_values) > _RELATION_SEARCH_MAX_SELECTOR_VALUES:
                raise RuntimeError(
                    f"Predicate #{index} field '{public_key}' must contain at most "
                    f"{_RELATION_SEARCH_MAX_SELECTOR_VALUES} values."
                )
            normalized_predicate[backend_key] = normalized_values

        if not normalized_predicate:
            raise RuntimeError(f"Predicate #{index} must contain at least one supported selector field.")

        normalized_predicates.append(normalized_predicate)

    return normalized_predicates


def _normalize_relation_search_sort(sort: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    if sort is None:
        return []
    if not isinstance(sort, list):
        raise RuntimeError("Parameter 'sort' must be a list.")

    normalized_sort: list[dict[str, str]] = []
    for index, sort_item in enumerate(sort, 1):
        if not isinstance(sort_item, dict):
            raise RuntimeError(f"Sort item #{index} must be an object.")

        unknown_keys = set(sort_item) - {"field", "direction"}
        if unknown_keys:
            names = ", ".join(sorted(unknown_keys))
            raise RuntimeError(f"Sort item #{index} contains unsupported field(s): {names}.")

        field = str(sort_item.get("field", "")).strip()
        direction = str(sort_item.get("direction", "asc")).strip().lower()
        if field not in _RELATION_SEARCH_SORT_FIELDS:
            raise RuntimeError(f"Sort item #{index} has unsupported field '{field}'.")
        if direction not in _RELATION_SEARCH_SORT_DIRECTIONS:
            raise RuntimeError(f"Sort item #{index} has unsupported direction '{direction}'.")

        normalized_sort.append({"field": field, "direction": direction})

    return normalized_sort


def _format_template_fields_summary(template_id: str, fields_data: Any) -> str:
    if not isinstance(fields_data, list):
        return f"Saved template fields for template {template_id}."

    lines = [f"Saved {len(fields_data)} field(s) for template {template_id}.", ""]
    for index, field in enumerate(fields_data, 1):
        if not isinstance(field, dict):
            lines.append(f"{index}. {field}")
            lines.append("")
            continue
        lines.append(f"{index}. {field.get('name', 'N/A')}")
        lines.append(f"   ID: {field.get('id', field.get('uuid', 'N/A'))}")
        lines.append(f"   Type: {field.get('type', field.get('fieldTypeName', 'N/A'))}")
        comment = field.get("comment")
        if comment:
            lines.append(f"   Comment: {comment}")
        abilities = field.get("abilities")
        if isinstance(abilities, list):
            lines.append(f"   Abilities: {', '.join(str(item) for item in abilities) if abilities else 'none'}")
        lines.append("")
    return "\n".join(lines)


def _format_diagram_info_summary(prefix: str, diagram: Any) -> str:
    if not isinstance(diagram, dict):
        return prefix

    lines = [
        prefix,
        f"ID: {diagram.get('id', 'N/A')}",
        f"Name: {diagram.get('name', 'N/A')}",
    ]
    summary = diagram.get("summary")
    if summary:
        lines.append(f"Summary: {summary}")
    creation_date = diagram.get("creationDate")
    if creation_date:
        lines.append(f"Creation date: {creation_date}")
    if "stared" in diagram:
        lines.append(f"Starred: {diagram.get('stared')}")
    tags = diagram.get("tags")
    if isinstance(tags, list):
        lines.append(f"Tags: {len(tags)}")
    return "\n".join(lines)


def _format_get_diagram_summary(diagram_id: str, data: Any) -> str:
    if not isinstance(data, dict):
        return f"Diagram loaded successfully.\nID: {diagram_id}"

    diagram = data.get("diagram") if isinstance(data.get("diagram"), dict) else {}
    lines = [
        "Diagram loaded successfully.",
        f"ID: {diagram.get('id', diagram_id)}",
        f"Name: {diagram.get('name', 'N/A')}",
    ]
    summary = diagram.get("summary")
    if summary:
        lines.append(f"Summary: {summary}")
    creation_date = diagram.get("creationDate")
    if creation_date:
        lines.append(f"Creation date: {creation_date}")
    representations = data.get("representations")
    if isinstance(representations, list):
        lines.append(f"Representations: {len(representations)}")
    links = data.get("links")
    if isinstance(links, list):
        lines.append(f"Links: {len(links)}")
    point_of_view = data.get("pointOfView")
    if isinstance(point_of_view, dict):
        lines.append("Point of view: present")
    return "\n".join(lines)


def _normalize_positive_int(value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError(f"Parameter '{label}' must be an integer.")
    if value <= 0:
        raise RuntimeError(f"Parameter '{label}' must be positive.")
    return value


def _extract_id(value: dict[str, Any]) -> str:
    for key in ("id", "uuid", "tagId"):
        raw_value = value.get(key)
        if raw_value:
            return str(raw_value)
    return "N/A"


def _format_page_metadata(data: dict[str, Any]) -> str:
    return (
        f"totalResults: {data.get('totalResults', 'N/A')}, "
        f"totalPages: {data.get('totalPages', 'N/A')}, "
        f"page: {data.get('page', 'N/A')}, "
        f"size: {data.get('size', 'N/A')}"
    )


def _format_diagram_page(data: Any, realm_id: str) -> str:
    if not isinstance(data, dict):
        return f"Unexpected diagram page response format: {type(data)}"

    results = data.get("results")
    if not isinstance(results, list):
        return f"Unexpected diagram page results format: {type(results)}"

    if not results:
        return f"No diagrams found in realm {realm_id}. {_format_page_metadata(data)}."

    lines = [f"Found {len(results)} diagram(s) in realm {realm_id}.", _format_page_metadata(data), ""]
    for index, diagram in enumerate(results, 1):
        if not isinstance(diagram, dict):
            continue
        lines.append(f"{index}. {diagram.get('name', 'N/A')}")
        lines.append(f"   ID: {_extract_id(diagram)}")
        lines.append(f"   Summary: {diagram.get('summary', '')}")
        lines.append(f"   Creation date: {diagram.get('creationDate', 'N/A')}")
        lines.append(f"   Starred: {diagram.get('stared', 'N/A')}")
        tags = diagram.get("tags") if isinstance(diagram.get("tags"), list) else []
        lines.append(f"   Tags: {len(tags)}")
        for tag in tags:
            if isinstance(tag, dict):
                lines.append(f"   - {_extract_id(tag)}: {tag.get('name', tag.get('tagName', 'N/A'))}")
        lines.append("")

    lines.append("Page data:")
    lines.append(json.dumps(data, ensure_ascii=False, indent=2))
    return "\n".join(lines)


def _format_context_tag_page(data: Any, realm_id: str) -> str:
    if not isinstance(data, dict):
        return f"Unexpected context tag page response format: {type(data)}"

    results = data.get("results")
    if not isinstance(results, list):
        return f"Unexpected context tag page results format: {type(results)}"

    if not results:
        return f"No context tags found in realm {realm_id}. {_format_page_metadata(data)}."

    lines = [f"Found {len(results)} context tag(s) in realm {realm_id}.", _format_page_metadata(data), ""]
    for index, tag in enumerate(results, 1):
        if not isinstance(tag, dict):
            continue
        lines.append(f"{index}. {tag.get('name', tag.get('tagName', 'N/A'))}")
        lines.append(f"   ID: {_extract_id(tag)}")
        lines.append(f"   Color: {tag.get('color', 'N/A')}")
        lines.append(f"   Usage: {tag.get('usage', 'N/A')}")
        lines.append("")

    lines.append("Page data:")
    lines.append(json.dumps(data, ensure_ascii=False, indent=2))
    return "\n".join(lines)


def _extract_diagram_payload(data: Any) -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("diagram"), dict):
        return data["diagram"]
    if isinstance(data, dict):
        return data
    raise RuntimeError(f"Unexpected diagram response format: {type(data)}")


def _extract_diagram_tag_ids(diagram: dict[str, Any]) -> list[str]:
    tags = diagram.get("tags") if isinstance(diagram.get("tags"), list) else []
    tag_ids: list[str] = []
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        tag_id = _extract_id(tag)
        if tag_id != "N/A" and tag_id not in tag_ids:
            tag_ids.append(tag_id)
    return tag_ids


def _build_diagram_update_payload(diagram: dict[str, Any], tag_ids: list[str]) -> dict[str, Any]:
    name = str(diagram.get("name", "")).strip()
    if not name:
        raise RuntimeError("Cannot update diagram tags because existing diagram name is missing.")
    return {
        "name": name,
        "comment": "" if diagram.get("summary") is None else str(diagram.get("summary")),
        "tags": tag_ids,
    }


def _load_diagram_for_tag_update(realm_id: str, diagram_id: str) -> dict[str, Any]:
    data = _request_json(
        "GET",
        f"{ONTO_API_BASE}/realm/{realm_id}/diagram/v2/{diagram_id}",
        timeout=30,
    )
    return _extract_diagram_payload(data)


def _extract_node_chat_messages(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and "result" in data:
        data = data["result"]
    if not isinstance(data, list):
        raise RuntimeError(f"Expected node chat message list response, got: {type(data)}")
    return [message for message in data if isinstance(message, dict)]


def _format_node_chat_messages(realm_id: str, node_id: str, messages: list[dict[str, Any]]) -> str:
    if not messages:
        return f"No node chat messages found for node {node_id} in realm {realm_id}."

    lines = [f"Found {len(messages)} object/node chat message(s) for node {node_id} in realm {realm_id}:", ""]
    for index, message in enumerate(messages, 1):
        user = message.get("user") if isinstance(message.get("user"), dict) else {}
        lines.append(f"{index}. {message.get('text', '')}")
        lines.append(f"   ID: {message.get('id', 'N/A')}")
        lines.append(f"   timeStamp: {message.get('timeStamp', 'N/A')}")
        lines.append(f"   my: {message.get('my', 'N/A')}")
        lines.append(f"   user.userId: {user.get('userId', 'N/A')}")
        lines.append(f"   user.userName: {user.get('userName', 'N/A')}")
        lines.append(f"   user.comment: {user.get('comment', 'N/A')}")
        lines.append("")

    lines.append("Message data:")
    lines.append(json.dumps(messages, ensure_ascii=False, indent=2))
    return "\n".join(lines)


@mcp.tool
def about_onto(focus: str = "") -> str:
    """Return a domain description of Onto in the style of the canonical about text."""
    normalized_focus = (focus or "").strip().lower()
    if not normalized_focus:
        return ABOUT_ONTO_FULL

    if normalized_focus in ABOUT_ONTO_TOPICS:
        return ABOUT_ONTO_TOPICS[normalized_focus]

    available = ", ".join(sorted(ABOUT_ONTO_TOPICS.keys()))
    return (
        f"Unknown focus '{focus}'. "
        f"Available focus values: {available}. "
        "If focus is omitted, the tool returns the full Onto overview."
    )


@mcp.tool
def saveOntoAIThreadID(thread_external_id: str, ctx: Context) -> dict[str, Any]:
    """Persist the threadExternalId for the active MCP session."""
    context_id = ctx.session_id
    thread_id = (thread_external_id or "").strip()
    if not thread_id:
        return {
            "contextId": context_id,
            "threadExternalId": None,
            "message": "thread_external_id is required.",
        }

    if not is_session_state_configured():
        return {
            "contextId": context_id,
            "threadExternalId": None,
            "message": "Session-state service is not configured for this server.",
        }

    try:
        result = merge_session_state(
            context_id,
            lambda payload: {**payload, "threadExternalId": thread_id},
        )
    except SessionStateError as exc:
        safe_print(f"[session-state] save failed: {exc}")
        return {
            "contextId": context_id,
            "threadExternalId": None,
            "message": str(exc),
        }

    payload = result.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}

    return {
        "contextId": result.get("contextId", context_id),
        "threadExternalId": payload.get("threadExternalId", thread_id),
        "createdAt": result.get("createdAt"),
    }


@mcp.tool
def getOntoAIThreadID(ctx: Context) -> dict[str, Any]:
    """Return the stored threadExternalId for the active MCP session."""
    context_id = ctx.session_id

    if not is_session_state_configured():
        return {
            "contextId": context_id,
            "threadExternalId": None,
            "message": "Session-state service is not configured for this server.",
        }

    try:
        payload, meta = get_session_state(context_id)
    except SessionStateError as exc:
        safe_print(f"[session-state] get failed: {exc}")
        return {
            "contextId": context_id,
            "threadExternalId": None,
            "message": str(exc),
        }

    thread_id = payload.get("threadExternalId") if isinstance(payload, dict) else None
    if thread_id is None:
        return {
            "contextId": meta.get("contextId", context_id),
            "threadExternalId": None,
            "message": "No session state stored for this context.",
        }

    return {
        "contextId": meta.get("contextId", context_id),
        "threadExternalId": thread_id,
        "createdAt": meta.get("createdAt"),
    }


@mcp.resource("onto://spaces")
def get_user_spaces() -> list[dict]:
    """Return the list of Onto realms (spaces) visible to the configured API key."""
    return _get_user_spaces_data()


@mcp.resource("onto://user/info")
def get_user_info() -> dict[str, Any]:
    """Return current user information resolved through the configured Onto API key."""
    try:
        return _get_current_user_data()
    except RuntimeError as exc:
        return {"error": str(exc)}


@mcp.tool
def list_available_realms() -> str:
    """Get list of available realms (spaces) visible to the configured API key."""
    spaces = _get_user_spaces_data()
    if not spaces:
        return "No realms found."
    if "error" in spaces[0]:
        return str(spaces[0]["error"])

    result_lines = [f"Available realms ({len(spaces)}):", ""]
    for index, space in enumerate(spaces, 1):
        result_lines.append(f"{index}. {space.get('name', 'N/A')}")
        result_lines.append(f"   ID: {space.get('id', 'N/A')}")
        result_lines.append("")
    return "\n".join(result_lines)


@mcp.tool
def search_templates(
    name_part: str,
    realm_id: str | None = None,
    include_children: bool = False,
    include_parents: bool = False,
) -> str:
    """Search for templates (meta entities) in Onto by name."""
    try:
        realm_id = _resolve_realm_id(realm_id)
    except RuntimeError as exc:
        return str(exc)

    payload = {
        "namePart": name_part,
        "children": include_children,
        "parents": include_parents,
    }

    try:
        response_data = _request_json("POST", f"{ONTO_API_BASE}/realm/{realm_id}/meta/find", json_payload=payload, timeout=15)
    except RuntimeError as exc:
        return str(exc)

    templates = response_data.get("result") if isinstance(response_data, dict) else response_data
    if not isinstance(templates, list):
        return f"Unexpected response format: {type(templates)}"
    if not templates:
        return f"No templates found matching '{name_part}' in realm {realm_id}"

    result_lines = [f"Found {len(templates)} template(s) matching '{name_part}':", ""]
    for index, template in enumerate(templates, 1):
        if not isinstance(template, dict):
            result_lines.append(f"{index}. {template}")
            result_lines.append("")
            continue
        result_lines.append(f"{index}. {template.get('name', 'N/A')}")
        result_lines.append(f"   UUID: {template.get('uuid', template.get('id', 'N/A'))}")
        comment = template.get("comment")
        if comment:
            result_lines.append(f"   Comment: {comment}")
        result_lines.append("")
    return "\n".join(result_lines)


@mcp.tool
def search_relation_templates(
    realm_id: str,
    relation_type_name: str = "",
    meta_ids: list[str] | None = None,
) -> str:
    """Search for relation templates in Onto through the read-only discovery endpoint."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."

    normalized_relation_type_name = relation_type_name.strip()
    try:
        normalized_meta_ids = _normalize_relation_template_meta_ids(meta_ids)
    except RuntimeError as exc:
        return str(exc)

    if not normalized_relation_type_name and not normalized_meta_ids:
        return "At least one filter must be provided: 'relation_type_name' or 'meta_ids'."

    payload: dict[str, Any] = {}
    if normalized_relation_type_name:
        payload["relationTypeName"] = normalized_relation_type_name
    if normalized_meta_ids:
        payload["metaIds"] = normalized_meta_ids

    try:
        response_data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/meta/relation/find",
            json_payload=payload,
            timeout=15,
        )
    except RuntimeError as exc:
        return str(exc)

    relation_templates = response_data.get("result") if isinstance(response_data, dict) else response_data
    if not isinstance(relation_templates, list):
        return f"Unexpected response format: {type(relation_templates)}"
    if not relation_templates:
        return "No relation templates found for the provided filters."

    applied_filters: list[str] = []
    if normalized_relation_type_name:
        applied_filters.append(f"relation_type_name='{normalized_relation_type_name}'")
    if normalized_meta_ids:
        applied_filters.append(f"meta_ids={normalized_meta_ids}")

    result_lines = [f"Found {len(relation_templates)} relation template(s) for {', '.join(applied_filters)}:", ""]
    for index, relation_template in enumerate(relation_templates, 1):
        if not isinstance(relation_template, dict):
            result_lines.append(f"{index}. {relation_template}")
            result_lines.append("")
            continue

        result_lines.append(f"{index}. {_extract_relation_template_name(relation_template)}")
        relation_template_id = relation_template.get("uuid") or relation_template.get("id") or "N/A"
        result_lines.append(f"   ID: {relation_template_id}")

        participants = _extract_relation_template_meta_participants(relation_template)
        if participants:
            result_lines.append(f"   Meta IDs: {', '.join(participants)}")

        comment = relation_template.get("comment")
        if comment:
            result_lines.append(f"   Comment: {comment}")
        result_lines.append("")

    return "\n".join(result_lines)


@mcp.tool
def search_entities_by_relations(
    realm_id: str,
    searched_meta_ids: list[str],
    predicates: list[dict[str, Any]] | None = None,
    include_descendants: bool = True,
    first: int = 0,
    offset: int = 100,
    sort: list[dict[str, Any]] | None = None,
) -> str:
    """
    Search entities using server-side one-hop relation-aware structural filters.

    Use this tool when entities of specific classifications must be constrained by
    direct relations to relation types, related classifications, or concrete
    related entity ids. Supports backend pagination (`first`, `offset`),
    descendant inclusion, and sort by `name` or `uuid`. This tool does not support name search, multi-hop
    traversal, boolean OR between predicates, nested predicates, direction, or
    business projections.
    """
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."

    try:
        normalized_searched_meta_ids = _normalize_non_empty_ids(searched_meta_ids, "searched_meta_ids")
        if len(normalized_searched_meta_ids) > _RELATION_SEARCH_MAX_SEARCHED_META_IDS:
            return (
                "Parameter 'searched_meta_ids' must contain at most "
                f"{_RELATION_SEARCH_MAX_SEARCHED_META_IDS} IDs."
            )
        if not isinstance(first, int):
            return "Parameter 'first' must be an integer."
        if first < 0:
            return "Parameter 'first' must not be negative."
        if not isinstance(offset, int):
            return "Parameter 'offset' must be an integer."
        if offset <= 0:
            return "Parameter 'offset' must be greater than zero."
        if offset > _RELATION_SEARCH_MAX_OFFSET:
            return f"Parameter 'offset' must be less than or equal to {_RELATION_SEARCH_MAX_OFFSET}."
        normalized_predicates = _normalize_relation_search_predicates(predicates)
        normalized_sort = _normalize_relation_search_sort(sort)
    except RuntimeError as exc:
        return str(exc)

    payload: dict[str, Any] = {
        "searchedMetaIds": normalized_searched_meta_ids,
        "includeDescendants": include_descendants,
        "first": first,
        "offset": offset,
    }
    if normalized_predicates:
        payload["predicates"] = normalized_predicates
    if normalized_sort:
        payload["sort"] = normalized_sort

    try:
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/entity/search",
            json_payload=payload,
            timeout=30,
        )
        entities = _extract_entities_from_search_response(data)
        page_metadata = _extract_entity_search_page_metadata(data)
    except RuntimeError as exc:
        return str(exc)

    return _format_entities_summary("Found", realm_id.strip(), entities, page_metadata)


@mcp.tool
def search_objects(
    realm_id: str | None = None,
    name_filter: str = "",
    template_uuid: str = "",
    comment_filter: str = "",
    load_all: bool = False,
    page_size: int = 20,
) -> str:
    """Search for objects in Onto by name, template, or comment with pagination support."""
    try:
        realm_id = _resolve_realm_id(realm_id)
    except RuntimeError as exc:
        return str(exc)

    url = f"{ONTO_API_BASE}/realm/{realm_id}/entity/find/v2"

    def make_request(first: int, offset: int) -> tuple[list, bool]:
        payload: dict[str, Any] = {
            "name": name_filter,
            "comment": comment_filter,
            "metaFieldFilters": [],
            "pagination": {"first": first, "offset": offset},
        }
        if template_uuid:
            payload["metaEntityRequest"] = {"uuid": template_uuid}

        response_data = _request_json("POST", url, json_payload=payload, timeout=30)
        if not isinstance(response_data, list):
            raise RuntimeError(f"Expected list response, got: {type(response_data)}")

        flat_results: list = []
        for item in response_data:
            if isinstance(item, dict) and isinstance(item.get("entities"), list):
                flat_results.extend(item["entities"])
            else:
                flat_results.append(item)

        has_more = len(flat_results) == offset
        return flat_results, has_more

    all_objects: list = []
    current_first = 0
    total_requests = 0
    max_requests = 100

    try:
        while total_requests < max_requests:
            total_requests += 1
            objects, has_more = make_request(current_first, page_size)
            all_objects.extend(objects)
            safe_print(f"[objects] page first={current_first} count={len(objects)} total={len(all_objects)}")
            if not load_all or not has_more:
                break
            current_first += len(objects)
    except RuntimeError as exc:
        return str(exc)

    if not all_objects:
        return f"No objects found in realm {realm_id}."

    result_lines = [
        f"Found {len(all_objects)} objects matching the current filters in realm {realm_id}:",
        "",
    ]
    for index, obj in enumerate(all_objects[:50], 1):
        if not isinstance(obj, dict):
            result_lines.append(f"{index}. {obj}")
            result_lines.append("")
            continue
        result_lines.append(f"{index}. {obj.get('name', 'N/A')}")
        result_lines.append(f"   UUID: {obj.get('id', 'N/A')}")
        meta_entity = obj.get("metaEntity") or {}
        if isinstance(meta_entity, dict) and meta_entity.get("name"):
            result_lines.append(
                f"   Template: {meta_entity.get('name')} ({meta_entity.get('id', meta_entity.get('uuid', 'N/A'))})"
            )
        comment = obj.get("comment")
        if comment:
            display_comment = comment[:100] + "..." if len(comment) > 100 else comment
            result_lines.append(f"   Comment: {display_comment}")
        result_lines.append("")

    if len(all_objects) > 50:
        result_lines.append(f"... and {len(all_objects) - 50} more objects.")
    return "\n".join(result_lines)


@mcp.tool
def create_realm(name: str, comment: str = "") -> str:
    """Create a new workspace (realm)."""
    if not name or not name.strip():
        return "Parameter 'name' is required and cannot be empty."

    payload = {"name": name.strip(), "comment": comment or ""}
    try:
        data = _request_json("POST", f"{ONTO_API_BASE}/realm/", json_payload=payload, timeout=30)
    except RuntimeError as exc:
        return str(exc)

    result = [
        "Workspace created successfully.",
        f"ID: {data.get('id', 'N/A')}",
        f"Name: {data.get('name', 'N/A')}",
    ]
    if data.get("comment"):
        result.append(f"Comment: {data['comment']}")
    return "\n".join(result)


@mcp.tool
def update_realm(realm_id: str, name: str, comment: str = "") -> str:
    """Update an existing workspace (realm)."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not name or not name.strip():
        return "Parameter 'name' is required and cannot be empty."

    payload = {"id": realm_id.strip(), "name": name.strip(), "comment": comment or ""}
    try:
        data = _request_json("PUT", f"{ONTO_API_BASE}/realm", json_payload=payload, timeout=30)
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(f"Workspace {realm_id.strip()} updated.", data)


@mcp.tool
def delete_realm(realm_id: str) -> str:
    """Delete a workspace (realm) by ID."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."

    try:
        data = _request_json(
            "DELETE",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}",
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(f"Workspace {realm_id.strip()} deleted.", data)


@mcp.tool
def save_template(realm_id: str, name: str, comment: str = "", template_id: str = "") -> str:
    """Create or update a template (meta entity) in a realm via saveMetaEntity upsert."""
    return _save_template_impl(realm_id=realm_id, name=name, comment=comment, template_id=template_id)


@mcp.tool
def create_template(realm_id: str, name: str, comment: str = "") -> str:
    """Create a new template (meta entity) in a specified realm."""
    return _save_template_impl(realm_id=realm_id, name=name, comment=comment)


@mcp.tool
def get_template(
    realm_id: str,
    template_id: str,
    include_children: bool = False,
    include_parents: bool = False,
    name: str = "",
) -> str:
    """Get a template (meta entity) by ID."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not template_id or not template_id.strip():
        return "Parameter 'template_id' is required and cannot be empty."

    query_params: dict[str, Any] = {
        "children": include_children,
        "parents": include_parents,
    }
    if name.strip():
        query_params["name"] = name.strip()

    try:
        data = _request_json(
            "GET",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/meta/{template_id.strip()}",
            query_params=query_params,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    data = _unwrap_result_dict(data)
    if not isinstance(data, dict):
        return f"Unexpected response format: {type(data)}"

    lines = _format_template_summary("Template loaded successfully.", data).splitlines()
    describer_fields = data.get("describerFields")
    if isinstance(describer_fields, list):
        lines.append(f"Describer fields: {len(describer_fields)}")
    fields = data.get("fields")
    if isinstance(fields, list):
        lines.append(f"Fields: {len(fields)}")
    return "\n".join(lines)


@mcp.tool
def delete_template(realm_id: str, template_id: str) -> str:
    """Delete a template (meta entity) by ID."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not template_id or not template_id.strip():
        return "Parameter 'template_id' is required and cannot be empty."

    try:
        data = _request_json(
            "DELETE",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/meta",
            query_params={"id": template_id.strip()},
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(f"Template {template_id.strip()} deleted.", data)


@mcp.tool
def link_template_to_parents(realm_id: str, child_template_id: str, parent_template_ids: list[str]) -> str:
    """Link a child template (meta entity) to one or more parent templates."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not child_template_id or not child_template_id.strip():
        return "Parameter 'child_template_id' is required and cannot be empty."
    if not parent_template_ids or not isinstance(parent_template_ids, list):
        return "Parameter 'parent_template_ids' must be a non-empty list."

    normalized_ids = [str(parent_id).strip() for parent_id in parent_template_ids if str(parent_id).strip()]
    if not normalized_ids:
        return "Parameter 'parent_template_ids' must contain at least one non-empty ID."

    try:
        data = _request_json(
            "PUT",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/meta/child/{child_template_id.strip()}/parents/link",
            query_params={"parentsUuids": normalized_ids},
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Linked template {child_template_id.strip()} to {len(normalized_ids)} parent template(s).",
        data,
    )


@mcp.tool
def unlink_template_from_parents(realm_id: str, child_template_id: str, parent_template_ids: list[str]) -> str:
    """Unlink a child template (meta entity) from one or more parent templates."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not child_template_id or not child_template_id.strip():
        return "Parameter 'child_template_id' is required and cannot be empty."
    if not parent_template_ids or not isinstance(parent_template_ids, list):
        return "Parameter 'parent_template_ids' must be a non-empty list."

    normalized_ids = [str(parent_id).strip() for parent_id in parent_template_ids if str(parent_id).strip()]
    if not normalized_ids:
        return "Parameter 'parent_template_ids' must contain at least one non-empty ID."

    try:
        data = _request_json(
            "PUT",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/meta/child/{child_template_id.strip()}/parents/unlink",
            query_params={"parentsUuids": normalized_ids},
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Unlinked template {child_template_id.strip()} from {len(normalized_ids)} parent template(s).",
        data,
    )


@mcp.tool
def create_entities_batch(realm_id: str, entities: list[dict]) -> str:
    """Create multiple entities in a realm in one batch."""
    return _save_entities_batch_impl(realm_id=realm_id, entities=entities)


@mcp.tool
def save_entity(
    realm_id: str,
    name: str,
    comment: str = "",
    entity_id: str = "",
    meta_entity_id: str = "",
) -> str:
    """Create or update an entity via saveEntity upsert semantics."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not name or not name.strip():
        return "Parameter 'name' is required and cannot be empty."

    payload = _build_entity_payload(
        name=name,
        comment=comment,
        entity_id=entity_id,
        meta_entity_id=meta_entity_id,
    )

    try:
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/entity",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    if not isinstance(data, dict):
        return f"Entity saved, but response format is unexpected: {type(data)}"

    action = "Entity updated successfully." if entity_id.strip() else "Entity created successfully."
    lines = _format_entity_summary(action, data, fallback_name=name.strip()).splitlines()
    if not meta_entity_id.strip():
        lines.append("Meta entity: omitted from request; Onto may remove current classification.")
    return "\n".join(lines)


@mcp.tool
def save_entities_batch(realm_id: str, entities: list[dict]) -> str:
    """Create or update multiple entities in a realm in one batch."""
    return _save_entities_batch_impl(realm_id=realm_id, entities=entities)


@mcp.tool
def get_entity(
    realm_id: str,
    entity_id: str,
    related_diagrams: bool = False,
    related_entities: bool = False,
    with_empty_stickers: bool = False,
    name: str = "",
) -> str:
    """Get an entity by ID."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not entity_id or not entity_id.strip():
        return "Parameter 'entity_id' is required and cannot be empty."

    query_params: dict[str, Any] = {
        "relatedDiagrams": related_diagrams,
        "relatedEntities": related_entities,
        "withEmptyStickers": with_empty_stickers,
    }
    if name.strip():
        query_params["name"] = name.strip()

    try:
        data = _request_json(
            "GET",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/entity/{entity_id.strip()}",
            query_params=query_params,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    data = _unwrap_result_dict(data)
    if not isinstance(data, dict):
        return f"Unexpected response format: {type(data)}"

    lines = _format_entity_summary("Entity loaded successfully.", data).splitlines()
    fields = data.get("fields")
    if isinstance(fields, list):
        lines.append(f"Fields: {len(fields)}")
    if related_diagrams and isinstance(data.get("related_diagrams"), list):
        lines.append(f"Related diagrams: {len(data['related_diagrams'])}")
    if related_entities and isinstance(data.get("related_entities"), list):
        lines.append(f"Related entities: {len(data['related_entities'])}")
    return "\n".join(lines)


@mcp.tool
def get_node_chat_messages(realm_id: str, node_id: str) -> str:
    """Read object/node chat messages for a node in a realm; this is not assistant chat."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not node_id or not node_id.strip():
        return "Parameter 'node_id' is required and cannot be empty."

    normalized_realm_id = realm_id.strip()
    normalized_node_id = node_id.strip()
    try:
        data = _request_json(
            "GET",
            f"{ONTO_API_BASE}/realm/{normalized_realm_id}/chat/{normalized_node_id}",
            timeout=30,
        )
        messages = _extract_node_chat_messages(data)
    except RuntimeError as exc:
        return str(exc)

    return _format_node_chat_messages(normalized_realm_id, normalized_node_id, messages)


@mcp.tool
def create_node_chat_message(realm_id: str, node_id: str, text: str) -> str:
    """Append an object/node chat message to a node in a realm; this is not assistant chat."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not node_id or not node_id.strip():
        return "Parameter 'node_id' is required and cannot be empty."
    if not text or not text.strip():
        return "Parameter 'text' is required and cannot be empty."

    normalized_realm_id = realm_id.strip()
    normalized_node_id = node_id.strip()
    payload = {"text": text.strip()}
    try:
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{normalized_realm_id}/chat/{normalized_node_id}",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Created object/node chat message for node {normalized_node_id} in realm {normalized_realm_id}.",
        data,
    )


@mcp.tool
def search_entities(
    realm_id: str | None = None,
    name_filter: str = "",
    meta_entity_id: str = "",
    comment_filter: str = "",
    include_inherited: bool = False,
    offset: int = 0,
    limit: int = 20,
) -> str:
    """Search entities in Onto without related-meta expansion."""
    try:
        realm_id = _resolve_realm_id(realm_id)
    except RuntimeError as exc:
        return str(exc)

    payload: dict[str, Any] = {
        "name": name_filter,
        "comment": comment_filter,
        "includeInherited": include_inherited,
        "metaFieldFilters": [],
        "pagination": {"first": offset, "offset": limit},
    }
    if meta_entity_id.strip():
        payload["metaEntityRequest"] = {"uuid": meta_entity_id.strip()}

    try:
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{realm_id}/entity/find",
            json_payload=payload,
            timeout=30,
        )
        entities = _extract_entities_from_search_response(data)
    except RuntimeError as exc:
        return str(exc)

    if not entities:
        return f"No entities found in realm {realm_id}."

    result_lines = [f"Found {len(entities)} entities in realm {realm_id}:", ""]
    for index, entity in enumerate(entities[:50], 1):
        result_lines.append(f"{index}. {entity.get('name', 'N/A')}")
        result_lines.append(f"   UUID: {entity.get('id', entity.get('uuid', 'N/A'))}")
        meta_entity = entity.get("metaEntity") or {}
        if isinstance(meta_entity, dict) and meta_entity.get("name"):
            result_lines.append(
                f"   Template: {meta_entity.get('name')} ({meta_entity.get('id', meta_entity.get('uuid', 'N/A'))})"
            )
        comment = entity.get("comment")
        if comment:
            display_comment = comment[:100] + "..." if len(comment) > 100 else comment
            result_lines.append(f"   Comment: {display_comment}")
        result_lines.append("")

    if len(entities) > 50:
        result_lines.append(f"... and {len(entities) - 50} more entities.")
    return "\n".join(result_lines)


@mcp.tool
def search_entities_with_related_meta(
    realm_id: str | None = None,
    name_filter: str = "",
    meta_entity_id: str = "",
    comment_filter: str = "",
    include_inherited: bool = False,
    offset: int = 0,
    limit: int = 20,
) -> str:
    """Search entities in Onto with related-meta expansion."""
    try:
        realm_id = _resolve_realm_id(realm_id)
    except RuntimeError as exc:
        return str(exc)

    payload: dict[str, Any] = {
        "name": name_filter,
        "comment": comment_filter,
        "includeInherited": include_inherited,
        "metaFieldFilters": [],
        "pagination": {"first": offset, "offset": limit},
    }
    if meta_entity_id.strip():
        payload["metaEntityRequest"] = {"uuid": meta_entity_id.strip()}

    try:
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{realm_id}/entity/find/v2",
            json_payload=payload,
            timeout=30,
        )
        entities = _extract_entities_from_search_response(data)
    except RuntimeError as exc:
        return str(exc)

    if not entities:
        return f"No entities found in realm {realm_id}."

    result_lines = [f"Found {len(entities)} entities with related meta in realm {realm_id}:", ""]
    for index, entity in enumerate(entities[:50], 1):
        result_lines.append(f"{index}. {entity.get('name', 'N/A')}")
        result_lines.append(f"   UUID: {entity.get('id', entity.get('uuid', 'N/A'))}")
        meta_entity = entity.get("metaEntity") or {}
        if isinstance(meta_entity, dict) and meta_entity.get("name"):
            result_lines.append(
                f"   Template: {meta_entity.get('name')} ({meta_entity.get('id', meta_entity.get('uuid', 'N/A'))})"
            )
        fields_map = entity.get("fieldsMap")
        if isinstance(fields_map, dict):
            result_lines.append(f"   Related meta fields: {len(fields_map)}")
        result_lines.append("")

    if len(entities) > 50:
        result_lines.append(f"... and {len(entities) - 50} more entities.")
    return "\n".join(result_lines)


@mcp.tool
def delete_entity(realm_id: str, entity_ids: list[str], name: str = "") -> str:
    """Delete one or more entities by ID."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not entity_ids or not isinstance(entity_ids, list):
        return "Parameter 'entity_ids' must be a non-empty list."

    normalized_ids = [str(entity_id).strip() for entity_id in entity_ids if str(entity_id).strip()]
    if not normalized_ids:
        return "Parameter 'entity_ids' must contain at least one non-empty ID."

    query_params: dict[str, Any] = {"ids": normalized_ids}
    if name.strip():
        query_params["name"] = name.strip()

    try:
        data = _request_json(
            "DELETE",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/entity",
            query_params=query_params,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(f"Deleted {len(normalized_ids)} entity(s).", data)


@mcp.tool
def create_relation(
    realm_id: str,
    start_entity_id: str,
    end_entity_id: str,
    relation_type_name: str,
    start_role: str = "",
    end_role: str = "",
    additional_properties: dict[str, Any] | None = None,
) -> str:
    """Create a relation between two entities."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not start_entity_id or not start_entity_id.strip():
        return "Parameter 'start_entity_id' is required and cannot be empty."
    if not end_entity_id or not end_entity_id.strip():
        return "Parameter 'end_entity_id' is required and cannot be empty."
    if not relation_type_name or not relation_type_name.strip():
        return "Parameter 'relation_type_name' is required and cannot be empty."

    payload = _build_entity_relation_payload(
        start_entity_id=start_entity_id,
        end_entity_id=end_entity_id,
        relation_type_name=relation_type_name,
        start_role=start_role,
        end_role=end_role,
        additional_properties=additional_properties,
    )

    try:
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/entity/relation",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Created relation '{relation_type_name.strip()}' from {start_entity_id.strip()} to {end_entity_id.strip()}.",
        data,
    )


@mcp.tool
def update_relation(
    realm_id: str,
    start_entity_id: str,
    end_entity_id: str,
    relation_type_name: str,
    start_role: str = "",
    end_role: str = "",
    additional_properties: dict[str, Any] | None = None,
) -> str:
    """Update a relation between two entities."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not start_entity_id or not start_entity_id.strip():
        return "Parameter 'start_entity_id' is required and cannot be empty."
    if not end_entity_id or not end_entity_id.strip():
        return "Parameter 'end_entity_id' is required and cannot be empty."
    if not relation_type_name or not relation_type_name.strip():
        return "Parameter 'relation_type_name' is required and cannot be empty."

    payload = _build_entity_relation_payload(
        start_entity_id=start_entity_id,
        end_entity_id=end_entity_id,
        relation_type_name=relation_type_name,
        start_role=start_role,
        end_role=end_role,
        additional_properties=additional_properties,
    )

    try:
        data = _request_json(
            "PUT",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/entity/relation",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Updated relation '{relation_type_name.strip()}' from {start_entity_id.strip()} to {end_entity_id.strip()}.",
        data,
    )


@mcp.tool
def delete_relation(
    realm_id: str,
    start_entity_id: str,
    end_entity_id: str,
    relation_type_name: str,
    name: str = "",
) -> str:
    """Delete a relation between two entities."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not start_entity_id or not start_entity_id.strip():
        return "Parameter 'start_entity_id' is required and cannot be empty."
    if not end_entity_id or not end_entity_id.strip():
        return "Parameter 'end_entity_id' is required and cannot be empty."
    if not relation_type_name or not relation_type_name.strip():
        return "Parameter 'relation_type_name' is required and cannot be empty."

    query_params: dict[str, Any] = {
        "startEntityId": start_entity_id.strip(),
        "endEntityId": end_entity_id.strip(),
        "relationTypeName": relation_type_name.strip(),
    }
    if name.strip():
        query_params["name"] = name.strip()

    try:
        data = _request_json(
            "DELETE",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/entity/relation",
            query_params=query_params,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Deleted relation '{relation_type_name.strip()}' from {start_entity_id.strip()} to {end_entity_id.strip()}.",
        data,
    )


@mcp.tool
def create_meta_relation(
    realm_id: str,
    start_meta_id: str,
    end_meta_id: str,
    relation_type_name: str,
    start_min: int = 0,
    start_max: int = 1,
    end_min: int = 0,
    end_max: int = 1,
    equal: bool = False,
) -> str:
    """Create a template/meta relation."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not start_meta_id or not start_meta_id.strip():
        return "Parameter 'start_meta_id' is required and cannot be empty."
    if not end_meta_id or not end_meta_id.strip():
        return "Parameter 'end_meta_id' is required and cannot be empty."
    if not relation_type_name or not relation_type_name.strip():
        return "Parameter 'relation_type_name' is required and cannot be empty."

    payload = _build_meta_relation_payload(
        start_meta_id=start_meta_id,
        end_meta_id=end_meta_id,
        relation_type_name=relation_type_name,
        start_min=start_min,
        start_max=start_max,
        end_min=end_min,
        end_max=end_max,
        equal=equal,
    )

    try:
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/meta/relation",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Created meta relation '{relation_type_name.strip()}' from {start_meta_id.strip()} to {end_meta_id.strip()}.",
        data,
    )


@mcp.tool
def update_meta_relation(
    realm_id: str,
    start_meta_id: str,
    end_meta_id: str,
    relation_type_name: str,
    start_min: int = 0,
    start_max: int = 1,
    end_min: int = 0,
    end_max: int = 1,
    equal: bool = False,
) -> str:
    """Update a template/meta relation."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not start_meta_id or not start_meta_id.strip():
        return "Parameter 'start_meta_id' is required and cannot be empty."
    if not end_meta_id or not end_meta_id.strip():
        return "Parameter 'end_meta_id' is required and cannot be empty."
    if not relation_type_name or not relation_type_name.strip():
        return "Parameter 'relation_type_name' is required and cannot be empty."

    payload = _build_meta_relation_payload(
        start_meta_id=start_meta_id,
        end_meta_id=end_meta_id,
        relation_type_name=relation_type_name,
        start_min=start_min,
        start_max=start_max,
        end_min=end_min,
        end_max=end_max,
        equal=equal,
    )

    try:
        data = _request_json(
            "PUT",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/meta/relation",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Updated meta relation '{relation_type_name.strip()}' from {start_meta_id.strip()} to {end_meta_id.strip()}.",
        data,
    )


@mcp.tool
def delete_meta_relation(
    realm_id: str,
    start_meta_id: str,
    end_meta_id: str,
    relation_type_name: str,
) -> str:
    """Delete a template/meta relation."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not start_meta_id or not start_meta_id.strip():
        return "Parameter 'start_meta_id' is required and cannot be empty."
    if not end_meta_id or not end_meta_id.strip():
        return "Parameter 'end_meta_id' is required and cannot be empty."
    if not relation_type_name or not relation_type_name.strip():
        return "Parameter 'relation_type_name' is required and cannot be empty."

    try:
        data = _request_json(
            "DELETE",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/meta/relation",
            query_params={
                "startMetaId": start_meta_id.strip(),
                "endMetaId": end_meta_id.strip(),
                "relationTypeName": relation_type_name.strip(),
            },
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Deleted meta relation '{relation_type_name.strip()}' from {start_meta_id.strip()} to {end_meta_id.strip()}.",
        data,
    )


@mcp.tool
def save_entity_fields(realm_id: str, entity_id: str, fields: list[dict[str, Any]]) -> str:
    """Save fields on an entity, including template-derived fields linked by metaFieldUuid."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not entity_id or not entity_id.strip():
        return "Parameter 'entity_id' is required and cannot be empty."

    try:
        payload = _build_entity_fields_payload(fields)
    except RuntimeError as exc:
        return str(exc)

    try:
        data = _request_json(
            "PATCH",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/entity/{entity_id.strip()}/fields",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Saved {len(payload)} field(s) for entity {entity_id.strip()}.",
        data,
    )


@mcp.tool
def delete_entity_fields(realm_id: str, entity_id: str, field_ids: list[str]) -> str:
    """Delete one or more fields from an entity by field UUID."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not entity_id or not entity_id.strip():
        return "Parameter 'entity_id' is required and cannot be empty."

    try:
        normalized_field_ids = _normalize_non_empty_ids(field_ids, "field_ids")
    except RuntimeError as exc:
        return str(exc)

    try:
        data = _request_json(
            "DELETE",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/entity/{entity_id.strip()}/fields",
            query_params={"fieldsUuids": normalized_field_ids},
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Deleted {len(normalized_field_ids)} field(s) from entity {entity_id.strip()}.",
        data,
    )


@mcp.tool
def save_template_fields(realm_id: str, template_id: str, fields: list[dict[str, Any]]) -> str:
    """Save fields on a template/meta entity through the confirmed meta fields endpoint."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not template_id or not template_id.strip():
        return "Parameter 'template_id' is required and cannot be empty."

    try:
        payload = _build_template_fields_payload(fields)
    except RuntimeError as exc:
        return str(exc)

    try:
        data = _request_json(
            "PATCH",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/meta/{template_id.strip()}/fields",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_template_fields_summary(template_id.strip(), data)


@mcp.tool
def delete_template_fields(realm_id: str, template_id: str, field_ids: list[str]) -> str:
    """Delete one or more fields from a template/meta entity by field UUID."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not template_id or not template_id.strip():
        return "Parameter 'template_id' is required and cannot be empty."

    try:
        normalized_field_ids = _normalize_non_empty_ids(field_ids, "field_ids")
    except RuntimeError as exc:
        return str(exc)

    try:
        data = _request_json(
            "DELETE",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/meta/{template_id.strip()}/fields",
            query_params={"fieldsIds": normalized_field_ids},
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Deleted {len(normalized_field_ids)} field(s) from template {template_id.strip()}.",
        data,
    )


@mcp.tool
def search_diagrams(
    realm_id: str,
    name_part: str = "",
    tag_ids: list[str] | None = None,
    page: int = 1,
    size: int = 20,
) -> str:
    """List, search, and filter diagrams in a realm by name and context tags."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."

    try:
        normalized_page = _normalize_positive_int(page, "page")
        normalized_size = _normalize_positive_int(size, "size")
        normalized_tag_ids = _normalize_non_empty_ids(tag_ids, "tag_ids") if tag_ids is not None else []
    except RuntimeError as exc:
        return str(exc)

    normalized_realm_id = realm_id.strip()
    payload = {"namePart": name_part.strip() if name_part else "", "tags": normalized_tag_ids}
    try:
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{normalized_realm_id}/diagram/v2/page/{normalized_page}/size/{normalized_size}",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_diagram_page(data, normalized_realm_id)


@mcp.tool
def search_context_tags(realm_id: str, name_part: str = "", page: int = 1, size: int = 20) -> str:
    """List and search realm context tags that can be assigned to diagrams."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."

    try:
        normalized_page = _normalize_positive_int(page, "page")
        normalized_size = _normalize_positive_int(size, "size")
    except RuntimeError as exc:
        return str(exc)

    normalized_realm_id = realm_id.strip()
    normalized_name_part = name_part.strip() if name_part and name_part.strip() else "*"
    encoded_name_part = quote(normalized_name_part, safe="*")
    try:
        data = _request_json(
            "GET",
            f"{ONTO_API_BASE}/realm/{normalized_realm_id}/entity/tags/name/{encoded_name_part}/page/{normalized_page}/size/{normalized_size}",
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_context_tag_page(data, normalized_realm_id)


@mcp.tool
def create_context_tag_from_object(realm_id: str, entity_id: str) -> str:
    """Mark an existing object/entity in a realm as a context tag without creating a duplicate object."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not entity_id or not entity_id.strip():
        return "Parameter 'entity_id' is required and cannot be empty."

    normalized_realm_id = realm_id.strip()
    normalized_entity_id = entity_id.strip()
    try:
        entity_data = _request_json(
            "GET",
            f"{ONTO_API_BASE}/realm/{normalized_realm_id}/entity/{normalized_entity_id}",
            query_params={"relatedDiagrams": False, "relatedEntities": False, "withEmptyStickers": False},
            timeout=30,
        )
        entity = _unwrap_result_dict(entity_data)
        if not isinstance(entity, dict):
            return f"Unexpected entity response format: {type(entity)}"

        name = str(entity.get("name", "")).strip()
        if not name:
            return "Cannot create context tag because existing entity name is missing."

        meta_entity = entity.get("metaEntity") if isinstance(entity.get("metaEntity"), dict) else {}
        meta_entity_id = meta_entity.get("id") or meta_entity.get("uuid")
        if not meta_entity_id:
            return "Cannot create context tag because existing entity template id is missing."

        payload = {
            "id": normalized_entity_id,
            "name": name,
            "comment": "" if entity.get("comment") is None else str(entity.get("comment")),
            "metaEntityId": str(meta_entity_id),
            "isTag": True,
        }
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{normalized_realm_id}/entity",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Created context tag from existing entity {normalized_entity_id} ({name}).",
        data,
    )


@mcp.tool
def add_diagram_tag(realm_id: str, diagram_id: str, tag_id: str) -> str:
    """Assign a context tag to a diagram using read-modify-write over the full tag list."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not diagram_id or not diagram_id.strip():
        return "Parameter 'diagram_id' is required and cannot be empty."
    if not tag_id or not tag_id.strip():
        return "Parameter 'tag_id' is required and cannot be empty."

    normalized_realm_id = realm_id.strip()
    normalized_diagram_id = diagram_id.strip()
    normalized_tag_id = tag_id.strip()
    try:
        diagram = _load_diagram_for_tag_update(normalized_realm_id, normalized_diagram_id)
        current_tag_ids = _extract_diagram_tag_ids(diagram)
        if normalized_tag_id in current_tag_ids:
            return (
                f"Diagram {normalized_diagram_id} already has context tag {normalized_tag_id}. "
                f"Final tag count: {len(current_tag_ids)}."
            )

        final_tag_ids = [*current_tag_ids, normalized_tag_id]
        payload = _build_diagram_update_payload(diagram, final_tag_ids)
        data = _request_json(
            "PUT",
            f"{ONTO_API_BASE}/realm/{normalized_realm_id}/diagram/v2/{normalized_diagram_id}",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Added context tag {normalized_tag_id} to diagram {normalized_diagram_id}. Final tag count: {len(final_tag_ids)}.",
        data,
    )


@mcp.tool
def remove_diagram_tag(realm_id: str, diagram_id: str, tag_id: str) -> str:
    """Remove a context tag from a diagram using read-modify-write over the full tag list."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not diagram_id or not diagram_id.strip():
        return "Parameter 'diagram_id' is required and cannot be empty."
    if not tag_id or not tag_id.strip():
        return "Parameter 'tag_id' is required and cannot be empty."

    normalized_realm_id = realm_id.strip()
    normalized_diagram_id = diagram_id.strip()
    normalized_tag_id = tag_id.strip()
    try:
        diagram = _load_diagram_for_tag_update(normalized_realm_id, normalized_diagram_id)
        current_tag_ids = _extract_diagram_tag_ids(diagram)
        if normalized_tag_id not in current_tag_ids:
            return (
                f"Diagram {normalized_diagram_id} does not have context tag {normalized_tag_id}. "
                f"Final tag count: {len(current_tag_ids)}."
            )

        final_tag_ids = [existing_tag_id for existing_tag_id in current_tag_ids if existing_tag_id != normalized_tag_id]
        payload = _build_diagram_update_payload(diagram, final_tag_ids)
        data = _request_json(
            "PUT",
            f"{ONTO_API_BASE}/realm/{normalized_realm_id}/diagram/v2/{normalized_diagram_id}",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Removed context tag {normalized_tag_id} from diagram {normalized_diagram_id}. Final tag count: {len(final_tag_ids)}.",
        data,
    )


@mcp.tool
def create_diagram(realm_id: str, name: str, comment: str = "") -> str:
    """Create a diagram in a realm through the confirmed diagram v2 endpoint."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not name or not name.strip():
        return "Parameter 'name' is required and cannot be empty."

    try:
        data = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/diagram/v2",
            query_params={
                "name": name.strip(),
                "comment": comment or "",
            },
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_diagram_info_summary("Diagram created successfully.", data)


@mcp.tool
def get_diagram(realm_id: str, diagram_id: str) -> str:
    """Load a diagram and summarize its primary metadata and content counts."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not diagram_id or not diagram_id.strip():
        return "Parameter 'diagram_id' is required and cannot be empty."

    try:
        data = _request_json(
            "GET",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/diagram/v2/{diagram_id.strip()}",
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_get_diagram_summary(diagram_id.strip(), data)


@mcp.tool
def update_diagram(
    realm_id: str,
    diagram_id: str,
    name: str = "",
    comment: str = "",
    tag_ids: list[str] | None = None,
) -> str:
    """Update diagram metadata through the diagram v2 endpoint."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not diagram_id or not diagram_id.strip():
        return "Parameter 'diagram_id' is required and cannot be empty."

    payload: dict[str, Any] = {}
    if name.strip():
        payload["name"] = name.strip()
    if comment.strip():
        payload["comment"] = comment.strip()
    if tag_ids is not None:
        try:
            payload["tags"] = _normalize_non_empty_ids(tag_ids, "tag_ids")
        except RuntimeError as exc:
            return str(exc)

    if not payload:
        return "At least one of 'name', 'comment', or 'tag_ids' must be provided."

    try:
        data = _request_json(
            "PUT",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/diagram/v2/{diagram_id.strip()}",
            json_payload=payload,
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Updated diagram {diagram_id.strip()}.",
        data,
    )


@mcp.tool
def delete_diagram(realm_id: str, diagram_id: str) -> str:
    """Delete a diagram by id."""
    if not realm_id or not realm_id.strip():
        return "Parameter 'realm_id' is required and cannot be empty."
    if not diagram_id or not diagram_id.strip():
        return "Parameter 'diagram_id' is required and cannot be empty."

    try:
        data = _request_json(
            "DELETE",
            f"{ONTO_API_BASE}/realm/{realm_id.strip()}/diagram/v2/{diagram_id.strip()}",
            timeout=30,
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_status_response(
        f"Deleted diagram {diagram_id.strip()}.",
        data,
    )
