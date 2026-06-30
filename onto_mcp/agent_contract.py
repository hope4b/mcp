from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path(__file__).with_name("agent_contract.json")

_DESTRUCTIVE_RE = re.compile(r"\b(delete|destroy|remove permanently)\b", re.IGNORECASE)
_LIFECYCLE_RE = re.compile(r"\b(submit|accept|approve|revoke|supersede|transition|status)\b", re.IGNORECASE)
_WRITE_RE = re.compile(r"\b(create|update|save|write|draft|link|unlink|add|remove|append|manage)\b", re.IGNORECASE)
_CONFIRMATION_RE = re.compile(r"\b(confirm|confirmed|explicit|operator intent|approved|approval)\b", re.IGNORECASE)
_REQUIREMENT_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9_]*(?:_ids|_id)\b", re.IGNORECASE)
_NAMED_REQUIREMENT_VALUE_RE = re.compile(
    r"\b(?P<name>[a-z][a-z0-9_]*(?:_ids|_id))\b\s*(?:=|:|is)?\s*(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)
_ROUTE_DIRECTIVE_RE = re.compile(r"\broute\s*:\s*(?P<route>[a-z][a-z0-9_-]*)\b", re.IGNORECASE)
_SCOPE_GLOSSARY_RE = re.compile(
    r"(\bwhat\s+is\s+(?:an?\s+)?ontology\b|\bdefine\s+ontology\b|\bontology\s+definition\b|"
    r"\b\u0447\u0442\u043e\s+\u0442\u0430\u043a\u043e\u0435\s+\u043e\u043d\u0442\u043e\u043b\u043e\u0433)",
    re.IGNORECASE,
)
_PUBLIC_ROUTE_ALIASES = {
    "memory": "memory",
    "memory_artifact": "memory",
    "memoryartifact": "memory",
    "agent_memory": "memory",
}


@lru_cache(maxsize=1)
def load_agent_contract() -> dict[str, Any]:
    with CONTRACT_PATH.open(encoding="utf-8") as contract_file:
        return json.load(contract_file)


def get_agent_contract() -> dict[str, Any]:
    """Return a copy so callers cannot mutate the cached contract."""
    return copy.deepcopy(load_agent_contract())


def build_how_to_response(question: str = "", safety_mode: str = "read_only") -> dict[str, Any]:
    contract = load_agent_contract()
    normalized_question = (question or "").strip()
    effective_safety_mode = _normalize_safety_mode(contract, safety_mode)

    if _is_scope_glossary_prompt(normalized_question):
        return _scope_guard_response(effective_safety_mode)

    if not normalized_question:
        return _general_onboarding_response(contract, effective_safety_mode)

    matched_task_classes = _match_task_classes(contract, normalized_question)
    if not matched_task_classes:
        return _unclear_response(contract, normalized_question, effective_safety_mode)

    if len(matched_task_classes) > 1:
        return _ambiguous_response(contract, matched_task_classes, effective_safety_mode)

    return _matched_route_response(
        contract=contract,
        task_class_name=matched_task_classes[0],
        question=normalized_question,
        effective_safety_mode=effective_safety_mode,
    )


def _normalize_safety_mode(contract: dict[str, Any], safety_mode: str) -> str:
    normalized = (safety_mode or "read_only").strip().lower().replace("-", "_")
    for mode_name, mode in contract["safety_modes"].items():
        aliases = {alias.replace("-", "_") for alias in mode.get("aliases", [])}
        if normalized == mode_name or normalized in aliases:
            return mode_name
    return "read_only"


def _match_task_classes(contract: dict[str, Any], question: str) -> list[str]:
    question_lower = question.lower()
    explicit_task_class = _explicit_task_class(contract, question_lower)
    if explicit_task_class:
        return [explicit_task_class]

    matches: list[str] = []
    for task_class_name, task_class in contract["task_classes"].items():
        keywords = task_class.get("keywords", [])
        if any(_keyword_matches(question_lower, keyword) for keyword in keywords):
            matches.append(task_class_name)
    if "object_search" in matches and _field_value_search_requested(question):
        return ["object_search"]
    return matches


def _explicit_task_class(contract: dict[str, Any], question_lower: str) -> str:
    match = _ROUTE_DIRECTIVE_RE.search(question_lower)
    if not match:
        return ""
    route_name = match.group("route").replace("-", "_")
    task_class_name = _PUBLIC_ROUTE_ALIASES.get(route_name, route_name)
    if task_class_name in contract["task_classes"]:
        return task_class_name
    return ""


def _keyword_matches(question_lower: str, keyword: str) -> bool:
    keyword_lower = keyword.lower()
    pattern = r"(?<![a-z0-9_])" + re.escape(keyword_lower) + r"(?![a-z0-9_])"
    return bool(re.search(pattern, question_lower))


def _is_scope_glossary_prompt(question: str) -> bool:
    return bool(question and _SCOPE_GLOSSARY_RE.search(question))


def _detect_intent(question: str) -> str:
    if _LIFECYCLE_RE.search(question):
        return "lifecycle"
    if _DESTRUCTIVE_RE.search(question):
        return "destructive"
    if _WRITE_RE.search(question):
        return "write"
    return "read"


def _has_confirmation(question: str) -> bool:
    return bool(_CONFIRMATION_RE.search(question))


def _scope_guard_response(effective_safety_mode: str) -> dict[str, Any]:
    return {
        "answer": (
            "This tool routes actionable Onto MCP work. It does not answer glossary or encyclopedia prompts. "
            "Ask for a concrete MCP goal such as finding an object, inspecting templates, updating a diagram, "
            "or planning a safe delete sequence."
        ),
        "next_calls": [],
        "clarifying_question": "What actionable Onto MCP task should I route, and what inputs are already known?",
        "avoid_tools": _all_mutating_tool_names(load_agent_contract()),
        "safety_notes": [
            f"Effective safety mode is {effective_safety_mode}.",
            "No Onto MCP tool sequence should be selected until the request is an operational MCP goal.",
        ],
    }


def _general_onboarding_response(contract: dict[str, Any], effective_safety_mode: str) -> dict[str, Any]:
    return {
        "answer": (
            "Use this as the first Onto MCP routing call. Provide the user's goal and known inputs; start with "
            "realm discovery before realm-scoped tools."
        ),
        "next_calls": [
            _next_call(
                1,
                "list_available_realms",
                "Discover accessible realms and choose the realm_id for the user's goal.",
            )
        ],
        "clarifying_question": "What Onto MCP goal should be routed, and which names or IDs are already known?",
        "avoid_tools": _all_mutating_tool_names(contract),
        "safety_notes": [
            f"Effective safety mode is {effective_safety_mode}.",
            "Keep write, destructive, lifecycle, admin-like, and high-risk tools out of next_calls until intent and required IDs are explicit.",
        ],
    }


def _unclear_response(contract: dict[str, Any], question: str, effective_safety_mode: str) -> dict[str, Any]:
    return {
        "answer": (
            "The request is not specific enough to choose an Onto MCP tool sequence. Safe discovery can start, "
            "but mutation or deletion must wait for a concrete goal."
        ),
        "next_calls": [
            _next_call(
                1,
                "list_available_realms",
                "Safe discovery of accessible realms while the actionable MCP goal is clarified.",
            )
        ],
        "clarifying_question": (
            "Which Onto MCP goal should be routed: find/read/update/delete templates, objects, diagrams, "
            "relations, memory artifacts, or workspace state?"
        ),
        "avoid_tools": _all_mutating_tool_names(contract),
        "safety_notes": [
            f"Effective safety mode is {effective_safety_mode}.",
            f"Do not invent a tool sequence for this unclear request: {question}",
        ],
    }


def _ambiguous_response(
    contract: dict[str, Any],
    matched_task_classes: list[str],
    effective_safety_mode: str,
) -> dict[str, Any]:
    candidate_families = _families_for_task_classes(contract, matched_task_classes)
    return {
        "answer": "The request matches more than one Onto MCP route. Use only safe discovery until the route is clarified.",
        "next_calls": [
            _next_call(
                1,
                "list_available_realms",
                "Discover accessible realms; this is safe before disambiguating the route.",
            )
        ],
        "clarifying_question": "Which route should be used: " + ", ".join(matched_task_classes) + "?",
        "avoid_tools": _blocked_tool_names(contract, candidate_families, effective_safety_mode, "", require_ids=True),
        "safety_notes": [
            f"Effective safety mode is {effective_safety_mode}.",
            "Ambiguous requests must not produce immediate write, destructive, lifecycle, admin-like, or high-risk next calls.",
        ],
    }


def _matched_route_response(
    *,
    contract: dict[str, Any],
    task_class_name: str,
    question: str,
    effective_safety_mode: str,
) -> dict[str, Any]:
    intent = _detect_intent(question)
    route = _route_for_task_class(task_class_name, question)
    family_names = contract["task_classes"][task_class_name]["families"]
    next_calls = route["next_calls"](question, effective_safety_mode, contract)
    avoid_tools = _blocked_tool_names(
        contract,
        family_names,
        effective_safety_mode,
        question,
        require_ids=intent in {"write", "destructive", "lifecycle"},
    )
    next_call_tools = {call["tool"] for call in next_calls}
    avoid_tools = [tool_name for tool_name in avoid_tools if tool_name not in next_call_tools]
    safety_notes = _route_safety_notes(
        contract=contract,
        route_name=route["name"],
        family_names=family_names,
        question=question,
        effective_safety_mode=effective_safety_mode,
        intent=intent,
        avoid_tools=avoid_tools,
    )

    response: dict[str, Any] = {
        "answer": route["answer"](effective_safety_mode),
        "next_calls": next_calls,
    }
    clarifying_question = route["clarifying_question"](question, effective_safety_mode)
    if clarifying_question:
        response["clarifying_question"] = clarifying_question
    if avoid_tools:
        response["avoid_tools"] = avoid_tools
    if safety_notes:
        response["safety_notes"] = safety_notes
    return response


def _route_for_task_class(task_class_name: str, question: str) -> dict[str, Any]:
    question_lower = question.lower()
    if task_class_name == "object_search":
        return {
            "name": "object_search",
            "next_calls": _object_search_next_calls,
            "answer": lambda mode: (
                "Start with realm discovery, then search objects/entities by the known name or filter."
            ),
            "clarifying_question": lambda _question, _mode: None,
        }
    if task_class_name == "diagram_work":
        if _DESTRUCTIVE_RE.search(question):
            return _diagram_delete_route()
        if "update" in question_lower or "edit" in question_lower or "rename" in question_lower:
            return _diagram_update_route()
        return _diagram_discovery_route()
    if task_class_name == "template_entity_modeling":
        if _DESTRUCTIVE_RE.search(question) and "template" in question_lower:
            return _template_delete_route()
        if "field" in question_lower:
            return _template_field_route()
        return _template_management_route()
    if task_class_name == "memory":
        return _memory_route()
    return _generic_route(task_class_name)


def _object_search_next_calls(question: str, _effective_safety_mode: str, _contract: dict[str, Any]) -> list[dict[str, Any]]:
    name_filter = _known_name_param(question, "object")
    if _field_value_search_requested(question):
        field_value = _named_input_value(question, "field_value") or _named_input_value(question, "value")
        field_id = _named_input_value(question, "field_id")
        field_filters = [{"field_id": field_id, "value": field_value}] if field_id and field_value else None
        return [
            _next_call(1, "list_available_realms", "Discover the realm_id to search in."),
            _next_call(
                2,
                "search_templates",
                "Find the relevant template so get_template can expose field ids for field-value lookup.",
                missing_args=[_missing_arg("realm_id", "list_available_realms")],
            ),
            _next_call(
                3,
                "get_template",
                "Inspect the relevant template to obtain the field_id for the requested field name, such as INN or OGRN.",
                missing_args=[
                    _missing_arg("realm_id", "list_available_realms"),
                    _missing_arg("template_id", "search_templates"),
                ],
            ),
            _next_call(
                4,
                "search_entities_by_fields",
                "Search entities by exact template field values. Call with field_filters=[{'field_id': '<id from get_template>', 'value': '<exact value>'}], first=0, offset=100. Do not use metaFieldUuid; offset is page size, not skip.",
                params={"field_filters": field_filters, "first": 0, "offset": 100} if field_filters else {"first": 0, "offset": 100},
                missing_args=[
                    _missing_arg("realm_id", "list_available_realms"),
                    _missing_arg("field_filters", "get_template"),
                ],
            ),
        ]

    calls = [
        _next_call(1, "list_available_realms", "Discover the realm_id to search in."),
        _next_call(
            2,
            "search_objects",
            "Search objects by the known name or object filter.",
            params={"name_filter": name_filter, "first": 0, "offset": 100},
            missing_args=[_missing_arg("realm_id", "list_available_realms")],
        ),
    ]
    calls.append(
        _next_call(
            len(calls) + 1,
            "search_entities",
            "Run the entity search variant if object search needs confirmation or template filtering.",
            params={"name_filter": name_filter, "first": 0, "offset": 100},
            missing_args=[_missing_arg("realm_id", "list_available_realms")],
        )
    )

    return calls


def _field_value_search_requested(question: str) -> bool:
    question_lower = question.lower()
    return any(
        marker in question_lower
        for marker in ("field value", "by field", "field_id", "field filter", "inn", "ogrn", "инн", "огрн")
    )


def _template_management_route() -> dict[str, Any]:
    return {
        "name": "template_management",
        "next_calls": _template_management_next_calls,
        "answer": lambda mode: (
            "Start with realm discovery, then search/read templates. In read_only mode, template writes and deletes are only avoided actions."
        ),
        "clarifying_question": lambda question, _mode: (
            None
            if _has_known_template_name(question)
            else "Which template name/filter and template action should be routed after realm discovery?"
        ),
    }


def _template_management_next_calls(question: str, _effective_safety_mode: str, _contract: dict[str, Any]) -> list[dict[str, Any]]:
    name_part = _known_name_param(question, "template")
    return [
        _next_call(1, "list_available_realms", "Discover the realm_id for template work."),
        _next_call(
            2,
            "search_templates",
            "Find candidate templates and exact template_id values.",
            params={"name_part": name_part},
            missing_args=[_missing_arg("realm_id", "list_available_realms")],
        ),
        _next_call(
            3,
            "get_template",
            "Inspect the selected template before any write or delete decision.",
            missing_args=[
                _missing_arg("realm_id", "list_available_realms"),
                _missing_arg("template_id", "search_templates"),
            ],
        ),
    ]


def _template_delete_route() -> dict[str, Any]:
    return {
        "name": "template_delete",
        "next_calls": _template_management_next_calls,
        "answer": lambda mode: (
            "Do not delete by name. Discover the realm, search the template, inspect the exact template_id, "
            "then require explicit operator confirmation before delete_template can be considered."
        ),
        "clarifying_question": lambda _question, _mode: (
            "After search_templates/get_template identify exact realm_id and template_id, does the operator explicitly confirm deletion?"
        ),
    }


def _template_field_route() -> dict[str, Any]:
    return {
        "name": "template_field",
        "next_calls": _template_management_next_calls,
        "answer": lambda mode: "Find the template first; field writes/deletes are not immediate next calls without exact IDs and write intent.",
        "clarifying_question": lambda _question, _mode: "Which field operation and field payload should be routed after the template is identified?",
    }


def _diagram_discovery_route() -> dict[str, Any]:
    return {
        "name": "diagram_discovery",
        "next_calls": _diagram_discovery_next_calls,
        "answer": lambda mode: "Start with realm discovery, then search and inspect diagrams before any diagram mutation.",
        "clarifying_question": lambda _question, _mode: None,
    }


def _diagram_update_route() -> dict[str, Any]:
    return {
        "name": "diagram_update",
        "next_calls": _diagram_discovery_next_calls,
        "answer": lambda mode: (
            "For a diagram update, first discover realm_id and diagram_id through read-only calls. "
            "update_diagram is not an immediate next call until exact IDs and write_intent are present."
        ),
        "clarifying_question": lambda _question, _mode: (
            "What diagram metadata should change: name, comment, or tag_ids?"
        ),
    }


def _diagram_delete_route() -> dict[str, Any]:
    return {
        "name": "diagram_delete",
        "next_calls": _diagram_discovery_next_calls,
        "answer": lambda mode: (
            "Do not delete a diagram by name. Search and inspect the exact diagram_id, then require explicit operator confirmation."
        ),
        "clarifying_question": lambda _question, _mode: (
            "After search_diagrams/get_diagram identify exact realm_id and diagram_id, does the operator explicitly confirm deletion?"
        ),
    }


def _diagram_discovery_next_calls(question: str, _effective_safety_mode: str, _contract: dict[str, Any]) -> list[dict[str, Any]]:
    name_part = _known_name_param(question, "diagram")
    return [
        _next_call(1, "list_available_realms", "Discover the realm_id for diagram work."),
        _next_call(
            2,
            "search_diagrams",
            "Find candidate diagrams and exact diagram_id values.",
            params={"name_part": name_part, "first": 0, "offset": 100},
            missing_args=[_missing_arg("realm_id", "list_available_realms")],
        ),
        _next_call(
            3,
            "get_diagram",
            "Inspect the selected diagram before any update or delete.",
            missing_args=[
                _missing_arg("realm_id", "list_available_realms"),
                _missing_arg("diagram_id", "search_diagrams"),
            ],
        ),
    ]


def _generic_route(task_class_name: str) -> dict[str, Any]:
    def next_calls(_question: str, _effective_safety_mode: str, _contract: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            _next_call(1, "list_available_realms", "Discover the realm_id for realm-scoped Onto MCP work.")
        ]

    return {
        "name": task_class_name,
        "next_calls": next_calls,
        "answer": lambda mode: "Start with safe realm discovery, then use read-only search/get tools for exact IDs.",
        "clarifying_question": lambda _question, _mode: None,
    }


def _memory_route() -> dict[str, Any]:
    return {
        "name": "memory",
        "next_calls": _memory_next_calls,
        "answer": lambda mode: (
            "Route MemoryArtifact work through the dedicated memory tools. In read_only mode this only searches or reads "
            "memory; owner-approved write/lifecycle intent can route draft, read-back, submit, and accept calls."
        ),
        "clarifying_question": _memory_clarifying_question,
    }


def _memory_next_calls(
    question: str,
    effective_safety_mode: str,
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    if (
        effective_safety_mode == "read_only"
        and (_memory_create_requested(question) or _memory_lifecycle_requested(question))
    ):
        return []

    if _memory_create_inputs_ready(question) and _memory_high_risk_allowed(contract, effective_safety_mode, question):
        next_calls = _memory_create_draft_next_calls(question)
        if _memory_lifecycle_requested(question) and _memory_lifecycle_allowed(contract, effective_safety_mode, question):
            next_calls.extend(_memory_submit_accept_next_calls(question, start_step=len(next_calls) + 1))
        return next_calls

    if (
        _memory_lifecycle_requested(question)
        and _memory_lifecycle_allowed(contract, effective_safety_mode, question)
        and _has_named_input(question, "realm_id")
        and _has_named_input(question, "artifact_id")
    ):
        return _memory_existing_artifact_lifecycle_next_calls(question)

    return _memory_read_next_calls(question)


def _memory_read_next_calls(question: str) -> list[dict[str, Any]]:
    realm_id = _named_input_value(question, "realm_id")
    target_id = _memory_target_id(question)
    artifact_path = _named_input_value(question, "artifact_path")
    artifact_id = _named_input_value(question, "artifact_id")
    calls: list[dict[str, Any]] = []

    if not realm_id:
        calls.append(_next_call(1, "list_available_realms", "Discover the realm_id for memory work."))

    search_params: dict[str, Any] = {}
    if realm_id:
        search_params["realm_id"] = realm_id
    if artifact_path:
        search_params["artifact_path"] = artifact_path
    if target_id:
        search_params["target_kind"] = _named_input_value(question, "target_kind") or "entity"
        search_params["target_id"] = target_id
    search_params.setdefault("first", 0)
    search_params.setdefault("offset", 100)

    calls.append(
        _next_call(
            len(calls) + 1,
            "search_memory_artifacts",
            "Search accepted MemoryArtifacts compactly; draft/proposed artifacts require a draft-specific read.",
            params=search_params,
            missing_args=[] if realm_id else [_missing_arg("realm_id", "list_available_realms")],
        )
    )

    if artifact_path:
        calls.append(
            _next_call(
                len(calls) + 1,
                "get_memory_artifact_by_path",
                "Read the accepted MemoryArtifact by path when an accepted path is known.",
                params={"realm_id": realm_id, "artifact_path": artifact_path} if realm_id else {"artifact_path": artifact_path},
                missing_args=[] if realm_id else [_missing_arg("realm_id", "list_available_realms")],
            )
        )
    if artifact_id:
        calls.append(
            _next_call(
                len(calls) + 1,
                "get_memory_artifact",
                "Read the MemoryArtifact by exact artifact_id.",
                params={"realm_id": realm_id, "artifact_id": artifact_id} if realm_id else {"artifact_id": artifact_id},
                missing_args=[] if realm_id else [_missing_arg("realm_id", "list_available_realms")],
            )
        )
    return calls


def _memory_create_draft_next_calls(question: str) -> list[dict[str, Any]]:
    realm_id = _named_input_value(question, "realm_id")
    return [
        _next_call(
            1,
            "create_memory_artifact_draft",
            "Create the owner-approved MemoryArtifact draft using the exact realm, artifact path, body, summary, source, and target.",
            params=_memory_create_params(question),
        ),
        _next_call(
            2,
            "get_memory_artifact",
            "Read back the created draft using the artifact_id returned by create_memory_artifact_draft.",
            params={"realm_id": realm_id},
            missing_args=[_missing_arg("artifact_id", "create_memory_artifact_draft")],
        ),
    ]


def _memory_submit_accept_next_calls(question: str, *, start_step: int) -> list[dict[str, Any]]:
    realm_id = _named_input_value(question, "realm_id")
    artifact_path = _named_input_value(question, "artifact_path")
    calls = [
        _next_call(
            start_step,
            "submit_memory_artifact",
            "Submit the reviewed draft for MemoryArtifact lifecycle review.",
            params={"realm_id": realm_id},
            missing_args=[_missing_arg("artifact_id", "create_memory_artifact_draft")],
        ),
        _next_call(
            start_step + 1,
            "accept_memory_artifact",
            "Accept the submitted MemoryArtifact after owner approval.",
            params={"realm_id": realm_id},
            missing_args=[_missing_arg("artifact_id", "create_memory_artifact_draft")],
        ),
    ]
    if artifact_path:
        calls.append(
            _next_call(
                start_step + 2,
                "get_memory_artifact_by_path",
                "Verify the accepted MemoryArtifact is visible by path after accept.",
                params={"realm_id": realm_id, "artifact_path": artifact_path},
            )
        )
    else:
        calls.append(
            _next_call(
                start_step + 2,
                "search_memory_artifacts",
                "Verify the accepted MemoryArtifact is visible in accepted search after accept.",
                params={"realm_id": realm_id},
            )
        )
    return calls


def _memory_existing_artifact_lifecycle_next_calls(question: str) -> list[dict[str, Any]]:
    realm_id = _named_input_value(question, "realm_id")
    artifact_id = _named_input_value(question, "artifact_id")
    params = {"realm_id": realm_id, "artifact_id": artifact_id}
    calls = [
        _next_call(1, "get_memory_artifact", "Read the exact MemoryArtifact before lifecycle transition.", params=params)
    ]
    if re.search(r"\bsubmit\b", question, re.IGNORECASE):
        calls.append(_next_call(len(calls) + 1, "submit_memory_artifact", "Submit the exact MemoryArtifact.", params=params))
    if re.search(r"\baccept|approve\b", question, re.IGNORECASE):
        calls.append(_next_call(len(calls) + 1, "accept_memory_artifact", "Accept the exact MemoryArtifact.", params=params))
    if re.search(r"\brevoke\b", question, re.IGNORECASE):
        calls.append(_next_call(len(calls) + 1, "revoke_memory_artifact", "Revoke the exact MemoryArtifact.", params=params))
    calls.append(
        _next_call(
            len(calls) + 1,
            "get_memory_artifact",
            "Read back the MemoryArtifact after the lifecycle transition.",
            params=params,
        )
    )
    return calls


def _memory_create_params(question: str) -> dict[str, Any]:
    target_id = _memory_target_id(question)
    target_kind = _named_input_value(question, "target_kind") or "entity"
    target_role = _named_input_value(question, "role") or "primary"
    return {
        "realm_id": _named_input_value(question, "realm_id"),
        "artifact_path": _named_input_value(question, "artifact_path"),
        "artifact_kind": _named_input_value(question, "artifact_kind"),
        "write_mode": _named_input_value(question, "write_mode"),
        "body": _named_input_value(question, "body") or "<body provided by operator>",
        "summary": _named_input_value(question, "summary") or "<summary provided by operator>",
        "source_ref": _named_input_value(question, "source_ref"),
        "targets": [{"target_kind": target_kind, "target_id": target_id, "role": target_role}],
    }


def _memory_clarifying_question(question: str, effective_safety_mode: str) -> str | None:
    intent = _detect_intent(question)
    if intent not in {"write", "lifecycle"}:
        return None
    if effective_safety_mode == "read_only":
        return "Should this MemoryArtifact write/lifecycle flow run with owner-approved write_intent or lifecycle_intent?"
    missing_inputs = _missing_memory_create_inputs(question)
    if _memory_create_requested(question) and missing_inputs:
        return "Provide these MemoryArtifact create inputs before routing create_memory_artifact_draft: " + ", ".join(missing_inputs) + "."
    if not _has_confirmation(question):
        return "Does the owner explicitly approve this MemoryArtifact write or lifecycle transition?"
    return None


def _memory_create_requested(question: str) -> bool:
    question_lower = question.lower()
    return bool(_WRITE_RE.search(question) and ("memory" in question_lower or "artifact" in question_lower))


def _memory_lifecycle_requested(question: str) -> bool:
    return bool(_LIFECYCLE_RE.search(question))


def _memory_high_risk_allowed(contract: dict[str, Any], effective_safety_mode: str, question: str) -> bool:
    return "high_risk" in contract["safety_modes"][effective_safety_mode]["allows"] and _has_confirmation(question)


def _memory_lifecycle_allowed(contract: dict[str, Any], effective_safety_mode: str, question: str) -> bool:
    return "lifecycle" in contract["safety_modes"][effective_safety_mode]["allows"] and _has_confirmation(question)


def _memory_create_inputs_ready(question: str) -> bool:
    return not _missing_memory_create_inputs(question)


def _missing_memory_create_inputs(question: str) -> list[str]:
    missing = [
        input_name
        for input_name in ["realm_id", "artifact_path", "artifact_kind", "write_mode", "body", "summary", "source_ref"]
        if not _has_named_input(question, input_name)
    ]
    if not _memory_target_id(question):
        missing.append("target_id or entity_id")
    return missing


def _memory_target_id(question: str) -> str:
    return (
        _named_input_value(question, "target_id")
        or _named_input_value(question, "entity_id")
        or _named_input_value(question, "node_id")
        or _json_string_value(question, "target_id")
    )


def _has_named_input(question: str, input_name: str) -> bool:
    if _named_input_value(question, input_name):
        return True
    pattern = r"(?<![a-z0-9_])" + re.escape(input_name) + r"(?![a-z0-9_])\s+(?:provided|ready|known|available)"
    return bool(re.search(pattern, question, re.IGNORECASE))


def _named_input_value(question: str, input_name: str) -> str:
    return _extract_named_text(question, input_name).strip().strip("\"'")


def _json_string_value(question: str, input_name: str) -> str:
    pattern = re.compile(rf'"{re.escape(input_name)}"\s*:\s*"(?P<value>[^"]+)"', re.IGNORECASE)
    match = pattern.search(question)
    return match.group("value").strip() if match else ""


def _route_safety_notes(
    *,
    contract: dict[str, Any],
    route_name: str,
    family_names: list[str],
    question: str,
    effective_safety_mode: str,
    intent: str,
    avoid_tools: list[str],
) -> list[str]:
    notes = [f"Effective safety mode is {effective_safety_mode}."]
    if effective_safety_mode == "read_only":
        notes.append("read_only mode must keep write, destructive, lifecycle, admin-like, and high-risk tools out of next_calls.")
    if avoid_tools:
        notes.append("Avoided tools are not immediate next calls for the current inputs and safety mode.")
    if route_name == "diagram_update" and "update_diagram" in avoid_tools:
        notes.append("update_diagram requires exact realm_id and diagram_id plus write_intent before it can be routed as a mutation.")
    if route_name == "template_delete" and "delete_template" in avoid_tools:
        notes.append("delete_template requires exact realm_id and template_id plus explicit operator confirmation.")
    if route_name == "memory":
        notes.append("MemoryArtifact writes and lifecycle transitions must use dedicated MemoryArtifact MCP tools.")
        notes.append("Accepted artifacts are visible through search_memory_artifacts or get_memory_artifact_by_path; drafts are read by artifact_id.")
        if effective_safety_mode == "read_only" and intent in {"write", "lifecycle"}:
            notes.append("Do not substitute read-only search for a requested MemoryArtifact write; rerun with owner-approved write_intent or lifecycle_intent.")
    if _tools_for_safety(contract, family_names, "high_risk"):
        notes.append("High-risk MemoryArtifact write tools require owner-approved intent before use.")
    if route_name == "memory" and intent == "lifecycle" and _memory_create_inputs_ready(question):
        notes.append("Lifecycle calls use the artifact_id returned by create_memory_artifact_draft in this planned sequence.")
    elif intent in {"destructive", "lifecycle"}:
        notes.append(f"{intent} intent requires exact named IDs and explicit operator confirmation; a bare UUID is not enough.")
    elif _tools_for_safety(contract, family_names, "destructive"):
        notes.append("Destructive tools require exact named IDs and explicit operator confirmation before use.")
    return _dedupe_strings(notes)


def _known_name_param(question: str, kind: str) -> str:
    value = _extract_named_text(question, f"{kind} name")
    if value:
        return value
    if f"{kind} name" in question.lower():
        return f"<{kind} name>"
    return ""


def _has_known_template_name(question: str) -> bool:
    question_lower = question.lower()
    return "template name" in question_lower or bool(_extract_named_text(question, "template name"))


def _extract_named_text(question: str, label: str) -> str:
    pattern = re.compile(rf"\b{re.escape(label)}\b\s*(?:=|:|is)\s*(?P<value>[^.;\n]+)", re.IGNORECASE)
    match = pattern.search(question)
    if not match:
        return ""
    value = match.group("value").strip()
    if value.lower() in {"only", "none", "unknown"}:
        return ""
    if value.lower().endswith(" only"):
        value = value[:-5].strip()
    return value


def _next_call(
    step: int,
    tool: str,
    purpose: str,
    *,
    params: dict[str, Any] | None = None,
    missing_args: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "step": step,
        "tool": tool,
        "purpose": purpose,
        "params": params or {},
        "missing_args": missing_args or [],
    }


def _missing_arg(arg: str, get_with_tool: str) -> dict[str, str]:
    return {"arg": arg, "get_with_tool": get_with_tool}


def _families_for_task_classes(contract: dict[str, Any], task_class_names: list[str]) -> list[str]:
    families: list[str] = []
    for task_class_name in task_class_names:
        for family_name in contract["task_classes"][task_class_name]["families"]:
            if family_name not in families:
                families.append(family_name)
    return families


def _blocked_tool_names(
    contract: dict[str, Any],
    family_names: list[str],
    effective_safety_mode: str,
    question: str,
    *,
    require_ids: bool,
) -> list[str]:
    allowed_safety = set(contract["safety_modes"][effective_safety_mode]["allows"])
    blocked: list[str] = []
    for family_name in family_names:
        for tool_name in contract["tool_families"][family_name]["tools"]:
            tool_safety = contract["tool_contract"][tool_name]["safety"]
            if tool_safety == "read_only":
                continue
            if tool_safety not in allowed_safety:
                blocked.append(tool_name)
                continue
            if tool_safety == "high_risk" and not _has_confirmation(question):
                blocked.append(tool_name)
                continue
            if require_ids and not _tool_required_ids_present(contract, tool_name, question):
                blocked.append(tool_name)
                continue
            if tool_name == "create_memory_artifact_draft" and not _memory_create_inputs_ready(question):
                blocked.append(tool_name)
                continue
            if tool_safety in {"destructive", "lifecycle"} and not _has_confirmation(question):
                blocked.append(tool_name)
    return _dedupe_strings(blocked)


def _all_mutating_tool_names(contract: dict[str, Any]) -> list[str]:
    return _dedupe_strings(
        [
            tool_name
            for tool_name, tool in contract["tool_contract"].items()
            if tool["safety"] != "read_only"
        ]
    )


def _tool_required_ids_present(contract: dict[str, Any], tool_name: str, question: str) -> bool:
    known_ids = _known_id_names(contract)
    requirements = contract["tool_contract"][tool_name].get("required_inputs", [])
    id_requirements = [requirement for requirement in requirements if _requirement_tokens(requirement, known_ids)]
    return all(_requirement_present(requirement, question, known_ids) for requirement in id_requirements)


def _tools_for_safety(contract: dict[str, Any], family_names: list[str], safety: str) -> list[str]:
    tools: list[str] = []
    for family_name in family_names:
        for tool_name in contract["tool_families"][family_name]["tools"]:
            if contract["tool_contract"][tool_name]["safety"] == safety:
                tools.append(tool_name)
    return tools


def _requirement_present(required_id: str, question: str, known_ids: set[str]) -> bool:
    if not question:
        return False
    provided_names = _provided_requirement_names(question)
    alternatives = _requirement_alternatives(required_id, known_ids)
    if not alternatives:
        return False
    return any(all(_requirement_token_present(token, provided_names) for token in alternative) for alternative in alternatives)


def _provided_requirement_names(question: str) -> set[str]:
    provided: set[str] = set()
    for match in _NAMED_REQUIREMENT_VALUE_RE.finditer(question):
        name = match.group("name").lower()
        value = match.group("value").strip().strip(".,;")
        if not value or _CONFIRMATION_RE.fullmatch(value):
            continue
        provided.add(name)
    return provided


def _requirement_alternatives(required_id: str, known_ids: set[str]) -> list[list[str]]:
    requirement = required_id.lower()
    alternatives: list[list[str]] = []
    for raw_alternative in re.split(r"\s+or\s+", requirement):
        tokens = _requirement_tokens(raw_alternative, known_ids)
        if tokens:
            alternatives.append(tokens)
    return alternatives


def _requirement_tokens(requirement: str, known_ids: set[str]) -> list[str]:
    tokens = [token.lower() for token in _REQUIREMENT_TOKEN_RE.findall(requirement)]
    if tokens:
        return _dedupe_strings(tokens)
    return _dedupe_strings([known_id for known_id in known_ids if known_id in requirement])


def _requirement_token_present(token: str, provided_names: set[str]) -> bool:
    if token in provided_names:
        return True
    if token.endswith("_ids") and f"{token[:-4]}_id" in provided_names:
        return True
    if token.endswith("_id") and f"{token[:-3]}_ids" in provided_names:
        return True
    return False


def _known_id_names(contract: dict[str, Any]) -> set[str]:
    return set(contract["id_dependency_graph"]["ids"])


def _dedupe_strings(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
