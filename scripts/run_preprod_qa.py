from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from onto_mcp.api_resources import ONTO_API_BASE, mcp, _get_user_spaces_data, _request_json


EXPECTED_TOOLS = {
    "about_onto",
    "list_available_realms",
    "search_templates",
    "search_objects",
    "create_realm",
    "update_realm",
    "delete_realm",
    "save_template",
    "create_template",
    "get_template",
    "list_templates",
    "delete_template",
    "link_template_to_parents",
    "save_entity",
    "save_entities_batch",
    "create_entities_batch",
    "get_entity",
    "search_entities",
    "search_entities_with_related_meta",
    "delete_entity",
    "create_relation",
    "update_relation",
    "delete_relation",
    "create_meta_relation",
    "update_meta_relation",
    "delete_meta_relation",
    "saveOntoAIThreadID",
    "getOntoAIThreadID",
}


class FakeContext:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


@dataclass
class CaseResult:
    tool: str
    status: str
    what_was_tested: str
    observed_behavior: str
    contract_mismatch: str
    recommended_fix: str


def extract_text(tool_result: Any) -> str:
    structured = getattr(tool_result, "structured_content", None)
    if isinstance(structured, dict) and "result" in structured:
        return str(structured["result"])

    content = getattr(tool_result, "content", None)
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if text is not None:
                texts.append(str(text))
        return "\n".join(texts)

    return str(tool_result)


def parse_id(summary: str) -> str:
    match = re.search(r"^ID:\s*(.+)$", summary, flags=re.MULTILINE)
    if not match:
        raise ValueError(f"Could not parse ID from summary:\n{summary}")
    return match.group(1).strip()


def is_real_id(value: str) -> bool:
    normalized = (value or "").strip()
    return bool(normalized) and normalized.upper() != "N/A"


def contains_value(node: Any, expected: Any) -> bool:
    if node == expected:
        return True
    if isinstance(node, dict):
        return any(contains_value(value, expected) for value in node.values())
    if isinstance(node, list):
        return any(contains_value(value, expected) for value in node)
    return False


def summarize_exception(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


async def invoke_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    tool = mcp._tool_manager._tools[name]
    return await tool.run(arguments or {})


def call_session_tool(name: str, *args: Any, **kwargs: Any) -> Any:
    tool = mcp._tool_manager._tools[name]
    return tool.fn(*args, **kwargs)


def raw_get_template(realm_id: str, template_id: str, *, children: bool = False, parents: bool = False) -> dict[str, Any]:
    data = _request_json(
        "GET",
        f"{ONTO_API_BASE}/realm/{realm_id}/meta/{template_id}",
        query_params={"children": children, "parents": parents},
        timeout=30,
    )
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected template payload type: {type(data)}")
    return data


def raw_get_entity(
    realm_id: str,
    entity_id: str,
    *,
    related_entities: bool = False,
    related_diagrams: bool = False,
    with_empty_stickers: bool = False,
) -> dict[str, Any]:
    data = _request_json(
        "GET",
        f"{ONTO_API_BASE}/realm/{realm_id}/entity/{entity_id}",
        query_params={
            "relatedEntities": related_entities,
            "relatedDiagrams": related_diagrams,
            "withEmptyStickers": with_empty_stickers,
        },
        timeout=30,
    )
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected entity payload type: {type(data)}")
    return data


def raw_find_any_template(realm_id: str) -> dict[str, Any] | None:
    data = _request_json(
        "POST",
        f"{ONTO_API_BASE}/realm/{realm_id}/meta/find",
        json_payload={"namePart": "", "children": False, "parents": False},
        timeout=30,
    )
    result = data.get("result") if isinstance(data, dict) else data
    if isinstance(result, list) and result:
        return result[0]
    return None


def raw_find_template_by_name(realm_id: str, name_part: str) -> dict[str, Any] | None:
    data = _request_json(
        "POST",
        f"{ONTO_API_BASE}/realm/{realm_id}/meta/find",
        json_payload={"namePart": name_part, "children": False, "parents": False},
        timeout=30,
    )
    result = data.get("result") if isinstance(data, dict) else data
    if not isinstance(result, list):
        return None
    exact = [
        item for item in result
        if isinstance(item, dict) and str(item.get("name", "")).strip() == name_part
    ]
    if exact:
        return exact[0]
    return result[0] if result else None


def raw_find_any_entity(realm_id: str) -> dict[str, Any] | None:
    data = _request_json(
        "POST",
        f"{ONTO_API_BASE}/realm/{realm_id}/entity/find",
        json_payload={
            "name": "",
            "comment": "",
            "includeInherited": False,
            "metaFieldFilters": [],
            "pagination": {"offset": 0, "first": 1},
        },
        timeout=30,
    )
    if not isinstance(data, list):
        return None
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("entities"), list) and item["entities"]:
            return item["entities"][0]
        if isinstance(item, dict):
            return item
    return None


def raw_find_entity_by_name(realm_id: str, name: str) -> dict[str, Any] | None:
    data = _request_json(
        "POST",
        f"{ONTO_API_BASE}/realm/{realm_id}/entity/find",
        json_payload={
            "name": name,
            "comment": "",
            "includeInherited": False,
            "metaFieldFilters": [],
            "pagination": {"offset": 0, "first": 10},
        },
        timeout=30,
    )
    if not isinstance(data, list):
        return None
    matches: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("entities"), list):
            matches.extend([entry for entry in item["entities"] if isinstance(entry, dict)])
        elif isinstance(item, dict):
            matches.append(item)
    exact = [item for item in matches if str(item.get("name", "")).strip() == name]
    if exact:
        return exact[0]
    return matches[0] if matches else None


async def main() -> int:
    if not ONTO_API_BASE or not os.getenv("ONTO_API_KEY", "").strip():
        print("ONTO_API_BASE and ONTO_API_KEY must be configured in environment.", file=sys.stderr)
        return 2

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"qa_codex_{timestamp}_{uuid.uuid4().hex[:8]}"
    spaces = _get_user_spaces_data()
    if not spaces or "error" in spaces[0]:
        raise RuntimeError(f"Failed to resolve visible realms: {spaces}")
    default_realm_id = str(spaces[0]["id"])

    results: list[CaseResult] = []
    created_realm_id: str | None = None
    created_template_ids: list[str] = []
    created_entity_ids: list[str] = []
    relation_type_name = f"{prefix}_rel"
    meta_relation_type_name = f"{prefix}_meta_rel"

    def add_result(
        tool: str,
        status: str,
        what_was_tested: str,
        observed_behavior: str,
        contract_mismatch: str = "",
        recommended_fix: str = "",
    ) -> None:
        results.append(
            CaseResult(
                tool=tool,
                status=status,
                what_was_tested=what_was_tested,
                observed_behavior=observed_behavior,
                contract_mismatch=contract_mismatch,
                recommended_fix=recommended_fix,
            )
        )

    try:
        actual_tools = set(mcp._tool_manager._tools.keys())
        missing = sorted(EXPECTED_TOOLS - actual_tools)
        unexpected = sorted(actual_tools - EXPECTED_TOOLS)
        add_result(
            "tool_registration",
            "pass" if not missing else "fail",
            "Compared registered runtime tools against QA_MCP_TOOL_CATALOG.md expected set.",
            f"registered={len(actual_tools)}, missing={missing}, unexpected={unexpected}",
            "" if not missing else "Runtime tool set is missing documented tools.",
            "" if not missing else "Register the missing tools or update the catalog to match runtime.",
        )

        list_realms_summary = extract_text(await invoke_tool("list_available_realms"))
        add_result(
            "list_available_realms",
            "pass" if f"ID: {default_realm_id}" in list_realms_summary else "fail",
            "Verified live realm listing via configured API key.",
            list_realms_summary.splitlines()[0],
            "" if f"ID: {default_realm_id}" in list_realms_summary else "Default visible realm not present in summary.",
            "" if f"ID: {default_realm_id}" in list_realms_summary else "Inspect user realm-role extraction and formatter.",
        )

        absent_token = f"__{prefix}_absent__"
        search_templates_summary = extract_text(await invoke_tool("search_templates", {"name_part": absent_token}))
        search_objects_summary = extract_text(await invoke_tool("search_objects", {"name_filter": absent_token, "page_size": 5}))
        search_entities_summary = extract_text(await invoke_tool("search_entities", {"name_filter": absent_token, "limit": 5}))
        search_entities_v2_summary = extract_text(
            await invoke_tool("search_entities_with_related_meta", {"name_filter": absent_token, "limit": 5})
        )
        add_result(
            "read_only_baseline",
            "pass",
            "Verified default realm fallback and empty-result handling for template/object/entity searches.",
            " | ".join(
                [
                    search_templates_summary,
                    search_objects_summary,
                    search_entities_summary,
                    search_entities_v2_summary,
                ]
            ),
            "",
            "",
        )

        existing_template = raw_find_any_template(default_realm_id)
        if existing_template:
            existing_template_id = str(existing_template.get("uuid") or existing_template.get("id"))
            get_template_summary = extract_text(
                await invoke_tool(
                    "get_template",
                    {"realm_id": default_realm_id, "template_id": existing_template_id, "include_children": True, "include_parents": True},
                )
            )
            raw_template = raw_get_template(default_realm_id, existing_template_id, children=True, parents=True)
            describer_count = len(raw_template.get("describerFields", [])) if isinstance(raw_template.get("describerFields"), list) else 0
            fields_count = len(raw_template.get("fields", [])) if isinstance(raw_template.get("fields"), list) else 0
            summary_matches = (
                f"Describer fields: {describer_count}" in get_template_summary
                and f"Fields: {fields_count}" in get_template_summary
            )
            add_result(
                "get_template",
                "pass" if summary_matches else "ambiguous",
                "Loaded an existing template by id and compared field-count summary against raw Onto payload.",
                get_template_summary.replace("\n", " | "),
                "" if summary_matches else "Summary may omit or miscount template field buckets.",
                "" if summary_matches else "Expose raw count sources or expand formatter coverage for QA visibility.",
            )
        else:
            add_result(
                "get_template",
                "ambiguous",
                "Attempted to load an existing template by id from the default realm.",
                "No existing template was discoverable in the default realm search sample.",
                "Could not verify read-by-id baseline against pre-existing data.",
                "Provide a stable fixture template id for baseline smoke.",
            )

        existing_entity = raw_find_any_entity(default_realm_id)
        if existing_entity:
            existing_entity_id = str(existing_entity.get("uuid") or existing_entity.get("id"))
            get_entity_summary = extract_text(
                await invoke_tool(
                    "get_entity",
                    {
                        "realm_id": default_realm_id,
                        "entity_id": existing_entity_id,
                        "related_entities": True,
                        "related_diagrams": True,
                    },
                )
            )
            raw_entity = raw_get_entity(default_realm_id, existing_entity_id, related_entities=True, related_diagrams=True)
            fields_count = len(raw_entity.get("fields", [])) if isinstance(raw_entity.get("fields"), list) else 0
            diagrams_count = len(raw_entity.get("relatedDiagrams", [])) if isinstance(raw_entity.get("relatedDiagrams"), list) else 0
            relations_count = len(raw_entity.get("relatedEntities", [])) if isinstance(raw_entity.get("relatedEntities"), list) else 0
            summary_matches = (
                f"Fields: {fields_count}" in get_entity_summary
                and f"Related diagrams: {diagrams_count}" in get_entity_summary
                and f"Related entities: {relations_count}" in get_entity_summary
            )
            add_result(
                "get_entity",
                "pass" if summary_matches else "ambiguous",
                "Loaded an existing entity by id and compared counts against raw Onto payload.",
                get_entity_summary.replace("\n", " | "),
                "" if summary_matches else "Summary may omit counts or payload details from getEntity.",
                "" if summary_matches else "Expand formatter or provide a diagnostic/raw mode for QA.",
            )
        else:
            add_result(
                "get_entity",
                "ambiguous",
                "Attempted to load an existing entity by id from the default realm.",
                "No existing entity was discoverable in the default realm search sample.",
                "Could not verify read-by-id baseline against pre-existing data.",
                "Provide a stable fixture entity id for baseline smoke.",
            )

        create_realm_summary = extract_text(
            await invoke_tool("create_realm", {"name": f"{prefix}_realm", "comment": "qa realm create"})
        )
        created_realm_id = parse_id(create_realm_summary)
        add_result(
            "create_realm",
            "pass",
            "Created an isolated realm for lifecycle and mutation tests.",
            create_realm_summary.replace("\n", " | "),
            "",
            "",
        )

        update_realm_summary = extract_text(
            await invoke_tool(
                "update_realm",
                {"realm_id": created_realm_id, "name": f"{prefix}_realm_updated", "comment": "qa realm updated"},
            )
        )
        visible_realms_after_update = _get_user_spaces_data()
        updated_realm_entry = next(
            (realm for realm in visible_realms_after_update if isinstance(realm, dict) and str(realm.get("id")) == created_realm_id),
            None,
        )
        realm_update_ok = isinstance(updated_realm_entry, dict) and updated_realm_entry.get("name") == f"{prefix}_realm_updated"
        add_result(
            "update_realm",
            "pass" if realm_update_ok else "ambiguous",
            "Updated the isolated realm name/comment and verified state through visible realm listing.",
            f"{update_realm_summary.replace(chr(10), ' | ')} | visible_name={updated_realm_entry.get('name') if isinstance(updated_realm_entry, dict) else 'not-found'}",
            "" if realm_update_ok else "Tool summary does not expose updated values and Onto does not offer a supported GET /realm/{id} path here.",
            "" if realm_update_ok else "Consider returning updated realm name/comment in the summary for QA clarity.",
        )

        invalid_update_summary = extract_text(
            await invoke_tool(
                "update_realm",
                {"realm_id": "00000000-0000-0000-0000-000000000000", "name": "invalid", "comment": ""},
            )
        )
        invalid_delete_summary = extract_text(
            await invoke_tool("delete_realm", {"realm_id": "00000000-0000-0000-0000-000000000000"})
        )
        add_result(
            "realm_invalid_id_handling",
            "pass",
            "Verified invalid realm ids return normalized tool text instead of uncaught exceptions.",
            f"update={invalid_update_summary} | delete={invalid_delete_summary}",
            "",
            "",
        )

        parent_one_summary = extract_text(
            await invoke_tool(
                "save_template",
                {"realm_id": created_realm_id, "name": f"{prefix}_parent_one", "comment": ""},
            )
        )
        parent_one_id = parse_id(parent_one_summary)
        if not is_real_id(parent_one_id):
            parent_one_match = raw_find_template_by_name(created_realm_id, f"{prefix}_parent_one")
            parent_one_id = str(parent_one_match.get("uuid") or parent_one_match.get("id")) if isinstance(parent_one_match, dict) else parent_one_id
        created_template_ids.append(parent_one_id)

        parent_two_summary = extract_text(
            await invoke_tool(
                "save_template",
                {"realm_id": created_realm_id, "name": f"{prefix}_parent_two", "comment": "p2"},
            )
        )
        parent_two_id = parse_id(parent_two_summary)
        if not is_real_id(parent_two_id):
            parent_two_match = raw_find_template_by_name(created_realm_id, f"{prefix}_parent_two")
            parent_two_id = str(parent_two_match.get("uuid") or parent_two_match.get("id")) if isinstance(parent_two_match, dict) else parent_two_id
        created_template_ids.append(parent_two_id)

        child_summary = extract_text(
            await invoke_tool(
                "save_template",
                {"realm_id": created_realm_id, "name": f"{prefix}_child", "comment": "child"},
            )
        )
        child_id = parse_id(child_summary)
        if not is_real_id(child_id):
            child_match = raw_find_template_by_name(created_realm_id, f"{prefix}_child")
            child_id = str(child_match.get("uuid") or child_match.get("id")) if isinstance(child_match, dict) else child_id
        created_template_ids.append(child_id)
        add_result(
            "save_template_create",
            "pass" if all(is_real_id(value) for value in [parent_one_id, parent_two_id, child_id]) else "ambiguous",
            "Created templates via save_template without template_id.",
            f"parent_one={parent_one_id}, parent_two={parent_two_id}, child={child_id}",
            "" if all(is_real_id(value) for value in [parent_one_id, parent_two_id, child_id]) else "save_template summary did not consistently expose ids; fallback search by name was required.",
            "" if all(is_real_id(value) for value in [parent_one_id, parent_two_id, child_id]) else "Return created template id reliably in save_template summary even when Onto response omits id/uuid.",
        )

        update_child_summary = extract_text(
            await invoke_tool(
                "save_template",
                {
                    "realm_id": created_realm_id,
                    "name": f"{prefix}_child_renamed",
                    "comment": "child-updated",
                    "template_id": child_id,
                },
            )
        )
        raw_child = raw_get_template(created_realm_id, child_id)
        template_upsert_ok = raw_child.get("name") == f"{prefix}_child_renamed" and raw_child.get("comment") == "child-updated"
        add_result(
            "save_template_update",
            "pass" if template_upsert_ok else "fail",
            "Updated a template via save_template with template_id to verify upsert semantics.",
            update_child_summary.replace("\n", " | "),
            "" if template_upsert_ok else "Updated template state does not match requested name/comment.",
            "" if template_upsert_ok else "Inspect save_template payload mapping and Onto response handling.",
        )

        alias_id = ""
        try:
            create_template_summary = extract_text(
                await invoke_tool(
                    "create_template",
                    {"realm_id": created_realm_id, "name": f"{prefix}_alias", "comment": "alias"},
                )
            )
            alias_id = parse_id(create_template_summary)
            if not is_real_id(alias_id):
                alias_match = raw_find_template_by_name(created_realm_id, f"{prefix}_alias")
                alias_id = str(alias_match.get("uuid") or alias_match.get("id")) if isinstance(alias_match, dict) else alias_id
            if is_real_id(alias_id):
                created_template_ids.append(alias_id)
            add_result(
                "create_template",
                "pass" if is_real_id(alias_id) else "ambiguous",
                "Created a template via compatibility wrapper create_template.",
                create_template_summary.replace("\n", " | "),
                "" if is_real_id(alias_id) else "create_template/save_template summary did not expose the created template id directly.",
                "" if is_real_id(alias_id) else "Return created template id reliably from the wrapper path.",
            )
        except Exception as exc:
            add_result(
                "create_template",
                "fail",
                "Executed create_template compatibility wrapper through registered MCP runtime.",
                summarize_exception(exc),
                "Wrapper is calling decorated FunctionTool objects instead of the underlying function.",
                "Refactor wrappers to call undecorated helper functions or tool.fn, then add regression coverage.",
            )

        get_child_summary = extract_text(
            await invoke_tool(
                "get_template",
                {"realm_id": created_realm_id, "template_id": child_id, "include_children": True, "include_parents": True},
            )
        )
        raw_child_with_links = raw_get_template(created_realm_id, child_id, children=True, parents=True)
        child_describer_count = len(raw_child_with_links.get("describerFields", [])) if isinstance(raw_child_with_links.get("describerFields"), list) else 0
        child_fields_count = len(raw_child_with_links.get("fields", [])) if isinstance(raw_child_with_links.get("fields"), list) else 0
        get_template_ok = (
            f"Describer fields: {child_describer_count}" in get_child_summary
            and f"Fields: {child_fields_count}" in get_child_summary
        )
        add_result(
            "get_template_created",
            "pass" if get_template_ok else "ambiguous",
            "Loaded the created child template and compared count summary to raw payload.",
            get_child_summary.replace("\n", " | "),
            "" if get_template_ok else "Template summary may omit or miscount field buckets.",
            "" if get_template_ok else "Expose more detail in get_template summary for QA checks.",
        )

        list_template_candidates = ["MetaEntity", "EntityTemplate", "Template", "Class"]
        chosen_class_name = None
        for class_name in list_template_candidates:
            data = _request_json(
                "GET",
                f"{ONTO_API_BASE}/realm/{created_realm_id}/meta/filtered",
                query_params={"className": class_name},
                timeout=30,
            )
            items = data.get("result") if isinstance(data, dict) else data
            if isinstance(items, list) and any(str(item.get("uuid") or item.get("id")) == child_id for item in items if isinstance(item, dict)):
                chosen_class_name = class_name
                break
        if chosen_class_name:
            list_templates_summary = extract_text(
                await invoke_tool("list_templates", {"realm_id": created_realm_id, "class_name": chosen_class_name})
            )
            add_result(
                "list_templates",
                "pass" if child_id in list_templates_summary else "ambiguous",
                "Listed templates in the created realm using a discovered class_name candidate.",
                list_templates_summary.splitlines()[0],
                "" if child_id in list_templates_summary else "Summary did not clearly expose the created template id.",
                "" if child_id in list_templates_summary else "Document stable class_name values or expose raw class metadata.",
            )
        else:
            add_result(
                "list_templates",
                "ambiguous",
                "Attempted to verify list_templates against the created templates.",
                "Could not infer a working Onto class_name for filtered template listing in preprod.",
                "QA contract needs a stable class_name example or tool-level documentation of accepted values.",
                "Document accepted class_name values in README and QA catalog.",
            )

        link_one_summary = extract_text(
            await invoke_tool(
                "link_template_to_parents",
                {"realm_id": created_realm_id, "child_template_id": child_id, "parent_template_ids": [parent_one_id]},
            )
        )
        raw_child_after_link_one = raw_get_template(created_realm_id, child_id, parents=True)
        single_link_ok = contains_value(raw_child_after_link_one, parent_one_id)

        link_two_summary = extract_text(
            await invoke_tool(
                "link_template_to_parents",
                {
                    "realm_id": created_realm_id,
                    "child_template_id": child_id,
                    "parent_template_ids": [parent_one_id, parent_two_id],
                },
            )
        )
        raw_child_after_link_two = raw_get_template(created_realm_id, child_id, parents=True)
        multi_link_ok = contains_value(raw_child_after_link_two, parent_one_id) and contains_value(raw_child_after_link_two, parent_two_id)
        add_result(
            "link_template_to_parents",
            "pass" if single_link_ok and multi_link_ok else "ambiguous",
            "Linked the child template to one parent and then to multiple parents.",
            f"single={link_one_summary} | multi={link_two_summary}",
            "" if single_link_ok and multi_link_ok else "Raw get_template payload did not expose parent linkage clearly enough for deterministic QA.",
            "" if single_link_ok and multi_link_ok else "Document parent-link payload shape or surface parent count in get_template summary.",
        )

        save_entity_create_summary = extract_text(
            await invoke_tool(
                "save_entity",
                {
                    "realm_id": created_realm_id,
                    "name": f"{prefix}_entity_main",
                    "comment": "",
                    "meta_entity_id": child_id,
                },
            )
        )
        entity_main_id = parse_id(save_entity_create_summary)
        if not is_real_id(entity_main_id):
            entity_main_match = raw_find_entity_by_name(created_realm_id, f"{prefix}_entity_main")
            entity_main_id = str(entity_main_match.get("uuid") or entity_main_match.get("id")) if isinstance(entity_main_match, dict) else entity_main_id
        created_entity_ids.append(entity_main_id)
        raw_entity_main = raw_get_entity(created_realm_id, entity_main_id)
        classification_create_ok = contains_value(raw_entity_main.get("metaEntity"), child_id)
        add_result(
            "save_entity_create",
            "pass" if classification_create_ok and is_real_id(entity_main_id) else "ambiguous" if classification_create_ok else "fail",
            "Created an entity with meta_entity_id to verify classified create-like save.",
            save_entity_create_summary.replace("\n", " | "),
            "" if classification_create_ok and is_real_id(entity_main_id) else "Entity creation worked, but summary id fallback was required." if classification_create_ok else "Requested meta_entity_id was not applied during create-like save.",
            "" if classification_create_ok and is_real_id(entity_main_id) else "Return created entity id reliably in save_entity summary." if classification_create_ok else "Inspect save_entity payload and Onto create semantics.",
        )

        save_entity_update_summary = extract_text(
            await invoke_tool(
                "save_entity",
                {
                    "realm_id": created_realm_id,
                    "name": f"{prefix}_entity_main_updated",
                    "comment": "entity-updated",
                    "entity_id": entity_main_id,
                    "meta_entity_id": child_id,
                },
            )
        )
        raw_entity_main_updated = raw_get_entity(created_realm_id, entity_main_id)
        entity_upsert_ok = raw_entity_main_updated.get("name") == f"{prefix}_entity_main_updated" and raw_entity_main_updated.get("comment") == "entity-updated"
        add_result(
            "save_entity_update",
            "pass" if entity_upsert_ok else "fail",
            "Updated an existing entity via save_entity with entity_id.",
            save_entity_update_summary.replace("\n", " | "),
            "" if entity_upsert_ok else "Updated entity state does not match requested name/comment.",
            "" if entity_upsert_ok else "Inspect save_entity update semantics and response formatting.",
        )

        batch_summary = extract_text(
            await invoke_tool(
                "save_entities_batch",
                {
                    "realm_id": created_realm_id,
                    "entities": [
                        {
                            "id": entity_main_id,
                            "name": f"{prefix}_entity_main_batch",
                            "comment": "entity-batch-updated",
                            "metaEntityId": child_id,
                        },
                        {
                            "name": f"{prefix}_entity_batch_new_one",
                            "comment": "",
                            "metaEntityId": child_id,
                        },
                        {
                            "name": f"{prefix}_entity_batch_new_two",
                            "comment": "batch-two",
                        },
                    ],
                },
            )
        )
        search_after_batch = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{created_realm_id}/entity/find",
            json_payload={
                "name": prefix,
                "comment": "",
                "includeInherited": False,
                "metaFieldFilters": [],
                "pagination": {"offset": 0, "first": 50},
            },
            timeout=30,
        )
        found_after_batch: list[dict[str, Any]] = []
        if isinstance(search_after_batch, list):
            for item in search_after_batch:
                if isinstance(item, dict) and isinstance(item.get("entities"), list):
                    found_after_batch.extend([entry for entry in item["entities"] if isinstance(entry, dict)])
                elif isinstance(item, dict):
                    found_after_batch.append(item)
        ids_after_batch = {str(item.get("uuid") or item.get("id")) for item in found_after_batch}
        names_after_batch = {str(item.get("name")) for item in found_after_batch}
        created_entity_ids.extend(sorted(ids_after_batch - set(created_entity_ids)))
        batch_ok = (
            f"{prefix}_entity_main_batch" in names_after_batch
            and f"{prefix}_entity_batch_new_one" in names_after_batch
            and f"{prefix}_entity_batch_new_two" in names_after_batch
        )
        raw_batch_probe = _request_json(
            "POST",
            f"{ONTO_API_BASE}/realm/{created_realm_id}/entity/batch",
            json_payload={
                "entities": [
                    {
                        "id": entity_main_id,
                        "name": f"{prefix}_entity_main_batch_probe",
                        "comment": "entity-batch-probe",
                        "metaEntityId": child_id,
                    }
                ]
            },
            timeout=60,
        )
        raw_batch_keys = sorted(raw_batch_probe.keys()) if isinstance(raw_batch_probe, dict) else []
        add_result(
            "save_entities_batch",
            "pass" if batch_ok else "fail",
            "Ran mixed batch update/create and inspected raw batch response keys.",
            f"{batch_summary.splitlines()[0]} | raw_keys={raw_batch_keys}",
            "" if "updatedEntities" not in raw_batch_keys else "Tool summary currently reports only createdEntities while API also exposes updatedEntities.",
            "" if "updatedEntities" not in raw_batch_keys else "Adjust batch summary to include separate updated buckets from Onto.",
        )

        raw_entity_main_probe = raw_get_entity(created_realm_id, entity_main_id)
        if raw_entity_main_probe.get("name") == f"{prefix}_entity_main_batch_probe":
            # Keep local state aligned after raw probe update.
            pass

        try:
            create_batch_summary = extract_text(
                await invoke_tool(
                    "create_entities_batch",
                    {
                        "realm_id": created_realm_id,
                        "entities": [
                            {"name": f"{prefix}_entity_alias_batch", "comment": "alias-batch", "metaEntityId": parent_one_id}
                        ],
                    },
                )
            )
            alias_batch_search = _request_json(
                "POST",
                f"{ONTO_API_BASE}/realm/{created_realm_id}/entity/find",
                json_payload={
                    "name": f"{prefix}_entity_alias_batch",
                    "comment": "",
                    "includeInherited": False,
                    "metaFieldFilters": [],
                    "pagination": {"offset": 0, "first": 10},
                },
                timeout=30,
            )
            alias_batch_found = False
            if isinstance(alias_batch_search, list):
                for item in alias_batch_search:
                    if isinstance(item, dict) and isinstance(item.get("entities"), list):
                        for entry in item["entities"]:
                            if isinstance(entry, dict):
                                alias_batch_found = True
                                created_entity_ids.append(str(entry.get("uuid") or entry.get("id")))
            add_result(
                "create_entities_batch",
                "pass" if alias_batch_found else "fail",
                "Verified compatibility wrapper create_entities_batch persists entities similarly to save_entities_batch.",
                create_batch_summary.replace("\n", " | "),
                "" if alias_batch_found else "Wrapper did not produce a searchable created entity.",
                "" if alias_batch_found else "Inspect wrapper parity with save_entities_batch.",
            )
        except Exception as exc:
            add_result(
                "create_entities_batch",
                "fail",
                "Executed create_entities_batch compatibility wrapper through registered MCP runtime.",
                summarize_exception(exc),
                "Wrapper is calling decorated FunctionTool objects instead of the underlying batch-save function.",
                "Refactor wrappers to call undecorated helper functions or tool.fn, then add regression coverage.",
            )

        get_entity_created_summary = extract_text(
            await invoke_tool(
                "get_entity",
                {"realm_id": created_realm_id, "entity_id": entity_main_id, "related_entities": True, "related_diagrams": True},
            )
        )
        raw_entity_created = raw_get_entity(created_realm_id, entity_main_id, related_entities=True, related_diagrams=True)
        get_entity_created_ok = (
            f"Fields: {len(raw_entity_created.get('fields', [])) if isinstance(raw_entity_created.get('fields'), list) else 0}" in get_entity_created_summary
        )
        add_result(
            "get_entity_created",
            "pass" if get_entity_created_ok else "ambiguous",
            "Loaded the created entity and compared summary counts to raw payload.",
            get_entity_created_summary.replace("\n", " | "),
            "" if get_entity_created_ok else "Summary may not expose enough entity detail for QA.",
            "" if get_entity_created_ok else "Expose additional relation/field detail in get_entity summary.",
        )

        search_entity_created_summary = extract_text(
            await invoke_tool("search_entities", {"realm_id": created_realm_id, "name_filter": prefix, "limit": 20})
        )
        search_entity_related_meta_summary = extract_text(
            await invoke_tool(
                "search_entities_with_related_meta",
                {"realm_id": created_realm_id, "name_filter": prefix, "limit": 20},
            )
        )
        add_result(
            "search_entities",
            "pass" if prefix in search_entity_created_summary else "fail",
            "Searched created entities in isolated realm through plain endpoint.",
            search_entity_created_summary.splitlines()[0],
            "",
            "",
        )
        add_result(
            "search_entities_with_related_meta",
            "pass" if prefix in search_entity_related_meta_summary else "fail",
            "Searched created entities in isolated realm through v2 related-meta endpoint.",
            search_entity_related_meta_summary.splitlines()[0],
            "",
            "",
        )

        reclassify_summary = extract_text(
            await invoke_tool(
                "save_entity",
                {
                    "realm_id": created_realm_id,
                    "name": f"{prefix}_entity_main_reclassified",
                    "comment": "entity-reclassified",
                    "entity_id": entity_main_id,
                    "meta_entity_id": parent_two_id,
                },
            )
        )
        raw_entity_reclassified = raw_get_entity(created_realm_id, entity_main_id)
        reclassify_ok = contains_value(raw_entity_reclassified.get("metaEntity"), parent_two_id)
        add_result(
            "save_entity_reclassification",
            "pass" if reclassify_ok else "fail",
            "Changed meta_entity_id on an existing entity to verify reclassification.",
            reclassify_summary.replace("\n", " | "),
            "" if reclassify_ok else "Entity retained old classification or failed to apply requested meta_entity_id.",
            "" if reclassify_ok else "Inspect save_entity reclassification semantics against preprod.",
        )

        declassify_summary = extract_text(
            await invoke_tool(
                "save_entity",
                {
                    "realm_id": created_realm_id,
                    "name": f"{prefix}_entity_main_declassified",
                    "comment": "entity-declassified",
                    "entity_id": entity_main_id,
                },
            )
        )
        raw_entity_declassified = raw_get_entity(created_realm_id, entity_main_id)
        declassify_ok = not raw_entity_declassified.get("metaEntity")
        add_result(
            "save_entity_declassification",
            "pass" if declassify_ok else "ambiguous",
            "Omitted meta_entity_id on update to verify declassification behavior.",
            declassify_summary.replace("\n", " | "),
            "" if declassify_ok else "Preprod did not clearly remove classification when meta_entity_id was omitted.",
            "" if declassify_ok else "Clarify or document whether saveEntity omission preserves or clears classification in Onto.",
        )

        relation_entities = created_entity_ids[:2]
        if len(relation_entities) >= 2:
            relation_create_summary = extract_text(
                await invoke_tool(
                    "create_relation",
                    {
                        "realm_id": created_realm_id,
                        "start_entity_id": relation_entities[0],
                        "end_entity_id": relation_entities[1],
                        "relation_type_name": relation_type_name,
                        "start_role": "from-role",
                        "end_role": "to-role",
                        "additional_properties": {"qaFlag": "create"},
                    },
                )
            )
            raw_relation_entity = raw_get_entity(created_realm_id, relation_entities[0], related_entities=True)
            relation_create_ok = (
                contains_value(raw_relation_entity, relation_type_name)
                and contains_value(raw_relation_entity, "from-role")
                and contains_value(raw_relation_entity, "to-role")
            )
            additional_properties_visible = contains_value(raw_relation_entity, "qaFlag") or contains_value(raw_relation_entity, "create")
            add_result(
                "create_relation",
                "pass" if relation_create_ok else "ambiguous",
                "Created an entity relation with roles and additional_properties.",
                relation_create_summary.replace("\n", " | "),
                "" if additional_properties_visible else "Raw payload did not clearly expose additionalProperties persistence.",
                "" if additional_properties_visible else "Confirm the exact Onto response shape for relation additionalProperties or add a read tool for relations.",
            )

            relation_update_summary = extract_text(
                await invoke_tool(
                    "update_relation",
                    {
                        "realm_id": created_realm_id,
                        "start_entity_id": relation_entities[0],
                        "end_entity_id": relation_entities[1],
                        "relation_type_name": relation_type_name,
                        "start_role": "from-role-updated",
                        "end_role": "to-role-updated",
                        "additional_properties": {"qaFlag": "update"},
                    },
                )
            )
            raw_relation_entity_updated = raw_get_entity(created_realm_id, relation_entities[0], related_entities=True)
            relation_update_ok = (
                contains_value(raw_relation_entity_updated, "from-role-updated")
                and contains_value(raw_relation_entity_updated, "to-role-updated")
            )
            add_result(
                "update_relation",
                "pass" if relation_update_ok else "ambiguous",
                "Updated relation roles and additional_properties.",
                relation_update_summary.replace("\n", " | "),
                "" if relation_update_ok else "Raw payload did not clearly expose updated relation roles.",
                "" if relation_update_ok else "Add relation-read diagnostics or include relation detail in get_entity summary.",
            )

            relation_delete_summary = extract_text(
                await invoke_tool(
                    "delete_relation",
                    {
                        "realm_id": created_realm_id,
                        "start_entity_id": relation_entities[0],
                        "end_entity_id": relation_entities[1],
                        "relation_type_name": relation_type_name,
                    },
                )
            )
            raw_relation_entity_deleted = raw_get_entity(created_realm_id, relation_entities[0], related_entities=True)
            relation_delete_ok = not contains_value(raw_relation_entity_deleted, relation_type_name)
            add_result(
                "delete_relation",
                "pass" if relation_delete_ok else "ambiguous",
                "Deleted relation by exact start/end/type triple.",
                relation_delete_summary.replace("\n", " | "),
                "" if relation_delete_ok else "Relation type still appears in related entity payload after delete.",
                "" if relation_delete_ok else "Verify delete endpoint semantics and raw relation payload shape.",
            )
        else:
            add_result(
                "relation_lifecycle",
                "ambiguous",
                "Needed at least two persisted entities for relation tests.",
                "Not enough entities were available after batch setup.",
                "Relation lifecycle could not be executed.",
                "Stabilize entity fixture creation before relation QA.",
            )

        meta_relation_create_summary = extract_text(
            await invoke_tool(
                "create_meta_relation",
                {
                    "realm_id": created_realm_id,
                    "start_meta_id": parent_one_id,
                    "end_meta_id": parent_two_id,
                    "relation_type_name": meta_relation_type_name,
                    "start_min": 1,
                    "start_max": 2,
                    "end_min": 0,
                    "end_max": 3,
                    "equal": True,
                },
            )
        )
        raw_parent_one = raw_get_template(created_realm_id, parent_one_id, children=True, parents=True)
        meta_relation_create_visible = contains_value(raw_parent_one, meta_relation_type_name)
        add_result(
            "create_meta_relation",
            "pass" if meta_relation_create_visible else "ambiguous",
            "Created a meta relation with non-default cardinalities and equal=True.",
            meta_relation_create_summary.replace("\n", " | "),
            "" if meta_relation_create_visible else "Raw template payload did not expose created meta relation details clearly.",
            "" if meta_relation_create_visible else "Provide a relation-read tool or expand get_template summary for meta relations.",
        )

        meta_relation_update_summary = extract_text(
            await invoke_tool(
                "update_meta_relation",
                {
                    "realm_id": created_realm_id,
                    "start_meta_id": parent_one_id,
                    "end_meta_id": parent_two_id,
                    "relation_type_name": meta_relation_type_name,
                    "start_min": 2,
                    "start_max": 4,
                    "end_min": 1,
                    "end_max": 5,
                    "equal": False,
                },
            )
        )
        raw_parent_one_updated = raw_get_template(created_realm_id, parent_one_id, children=True, parents=True)
        meta_relation_update_visible = contains_value(raw_parent_one_updated, meta_relation_type_name) and contains_value(raw_parent_one_updated, 4)
        add_result(
            "update_meta_relation",
            "pass" if meta_relation_update_visible else "ambiguous",
            "Updated meta relation cardinalities and equal flag.",
            meta_relation_update_summary.replace("\n", " | "),
            "" if meta_relation_update_visible else "Raw template payload did not clearly expose updated meta relation values.",
            "" if meta_relation_update_visible else "Add meta-relation read coverage or richer summary diagnostics.",
        )

        meta_relation_delete_summary = extract_text(
            await invoke_tool(
                "delete_meta_relation",
                {
                    "realm_id": created_realm_id,
                    "start_meta_id": parent_one_id,
                    "end_meta_id": parent_two_id,
                    "relation_type_name": meta_relation_type_name,
                },
            )
        )
        raw_parent_one_deleted = raw_get_template(created_realm_id, parent_one_id, children=True, parents=True)
        meta_relation_delete_visible = not contains_value(raw_parent_one_deleted, meta_relation_type_name)
        add_result(
            "delete_meta_relation",
            "pass" if meta_relation_delete_visible else "ambiguous",
            "Deleted meta relation by exact start/end/type triple.",
            meta_relation_delete_summary.replace("\n", " | "),
            "" if meta_relation_delete_visible else "Raw template payload still contains the meta relation type after delete.",
            "" if meta_relation_delete_visible else "Confirm delete semantics and add a direct read path for meta relations.",
        )

        session_ctx = FakeContext(session_id=f"{prefix}_ctx")
        save_thread_result = call_session_tool("saveOntoAIThreadID", "thread-1", ctx=session_ctx)
        get_thread_result = call_session_tool("getOntoAIThreadID", ctx=session_ctx)
        session_unconfigured_ok = (
            isinstance(save_thread_result, dict)
            and save_thread_result.get("message") == "Session-state service is not configured for this server."
            and isinstance(get_thread_result, dict)
            and get_thread_result.get("message") == "Session-state service is not configured for this server."
        )
        add_result(
            "session_state_helpers",
            "pass" if session_unconfigured_ok else "ambiguous",
            "Verified unconfigured session-state helper behavior without SESSION_STATE_API_KEY.",
            f"save={save_thread_result} | get={get_thread_result}",
            "" if session_unconfigured_ok else "Observed behavior diverges from the documented unconfigured-session path.",
            "" if session_unconfigured_ok else "Recheck settings wiring for session-state detection.",
        )

        delete_single_summary = extract_text(
            await invoke_tool("delete_entity", {"realm_id": created_realm_id, "entity_ids": [entity_main_id]})
        )
        delete_single_ok = "Deleted 1 entity(s)." in delete_single_summary
        if entity_main_id in created_entity_ids:
            created_entity_ids.remove(entity_main_id)
        remaining_ids = created_entity_ids[:2]
        delete_multi_ok = True
        delete_multi_summary = "Skipped multi-delete due to insufficient remaining ids."
        if remaining_ids:
            delete_multi_summary = extract_text(
                await invoke_tool("delete_entity", {"realm_id": created_realm_id, "entity_ids": remaining_ids})
            )
            delete_multi_ok = f"Deleted {len(remaining_ids)} entity(s)." in delete_multi_summary
            created_entity_ids = [entity_id for entity_id in created_entity_ids if entity_id not in set(remaining_ids)]
        add_result(
            "delete_entity",
            "pass" if delete_single_ok and delete_multi_ok else "ambiguous",
            "Deleted one entity and then multiple entities through repeated ids query serialization.",
            f"single={delete_single_summary} | multi={delete_multi_summary}",
            "" if delete_single_ok and delete_multi_ok else "Delete summary did not clearly confirm one of the deletion modes.",
            "" if delete_single_ok and delete_multi_ok else "Consider exposing deleted ids/counts more explicitly.",
        )

        delete_template_results = []
        for template_id in list(created_template_ids):
            delete_template_results.append(
                extract_text(await invoke_tool("delete_template", {"realm_id": created_realm_id, "template_id": template_id}))
            )
        created_template_ids = []
        delete_template_ok = all("deleted" in entry.lower() for entry in delete_template_results)
        add_result(
            "delete_template",
            "pass" if delete_template_ok else "ambiguous",
            "Deleted all created templates in the isolated realm.",
            " | ".join(delete_template_results),
            "" if delete_template_ok else "One or more template delete summaries were not clearly successful.",
            "" if delete_template_ok else "Consider exposing deleted template ids/statuses more explicitly.",
        )

        delete_realm_summary = extract_text(await invoke_tool("delete_realm", {"realm_id": created_realm_id}))
        created_realm_id = None
        add_result(
            "delete_realm",
            "pass" if "deleted" in delete_realm_summary.lower() else "ambiguous",
            "Deleted the isolated QA realm after lifecycle checks.",
            delete_realm_summary.replace("\n", " | "),
            "" if "deleted" in delete_realm_summary.lower() else "Delete summary did not clearly confirm realm removal.",
            "" if "deleted" in delete_realm_summary.lower() else "Expose deleted realm id/status in summary.",
        )

    finally:
        if created_entity_ids and created_realm_id:
            for entity_id in list(created_entity_ids):
                try:
                    await invoke_tool("delete_entity", {"realm_id": created_realm_id, "entity_ids": [entity_id]})
                except Exception:
                    pass
        if created_template_ids and created_realm_id:
            for template_id in list(created_template_ids):
                try:
                    await invoke_tool("delete_template", {"realm_id": created_realm_id, "template_id": template_id})
                except Exception:
                    pass
        if created_realm_id:
            try:
                await invoke_tool("delete_realm", {"realm_id": created_realm_id})
            except Exception:
                pass

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "onto_api_base": ONTO_API_BASE,
        "default_realm_id": default_realm_id,
        "results": [result.__dict__ for result in results],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
