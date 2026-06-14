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
_WRITE_RE = re.compile(r"\b(create|update|save|link|unlink|add|remove|append|manage)\b", re.IGNORECASE)
_CONFIRMATION_RE = re.compile(r"\b(confirm|confirmed|explicit|operator intent|approved|approval)\b", re.IGNORECASE)
_REQUIREMENT_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9_]*(?:_ids|_id)\b", re.IGNORECASE)
_NAMED_REQUIREMENT_VALUE_RE = re.compile(
    r"\b(?P<name>[a-z][a-z0-9_]*(?:_ids|_id))\b\s*(?:=|:|is)?\s*(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)
_SCOPE_GLOSSARY_RE = re.compile(
    r"(\bwhat\s+is\s+(?:an?\s+)?ontology\b|\bdefine\s+ontology\b|\bontology\s+definition\b|"
    r"\b\u0447\u0442\u043e\s+\u0442\u0430\u043a\u043e\u0435\s+\u043e\u043d\u0442\u043e\u043b\u043e\u0433)",
    re.IGNORECASE,
)


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
    matches: list[str] = []
    for task_class_name, task_class in contract["task_classes"].items():
        keywords = task_class.get("keywords", [])
        if any(keyword.lower() in question_lower for keyword in keywords):
            matches.append(task_class_name)
    return matches


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
    next_calls = route["next_calls"](question)
    avoid_tools = _blocked_tool_names(
        contract,
        family_names,
        effective_safety_mode,
        question,
        require_ids=intent in {"write", "destructive", "lifecycle"},
    )
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
    return _generic_route(task_class_name)


def _object_search_next_calls(question: str) -> list[dict[str, Any]]:
    name_filter = _known_name_param(question, "object")
    return [
        _next_call(1, "list_available_realms", "Discover the realm_id to search in."),
        _next_call(
            2,
            "search_objects",
            "Search objects by the known name or object filter.",
            params={"name_filter": name_filter},
            missing_args=[_missing_arg("realm_id", "list_available_realms")],
        ),
        _next_call(
            3,
            "search_entities",
            "Run the entity search variant if object search needs confirmation or template filtering.",
            params={"name_filter": name_filter},
            missing_args=[_missing_arg("realm_id", "list_available_realms")],
        ),
    ]


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


def _template_management_next_calls(question: str) -> list[dict[str, Any]]:
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


def _diagram_discovery_next_calls(question: str) -> list[dict[str, Any]]:
    name_part = _known_name_param(question, "diagram")
    return [
        _next_call(1, "list_available_realms", "Discover the realm_id for diagram work."),
        _next_call(
            2,
            "search_diagrams",
            "Find candidate diagrams and exact diagram_id values.",
            params={"name_part": name_part},
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
    def next_calls(question: str) -> list[dict[str, Any]]:
        return [
            _next_call(1, "list_available_realms", "Discover the realm_id for realm-scoped Onto MCP work.")
        ]

    return {
        "name": task_class_name,
        "next_calls": next_calls,
        "answer": lambda mode: "Start with safe realm discovery, then use read-only search/get tools for exact IDs.",
        "clarifying_question": lambda _question, _mode: None,
    }


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
    if intent in {"destructive", "lifecycle"}:
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
            if require_ids and not _tool_required_ids_present(contract, tool_name, question):
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
