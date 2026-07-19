from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from typing import Any

SCHEMA_VERSION = "1"
CONSTITUTION_PATH = "realm/agents/constitution"
REGISTRY_PATH = "realm/agents/registry"
MAX_REGISTRY_ENTRIES = 32
MAX_RESULT_BYTES = 65536

LIST_LABEL = "Realm agent registry data:"
GET_LABEL = "Realm agent data:"

_UUID_RE = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
)
_UUID_SEARCH_RE = re.compile(
    r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"
)
_SLUG_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
_REGISTRY_HEADER = ["slug", "Роль", "Зона путей", "Режим", "Чартер", "Состояние"]
_ISSUE_ORDER = {
    code: index
    for index, code in enumerate(
        [
            "constitution_missing",
            "registry_missing",
            "registry_unparseable",
            "registry_row_malformed",
            "registry_required_field_missing",
            "registry_slug_duplicate",
            "resident_state_unsupported",
            "charter_missing",
            "charter_unparseable",
            "charter_path_mismatch",
            "charter_slug_mismatch",
            "charter_realm_mismatch",
            "registry_entry_missing",
            "registry_size_limit_exceeded",
            "response_size_limit_exceeded",
            "dependency_error",
        ]
    )
}

ArtifactReader = Callable[[str], dict[str, Any]]


class RealmAgentPathMissing(Exception):
    def __init__(self, artifact_path: str) -> None:
        super().__init__(artifact_path)
        self.artifact_path = artifact_path


class RealmAgentDependencyFailure(Exception):
    def __init__(
        self,
        kind: str,
        artifact_path: str,
        http_status: int | None = None,
    ) -> None:
        super().__init__(kind)
        self.kind = kind
        self.artifact_path = artifact_path
        self.http_status = http_status

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "operation": "read_accepted_artifact_by_path",
            "artifact_path": self.artifact_path,
            "http_status": self.http_status,
        }


def list_realm_agents_result(realm_id: str, read_artifact: ArtifactReader) -> str:
    normalized_realm_id, input_issue = _validate_realm_id(realm_id)
    if input_issue is not None:
        return _format_result("list", _list_input_error(realm_id, input_issue))

    governance = _load_governance(normalized_realm_id, read_artifact)
    data = {
        "schema_version": SCHEMA_VERSION,
        "realm_id": normalized_realm_id,
        "governance_status": governance["governance_status"],
        "constitution": governance["constitution"],
        "registry": governance["registry"],
        "agents": governance["agents"],
        "counts": governance["counts"],
        "complete_for_registry": governance["complete_for_registry"],
        "unregistered_charters_enumerated": False,
        "issues": governance["issues"],
        "dependency": governance["dependency"],
    }
    return _format_result("list", data)


def get_realm_agent_result(
    realm_id: str,
    slug: str,
    read_artifact: ArtifactReader,
) -> str:
    normalized_realm_id, realm_issue = _validate_realm_id(realm_id)
    if realm_issue is not None:
        return _format_result("get", _get_input_error(realm_id, slug, realm_issue))

    slug_issue = _validate_slug(slug)
    if slug_issue is not None:
        return _format_result(
            "get", _get_input_error(normalized_realm_id, slug, slug_issue)
        )

    governance = _load_governance(normalized_realm_id, read_artifact)
    governance_status = governance["governance_status"]
    if governance_status in {"governance_unavailable", "dependency_error"}:
        return _format_result(
            "get",
            _get_terminal_result(
                normalized_realm_id,
                slug,
                governance_status,
                governance_status,
                governance["issues"],
                governance["dependency"],
                complete=False,
            ),
        )

    if governance_status == "invalid_governance_state":
        rows = [row for row in governance["_rows"] if row["slug"] == slug]
        if rows and any(row["validity"] == "invalid" for row in rows):
            result = _get_terminal_result(
                normalized_realm_id,
                slug,
                governance_status,
                "invalid_registry_entry",
                governance["issues"],
                None,
                complete=governance["complete_for_registry"],
                validity="invalid",
                resident_state=rows[0]["resident_state"] if len(rows) == 1 else None,
            )
            if len(rows) == 1:
                result["charter"] = rows[0]["charter"]
            return _format_result("get", result)

        return _format_result(
            "get",
            _get_terminal_result(
                normalized_realm_id,
                slug,
                governance_status,
                "invalid_governance_state",
                governance["issues"],
                None,
                complete=governance["complete_for_registry"],
            ),
        )

    matching_rows = [row for row in governance["_rows"] if row["slug"] == slug]
    if matching_rows:
        row = matching_rows[0]
        resolution = (
            "valid_active_resident"
            if row["resident_state"] == "active"
            else "valid_suspended_resident"
        )
        return _format_result(
            "get",
            {
                "schema_version": SCHEMA_VERSION,
                "realm_id": normalized_realm_id,
                "slug": slug,
                "governance_status": "valid",
                "resolution": resolution,
                "resident_state": row["resident_state"],
                "validity": "valid",
                "boot_allowed": row["resident_state"] == "active",
                "charter": row["charter"],
                "complete_for_registry": True,
                "issues": [],
                "dependency": None,
            },
        )

    derived_path = _charter_path(slug)
    try:
        artifact = read_artifact(derived_path)
        _validate_unregistered_artifact(artifact, normalized_realm_id, derived_path)
    except RealmAgentPathMissing:
        unregistered_charter = {
            "exists": False,
            "artifact_id": None,
            "artifact_path": derived_path,
            "status": None,
        }
    except RealmAgentDependencyFailure as failure:
        return _format_result(
            "get",
            _get_dependency_result(normalized_realm_id, slug, failure),
        )
    else:
        compact = _compact_artifact(artifact)
        unregistered_charter = {"exists": True, **compact}

    return _format_result(
        "get",
        {
            "schema_version": SCHEMA_VERSION,
            "realm_id": normalized_realm_id,
            "slug": slug,
            "governance_status": "valid",
            "resolution": "not_registered",
            "resident_state": None,
            "validity": "not_resident",
            "boot_allowed": False,
            "unregistered_charter": unregistered_charter,
            "complete_for_registry": True,
            "issues": [
                _issue(
                    "registry_entry_missing",
                    (
                        "An accepted charter exists, but the slug is absent from the current registry."
                        if unregistered_charter["exists"]
                        else "The exact slug is absent from the current registry."
                    ),
                )
            ],
            "dependency": None,
        },
    )


def format_realm_agent_tool_timeout(
    tool_name: str,
    realm_id: str,
    slug: str = "",
    artifact_path: str = CONSTITUTION_PATH,
) -> str:
    normalized_realm_id, issue = _validate_realm_id(realm_id)
    output_realm_id = normalized_realm_id if issue is None else str(realm_id or "")
    failure = RealmAgentDependencyFailure("timeout", artifact_path, None)
    if tool_name == "get_realm_agent":
        return _format_result(
            "get", _get_dependency_result(output_realm_id, slug, failure)
        )

    return _format_result(
        "list",
        {
            "schema_version": SCHEMA_VERSION,
            "realm_id": output_realm_id,
            "governance_status": "dependency_error",
            "constitution": None,
            "registry": None,
            "agents": [],
            "counts": None,
            "complete_for_registry": False,
            "unregistered_charters_enumerated": False,
            "issues": [
                _issue(
                    "dependency_error",
                    "A dependency prevented a trustworthy realm-agent decision.",
                )
            ],
            "dependency": failure.as_dict(),
        },
    )


def _load_governance(realm_id: str, read_artifact: ArtifactReader) -> dict[str, Any]:
    constitution: dict[str, Any] | None = None
    registry: dict[str, Any] | None = None
    try:
        constitution_artifact = read_artifact(CONSTITUTION_PATH)
        _validate_governance_source(constitution_artifact, realm_id, CONSTITUTION_PATH)
        constitution = _compact_artifact(constitution_artifact)
    except RealmAgentPathMissing:
        return _governance_terminal(
            "governance_unavailable",
            constitution=None,
            registry=None,
            issues=[
                _issue(
                    "constitution_missing",
                    "The accepted/current realm-agent constitution is unavailable.",
                )
            ],
        )
    except RealmAgentDependencyFailure as failure:
        return _governance_dependency(constitution, registry, failure)

    try:
        registry_artifact = read_artifact(REGISTRY_PATH)
        _validate_governance_source(registry_artifact, realm_id, REGISTRY_PATH)
        registry = _compact_artifact(registry_artifact)
    except RealmAgentPathMissing:
        return _governance_terminal(
            "governance_unavailable",
            constitution=constitution,
            registry=None,
            issues=[
                _issue(
                    "registry_missing",
                    "The accepted/current realm-agent registry is unavailable.",
                )
            ],
        )
    except RealmAgentDependencyFailure as failure:
        return _governance_dependency(constitution, registry, failure)

    parsed_rows = _parse_registry(str(registry_artifact["body"]))
    if parsed_rows is None:
        return _governance_terminal(
            "invalid_governance_state",
            constitution=constitution,
            registry=registry,
            issues=[
                _issue(
                    "registry_unparseable",
                    "The canonical registry table cannot be parsed deterministically.",
                )
            ],
        )

    if len(parsed_rows) > MAX_REGISTRY_ENTRIES:
        return _governance_terminal(
            "invalid_governance_state",
            constitution=constitution,
            registry=registry,
            issues=[
                _issue(
                    "registry_size_limit_exceeded",
                    "The realm-agent registry exceeds the approved P0 row limit.",
                )
            ],
        )

    _add_duplicate_issues(parsed_rows)
    for row in parsed_rows:
        if not _row_charter_path_is_callable(row):
            _finish_row(row)
            continue

        expected_path = _charter_path(row["slug"])
        try:
            charter_artifact = read_artifact(expected_path)
        except RealmAgentPathMissing:
            row["charter"] = {
                "artifact_id": None,
                "artifact_path": expected_path,
                "status": None,
            }
            _append_issue(
                row, "charter_missing", "The registered charter is unavailable."
            )
        except RealmAgentDependencyFailure as failure:
            return _governance_dependency(constitution, registry, failure)
        else:
            row["charter"] = _compact_artifact(charter_artifact)
            _validate_charter(row, charter_artifact, realm_id, expected_path)
        _finish_row(row)

    agents = [
        _project_row(
            row,
            global_boot_allowed=all(row["validity"] == "valid" for row in parsed_rows),
        )
        for row in parsed_rows
    ]
    invalid_count = sum(row["validity"] == "invalid" for row in parsed_rows)
    issues = [issue for row in parsed_rows for issue in row["issues"]]
    return {
        "governance_status": "invalid_governance_state" if invalid_count else "valid",
        "constitution": constitution,
        "registry": registry,
        "agents": agents,
        "counts": {
            "registry_entries": len(parsed_rows),
            "valid_active": sum(
                row["validity"] == "valid" and row["resident_state"] == "active"
                for row in parsed_rows
            ),
            "valid_suspended": sum(
                row["validity"] == "valid" and row["resident_state"] == "suspended"
                for row in parsed_rows
            ),
            "invalid": invalid_count,
        },
        "complete_for_registry": True,
        "issues": issues,
        "dependency": None,
        "_rows": parsed_rows,
    }


def _parse_registry(body: str) -> list[dict[str, Any]] | None:
    lines = body.splitlines()
    header_indexes = [
        index
        for index, line in enumerate(lines)
        if _normalized_table_cells(line) == _REGISTRY_HEADER
    ]
    if len(header_indexes) != 1:
        return None

    header_index = header_indexes[0]
    if header_index + 1 >= len(lines) or not _is_separator_row(lines[header_index + 1]):
        return None

    physical_lines: list[str] = []
    for line in lines[header_index + 2 :]:
        if not line.strip():
            break
        if not line.lstrip().startswith("|"):
            break
        physical_lines.append(line)

    rows = [
        _parse_registry_row(line, index) for index, line in enumerate(physical_lines, 1)
    ]
    return rows


def _parse_registry_row(line: str, row_index: int) -> dict[str, Any]:
    cells = _split_table_cells(line)
    malformed = cells is None or len(cells) != 6
    if malformed:
        cells = (cells or [])[:6] + [""] * max(0, 6 - len(cells or []))

    values = [_strip_code_cell(cell) for cell in cells]
    slug, role, path_zone, mode, charter_path, source_state = values
    row: dict[str, Any] = {
        "row_index": row_index,
        "slug": slug,
        "role": role,
        "path_zone": path_zone,
        "mode": mode,
        "charter_path": charter_path,
        "source_state": source_state,
        "resident_state": _normalize_resident_state(source_state),
        "validity": "invalid",
        "charter": None,
        "issues": [],
    }
    if malformed or (slug and not _valid_slug_text(slug)):
        _append_issue(
            row,
            "registry_row_malformed",
            "The physical registry row has invalid structure.",
        )
    if any(not value for value in values):
        _append_issue(
            row,
            "registry_required_field_missing",
            "A mandatory registry field is missing.",
        )
    if source_state and row["resident_state"] is None:
        _append_issue(
            row,
            "resident_state_unsupported",
            "The registry resident state is unsupported.",
        )
    if slug and charter_path and charter_path != _charter_path(slug):
        _append_issue(
            row,
            "charter_path_mismatch",
            "The registry charter path does not match the exact slug path.",
        )
    return row


def _add_duplicate_issues(rows: list[dict[str, Any]]) -> None:
    counts = Counter(row["slug"] for row in rows if row["slug"])
    for row in rows:
        if row["slug"] and counts[row["slug"]] > 1:
            _append_issue(
                row,
                "registry_slug_duplicate",
                "The exact registry slug occurs more than once.",
            )


def _row_charter_path_is_callable(row: dict[str, Any]) -> bool:
    if not row["slug"] or not _valid_slug_text(row["slug"]):
        return False
    if row["charter_path"] != _charter_path(row["slug"]):
        return False
    return True


def _validate_charter(
    row: dict[str, Any],
    artifact: dict[str, Any],
    realm_id: str,
    expected_path: str,
) -> None:
    metadata = _parse_charter_metadata(str(artifact.get("body", "")))
    if metadata is None:
        _append_issue(
            row,
            "charter_unparseable",
            "Required charter metadata is missing or ambiguous.",
        )
    else:
        if metadata["artifact_path"] != expected_path:
            _append_issue(
                row,
                "charter_path_mismatch",
                "Charter metadata reports a different artifact path.",
            )
        if metadata["slug"] != row["slug"]:
            _append_issue(
                row,
                "charter_slug_mismatch",
                "Charter metadata reports a different slug.",
            )
        if metadata["realm_id"].lower() != realm_id:
            _append_issue(
                row,
                "charter_realm_mismatch",
                "Charter metadata reports a different realm.",
            )

    if str(artifact.get("artifact_path", "")) != expected_path:
        _append_issue(
            row,
            "charter_path_mismatch",
            "The returned charter artifact path does not match the registry path.",
        )
    if (
        str(artifact.get("realm_id", "")).lower() != realm_id
        or str(artifact.get("scope_kind", "")) != "realm"
        or str(artifact.get("scope_id", "")).lower() != realm_id
    ):
        _append_issue(
            row,
            "charter_realm_mismatch",
            "The returned charter artifact is not scoped to the supplied realm.",
        )


def _parse_charter_metadata(body: str) -> dict[str, str] | None:
    patterns = {
        "realm": re.compile(r"^\*\*Пространство:\*\*\s*(.+?)\s*$"),
        "artifact_path": re.compile(r"^\*\*Путь артефакта:\*\*\s*(.+?)\s*$"),
        "slug": re.compile(r"^\*\*Slug:\*\*\s*(.+?)\s*$"),
    }
    matches: dict[str, list[str]] = {name: [] for name in patterns}
    for line in body.splitlines():
        for name, pattern in patterns.items():
            match = pattern.match(line.strip())
            if match:
                matches[name].append(match.group(1).strip())

    if any(len(values) != 1 for values in matches.values()):
        return None
    realm_ids = _UUID_SEARCH_RE.findall(matches["realm"][0])
    if len(realm_ids) != 1:
        return None
    return {
        "realm_id": realm_ids[0],
        "artifact_path": _strip_code_cell(matches["artifact_path"][0]),
        "slug": _strip_code_cell(matches["slug"][0]),
    }


def _finish_row(row: dict[str, Any]) -> None:
    row["issues"].sort(key=lambda issue: _ISSUE_ORDER[issue["code"]])
    row["validity"] = "invalid" if row["issues"] else "valid"


def _project_row(row: dict[str, Any], *, global_boot_allowed: bool) -> dict[str, Any]:
    return {
        "row_index": row["row_index"],
        "slug": row["slug"],
        "role": row["role"],
        "path_zone": row["path_zone"],
        "mode": row["mode"],
        "resident_state": row["resident_state"],
        "validity": row["validity"],
        "boot_allowed": (
            global_boot_allowed
            and row["validity"] == "valid"
            and row["resident_state"] == "active"
        ),
        "charter": row["charter"],
        "issues": row["issues"],
    }


def _validate_governance_source(
    artifact: dict[str, Any], realm_id: str, path: str
) -> None:
    if (
        str(artifact.get("artifact_path", "")) != path
        or str(artifact.get("realm_id", "")).lower() != realm_id
        or str(artifact.get("scope_kind", "")) != "realm"
        or str(artifact.get("scope_id", "")).lower() != realm_id
        or str(artifact.get("status", "")) != "accepted"
    ):
        raise RealmAgentDependencyFailure("invalid_response", path, None)


def _validate_unregistered_artifact(
    artifact: dict[str, Any], realm_id: str, path: str
) -> None:
    _validate_governance_source(artifact, realm_id, path)


def _compact_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": artifact.get("artifact_id"),
        "artifact_path": artifact.get("artifact_path"),
        "status": artifact.get("status"),
    }


def _governance_terminal(
    governance_status: str,
    *,
    constitution: dict[str, Any] | None,
    registry: dict[str, Any] | None,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "governance_status": governance_status,
        "constitution": constitution,
        "registry": registry,
        "agents": [],
        "counts": None,
        "complete_for_registry": False,
        "issues": issues,
        "dependency": None,
        "_rows": [],
    }


def _governance_dependency(
    constitution: dict[str, Any] | None,
    registry: dict[str, Any] | None,
    failure: RealmAgentDependencyFailure,
) -> dict[str, Any]:
    result = _governance_terminal(
        "dependency_error",
        constitution=constitution,
        registry=registry,
        issues=[
            _issue(
                "dependency_error",
                "A dependency prevented a trustworthy realm-agent decision.",
            )
        ],
    )
    result["dependency"] = failure.as_dict()
    return result


def _get_terminal_result(
    realm_id: str,
    slug: str,
    governance_status: str,
    resolution: str,
    issues: list[dict[str, Any]],
    dependency: dict[str, Any] | None,
    *,
    complete: bool,
    validity: str = "unknown",
    resident_state: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "realm_id": realm_id,
        "slug": slug,
        "governance_status": governance_status,
        "resolution": resolution,
        "resident_state": resident_state,
        "validity": validity,
        "boot_allowed": False,
        "complete_for_registry": complete,
        "issues": issues,
        "dependency": dependency,
    }


def _get_dependency_result(
    realm_id: str,
    slug: str,
    failure: RealmAgentDependencyFailure,
) -> dict[str, Any]:
    return _get_terminal_result(
        realm_id,
        slug,
        "dependency_error",
        "dependency_error",
        [
            _issue(
                "dependency_error",
                "A dependency prevented a trustworthy realm-agent decision.",
            )
        ],
        failure.as_dict(),
        complete=False,
    )


def _list_input_error(realm_id: str, issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "realm_id": str(realm_id or ""),
        "governance_status": "input_error",
        "constitution": None,
        "registry": None,
        "agents": [],
        "counts": None,
        "complete_for_registry": False,
        "unregistered_charters_enumerated": False,
        "issues": [issue],
        "dependency": None,
    }


def _get_input_error(realm_id: str, slug: str, issue: dict[str, Any]) -> dict[str, Any]:
    return _get_terminal_result(
        str(realm_id or ""),
        str(slug or ""),
        "input_error",
        "input_error",
        [issue],
        None,
        complete=False,
    )


def _validate_realm_id(realm_id: str) -> tuple[str, dict[str, Any] | None]:
    value = "" if realm_id is None else str(realm_id)
    if not value or not value.strip():
        return value, _issue("realm_id_required", "realm_id is required.")
    if not _UUID_RE.fullmatch(value):
        return value, _issue(
            "realm_id_invalid_uuid", "realm_id must be a canonical hyphenated UUID."
        )
    return value.lower(), None


def _validate_slug(slug: str) -> dict[str, Any] | None:
    value = "" if slug is None else str(slug)
    if not value or not value.strip():
        return _issue("slug_required", "slug is required.")
    if not _valid_slug_text(value):
        return _issue(
            "slug_invalid_format", "slug must be one safe ASCII path segment."
        )
    return None


def _valid_slug_text(slug: str) -> bool:
    return len(slug) <= 64 and slug.isascii() and bool(_SLUG_RE.fullmatch(slug))


def _charter_path(slug: str) -> str:
    return f"realm/agents/{slug}/charter"


def _normalize_resident_state(source_state: str) -> str | None:
    if source_state == "активен":
        return "active"
    if source_state == "приостановлен":
        return "suspended"
    return None


def _split_table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _normalized_table_cells(line: str) -> list[str] | None:
    cells = _split_table_cells(line)
    if cells is None:
        return None
    return [_strip_code_cell(cell) for cell in cells]


def _is_separator_row(line: str) -> bool:
    cells = _split_table_cells(line)
    return bool(
        cells
        and len(cells) == 6
        and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)
    )


def _strip_code_cell(value: str) -> str:
    stripped = str(value).strip()
    if len(stripped) >= 2 and stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1]
    return stripped


def _issue(
    code: str,
    message: str,
    row_index: int | None = None,
) -> dict[str, Any]:
    issue: dict[str, Any] = {"code": code}
    if row_index is not None:
        issue["row_index"] = row_index
    issue["message"] = message
    return issue


def _append_issue(row: dict[str, Any], code: str, message: str) -> None:
    if any(issue["code"] == code for issue in row["issues"]):
        return
    row["issues"].append(_issue(code, message, row["row_index"]))


def _format_result(tool: str, data: dict[str, Any]) -> str:
    text = _serialize_result(tool, data)
    if len(text.encode("utf-8")) <= MAX_RESULT_BYTES:
        return text
    compact = _response_limit_result(
        tool, str(data.get("realm_id", "")), str(data.get("slug", ""))
    )
    compact_text = _serialize_result(tool, compact)
    if len(compact_text.encode("utf-8")) > MAX_RESULT_BYTES:
        raise RuntimeError(
            "Compact realm-agent response exceeds the approved byte limit."
        )
    return compact_text


def _serialize_result(tool: str, data: dict[str, Any]) -> str:
    if tool == "list":
        summary = "Realm-agent registry validation completed."
        label = LIST_LABEL
    else:
        summary = "Realm-agent validation completed."
        label = GET_LABEL
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"{summary}\n{label}\n{payload}"


def _response_limit_result(tool: str, realm_id: str, slug: str) -> dict[str, Any]:
    issue = _issue(
        "response_size_limit_exceeded",
        "The complete realm-agent result exceeds the approved P0 byte limit.",
    )
    if tool == "get":
        return _get_terminal_result(
            realm_id,
            slug,
            "invalid_governance_state",
            "invalid_governance_state",
            [issue],
            None,
            complete=False,
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "realm_id": realm_id,
        "governance_status": "invalid_governance_state",
        "constitution": None,
        "registry": None,
        "agents": [],
        "counts": None,
        "complete_for_registry": False,
        "unregistered_charters_enumerated": False,
        "issues": [issue],
        "dependency": None,
    }
