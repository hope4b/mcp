from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

SCHEMA_VERSION = "1"
CONSTITUTION_PATH = "realm/agents/constitution"
REGISTRY_PATH = "realm/agents/registry"
MAX_REGISTRY_ENTRIES = 32
MAX_RESULT_BYTES = 65536

LIST_LABEL = "Realm agent registry data:"
GET_LABEL = "Realm agent data:"
PREFLIGHT_LABEL = "Realm agent governance proposal preflight data:"

_UUID_RE = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
)
_UUID_SEARCH_RE = re.compile(
    r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"
)
_SLUG_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
_UTC_INSTANT_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{3}(?:[0-9]{3}){0,2})?Z$"
)
_CHARTER_PATH_RE = re.compile(
    r"^realm/agents/(?P<slug>[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)/charter$"
)
_V1_REGISTRY_HEADER = ["slug", "Роль", "Зона путей", "Режим", "Чартер", "Состояние"]
_V2_REGISTRY_HEADER = [
    "slug",
    "purpose",
    "territory",
    "mode",
    "charter_path",
    "state",
]
_V1_GOVERNANCE_CONTRACT = (
    "realm_agent_governance_v1",
    1,
    "agent_population_genesis_v1",
    1,
)
_V2_GOVERNANCE_CONTRACT = (
    "realm_agent_governance_v2",
    2,
    "agent_population_genesis_v2",
    2,
)
_V2_ADMISSION_POLICY = "owner_confirmed_single_role_admission_v1"
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
ExactArtifactReader = Callable[[str], dict[str, Any]]


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


class GovernancePreflightArtifactMissing(Exception):
    def __init__(
        self,
        operation: str,
        *,
        artifact_path: str | None = None,
        artifact_id: str | None = None,
    ) -> None:
        super().__init__(operation)
        self.operation = operation
        self.artifact_path = artifact_path
        self.artifact_id = artifact_id


class GovernancePreflightDependencyFailure(Exception):
    def __init__(
        self,
        kind: str,
        operation: str,
        *,
        artifact_path: str | None = None,
        artifact_id: str | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(kind)
        self.kind = kind
        self.operation = operation
        self.artifact_path = artifact_path
        self.artifact_id = artifact_id
        self.http_status = http_status

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "operation": self.operation,
            "artifact_path": self.artifact_path,
            "artifact_id": self.artifact_id,
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
    proposal_artifact_id: str = "",
    dependency_operation: str = "read_accepted_constitution",
    dependency_artifact_id: str | None = None,
) -> str:
    normalized_realm_id, issue = _validate_realm_id(realm_id)
    output_realm_id = normalized_realm_id if issue is None else str(realm_id or "")
    if tool_name == "preflight_realm_agent_governance_proposal":
        failure = GovernancePreflightDependencyFailure(
            "timeout",
            dependency_operation,
            artifact_path=artifact_path or None,
            artifact_id=dependency_artifact_id,
        )
        return _format_preflight_result(
            _preflight_failure(
                output_realm_id,
                str(proposal_artifact_id or ""),
                "dependency_error",
                "dependency_error",
                "dependency_error",
                "A dependency prevented a trustworthy governance preflight.",
                dependency=failure.as_dict(),
            )
        )

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


def preflight_realm_agent_governance_proposal_result(
    realm_id: str,
    proposal_artifact_id: str,
    read_artifact_by_id: ExactArtifactReader,
    read_accepted_artifact: ArtifactReader,
) -> str:
    normalized_realm_id, realm_issue = _validate_preflight_uuid(
        realm_id,
        "realm_id",
    )
    if realm_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                str(realm_id or ""),
                str(proposal_artifact_id or ""),
                "input_error",
                "unknown",
                realm_issue["code"],
                realm_issue["message"],
            )
        )

    normalized_proposal_id, proposal_id_issue = _validate_preflight_uuid(
        proposal_artifact_id,
        "proposal_artifact_id",
    )
    if proposal_id_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                str(proposal_artifact_id or ""),
                "input_error",
                "unknown",
                proposal_id_issue["code"],
                proposal_id_issue["message"],
            )
        )

    try:
        proposal_artifact = read_artifact_by_id(normalized_proposal_id)
    except GovernancePreflightArtifactMissing:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "proposal_unavailable",
                "unknown",
                "proposal_missing",
                "The exact proposed governance artifact is unavailable.",
            )
        )
    except GovernancePreflightDependencyFailure as failure:
        return _format_preflight_result(
            _dependency_preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                failure,
            )
        )

    proposal_identity = _trusted_uuid_field(proposal_artifact, "artifact_id")
    if proposal_identity is None:
        return _format_preflight_result(
            _invalid_response_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "read_proposal_by_id",
                artifact_id=normalized_proposal_id,
            )
        )
    if proposal_identity != normalized_proposal_id:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_proposal",
                "unknown",
                "proposal_artifact_id_mismatch",
                "The exact-id response returned a different proposal artifact id.",
            )
        )

    required_proposal_types = {
        "artifact_path": str,
        "realm_id": str,
        "scope_kind": str,
        "scope_id": str,
        "status": str,
        "artifact_kind": str,
        "write_mode": str,
        "updated_at": str,
        "source_context": dict,
    }
    if (
        not isinstance(proposal_artifact, dict)
        or any(
            not isinstance(proposal_artifact.get(field), expected)
            for field, expected in required_proposal_types.items()
        )
        or (
            proposal_artifact.get("supersedes_artifact_id") is not None
            and not isinstance(proposal_artifact.get("supersedes_artifact_id"), str)
        )
    ):
        return _format_preflight_result(
            _invalid_response_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "read_proposal_by_id",
                artifact_id=normalized_proposal_id,
            )
        )

    proposal = _proposal_projection(proposal_artifact)
    proposal_envelope_issue = _validate_proposal_envelope(
        proposal_artifact,
        normalized_realm_id,
    )
    if proposal_envelope_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_proposal",
                "unknown",
                proposal_envelope_issue["code"],
                proposal_envelope_issue["message"],
                proposal=proposal,
            )
        )

    submitted_at = _parse_utc_instant(str(proposal_artifact["updated_at"]))
    if submitted_at is None:
        proposal["proposal_submitted_at"] = None
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_proposal",
                "unknown",
                "proposal_submitted_at_invalid",
                "The proposal submit timestamp is not a supported server UTC instant.",
                proposal=proposal,
            )
        )

    capture, capture_issue = _parse_submit_electorate_capture(proposal_artifact)
    if capture_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_proposal",
                "unknown",
                capture_issue["code"],
                capture_issue["message"],
                proposal=proposal,
            )
        )
    assert capture is not None
    capture_projection = {
        "source_field": (
            "source_context.realm_agent_governance_submit."
            "electorate_registry_artifact_id"
        ),
        "registry_artifact_id": capture,
        "proposal_submitted_at": proposal_artifact["updated_at"],
    }

    try:
        captured_registry_artifact = read_artifact_by_id(capture)
    except GovernancePreflightArtifactMissing:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_current_governance",
                "governance_unavailable",
                "submit_electorate_registry_missing",
                "The captured submit-time electorate registry is unavailable.",
                proposal=proposal,
                submit_electorate_capture=capture_projection,
            )
        )
    except GovernancePreflightDependencyFailure as failure:
        return _format_preflight_result(
            _dependency_preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                failure,
                proposal=proposal,
                submit_electorate_capture=capture_projection,
            )
        )

    captured_identity = _trusted_uuid_field(
        captured_registry_artifact,
        "artifact_id",
    )
    if captured_identity is None:
        return _format_preflight_result(
            _invalid_response_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "read_submit_electorate_registry_by_id",
                artifact_path=REGISTRY_PATH,
                artifact_id=capture,
                proposal=proposal,
                submit_electorate_capture=capture_projection,
            )
        )
    if captured_identity != capture:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_current_governance",
                "invalid_governance_state",
                "submit_electorate_registry_artifact_id_mismatch",
                "The captured registry exact-id response returned a different artifact id.",
                proposal=proposal,
                submit_electorate_capture=capture_projection,
            )
        )

    required_registry_types = {
        "artifact_path": str,
        "realm_id": str,
        "scope_kind": str,
        "scope_id": str,
        "status": str,
        "artifact_kind": str,
        "write_mode": str,
        "body": str,
        "accepted_at": str,
    }
    if (
        not isinstance(captured_registry_artifact, dict)
        or any(
            not isinstance(captured_registry_artifact.get(field), expected)
            for field, expected in required_registry_types.items()
        )
        or "superseded_at" not in captured_registry_artifact
        or (
            captured_registry_artifact.get("superseded_at") is not None
            and not isinstance(captured_registry_artifact.get("superseded_at"), str)
        )
    ):
        return _format_preflight_result(
            _invalid_response_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "read_submit_electorate_registry_by_id",
                artifact_path=REGISTRY_PATH,
                artifact_id=capture,
                proposal=proposal,
                submit_electorate_capture=capture_projection,
            )
        )

    captured_envelope_issue = _validate_governance_envelope(
        captured_registry_artifact,
        normalized_realm_id,
        REGISTRY_PATH,
        "registry",
        allowed_statuses={"accepted", "superseded"},
    )
    if captured_envelope_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_current_governance",
                "invalid_governance_state",
                captured_envelope_issue["code"],
                captured_envelope_issue["message"],
                proposal=proposal,
                submit_electorate_capture=capture_projection,
            )
        )

    accepted_at = _parse_utc_instant(captured_registry_artifact["accepted_at"])
    if accepted_at is None:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_current_governance",
                "invalid_governance_state",
                "submit_electorate_registry_accepted_at_invalid",
                "The captured registry accepted_at value is not a supported server UTC instant.",
                proposal=proposal,
                submit_electorate_capture=capture_projection,
            )
        )

    superseded_text = captured_registry_artifact.get("superseded_at")
    superseded_at = (
        _parse_utc_instant(superseded_text)
        if isinstance(superseded_text, str)
        else None
    )
    if isinstance(superseded_text, str) and superseded_at is None:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_current_governance",
                "invalid_governance_state",
                "submit_electorate_registry_superseded_at_invalid",
                "The captured registry superseded_at value is not a supported server UTC instant.",
                proposal=proposal,
                submit_electorate_capture=capture_projection,
            )
        )

    status = captured_registry_artifact["status"]
    current_at_submit = bool(
        accepted_at <= submitted_at
        and (
            superseded_at is None
            or (
                superseded_at > accepted_at
                and submitted_at < superseded_at
            )
        )
        and (
            (status == "accepted" and superseded_text is None)
            or (status == "superseded" and superseded_text is not None)
        )
    )
    electorate_projection = {
        "artifact_id": capture,
        "artifact_path": REGISTRY_PATH,
        "status": status,
        "accepted_at": captured_registry_artifact["accepted_at"],
        "superseded_at": superseded_text,
        "current_at_proposal_submit": current_at_submit,
    }
    if not current_at_submit:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_proposal",
                "invalid_governance_state",
                "submit_electorate_not_current_at_submit",
                "The captured registry was not provably current when the proposal was submitted.",
                proposal=proposal,
                submit_electorate_capture=capture_projection,
                electorate_registry=electorate_projection,
            )
        )

    if (
        proposal_artifact["artifact_path"] == CONSTITUTION_PATH
        and proposal_artifact["body"] == ""
    ):
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_proposal",
                "unknown",
                "proposal_body_invalid",
                "The Constitution proposal body must not be empty.",
                proposal=proposal,
                proposal_kind="constitution",
                submit_electorate_capture=capture_projection,
                electorate_registry=electorate_projection,
            )
        )

    proposal["proposal_body_sha256"] = sha256(
        proposal_artifact["body"].encode("utf-8")
    ).hexdigest()

    try:
        constitution = read_accepted_artifact(CONSTITUTION_PATH)
    except GovernancePreflightArtifactMissing:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_current_governance",
                "governance_unavailable",
                "constitution_missing",
                "The accepted/current realm-agent constitution is unavailable.",
                proposal=proposal,
                submit_electorate_capture=capture_projection,
                electorate_registry=electorate_projection,
            )
        )
    except GovernancePreflightDependencyFailure as failure:
        return _format_preflight_result(
            _dependency_preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                failure,
                proposal=proposal,
                submit_electorate_capture=capture_projection,
                electorate_registry=electorate_projection,
            )
        )

    constitution_invalid = _untrusted_governance_record_failure(
        constitution,
        normalized_realm_id,
        normalized_proposal_id,
        "read_accepted_constitution",
        CONSTITUTION_PATH,
        proposal,
        capture_projection,
        electorate_projection,
    )
    if constitution_invalid is not None:
        return _format_preflight_result(constitution_invalid)
    constitution_issue = _validate_governance_envelope(
        constitution,
        normalized_realm_id,
        CONSTITUTION_PATH,
        "constitution",
        allowed_statuses={"accepted"},
    )
    if constitution_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_current_governance",
                "invalid_governance_state",
                constitution_issue["code"],
                constitution_issue["message"],
                proposal=proposal,
                submit_electorate_capture=capture_projection,
                electorate_registry=electorate_projection,
            )
        )

    registry_rows = _parse_registry(captured_registry_artifact["body"])
    registry_issue = _first_registry_issue(registry_rows)
    if registry_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                normalized_realm_id,
                normalized_proposal_id,
                "invalid_current_governance",
                "invalid_governance_state",
                registry_issue["code"],
                registry_issue["message"],
                proposal=proposal,
                submit_electorate_capture=capture_projection,
                electorate_registry=electorate_projection,
            )
        )
    assert registry_rows is not None

    charter_cache: dict[str, dict[str, Any]] = {}
    baseline_charters: dict[str, dict[str, Any]] = {}
    for row in registry_rows:
        charter_path = _charter_path(row["slug"])
        charter_result = _read_and_validate_preflight_charter(
            normalized_realm_id,
            normalized_proposal_id,
            charter_path,
            row["slug"],
            read_accepted_artifact,
            charter_cache,
            proposal,
            capture_projection,
            electorate_projection,
        )
        if isinstance(charter_result, str):
            return charter_result
        baseline_charters[row["slug"]] = charter_result

    target_path = proposal_artifact["artifact_path"]
    if target_path == CONSTITUTION_PATH:
        return _preflight_constitution_proposal(
            normalized_realm_id,
            normalized_proposal_id,
            proposal,
            capture_projection,
            electorate_projection,
            constitution,
        )
    if target_path == REGISTRY_PATH:
        return _preflight_registry_proposal(
            normalized_realm_id,
            normalized_proposal_id,
            proposal_artifact,
            proposal,
            capture_projection,
            electorate_projection,
            registry_rows,
            read_accepted_artifact,
            charter_cache,
        )
    return _preflight_charter_proposal(
        normalized_realm_id,
        normalized_proposal_id,
        proposal_artifact,
        proposal,
        capture_projection,
        electorate_projection,
        registry_rows,
        baseline_charters,
        read_accepted_artifact,
        charter_cache,
    )


def _validate_preflight_uuid(
    value: str,
    field: str,
) -> tuple[str, dict[str, Any] | None]:
    text = "" if value is None else str(value)
    if not text or not text.strip():
        return text, _issue(f"{field}_required", f"{field} is required.")
    if not _UUID_RE.fullmatch(text):
        return text, _issue(
            f"{field}_invalid",
            f"{field} must be a canonical hyphenated UUID.",
        )
    return text.lower(), None


def _trusted_uuid_field(artifact: Any, field: str) -> str | None:
    if not isinstance(artifact, dict):
        return None
    value = artifact.get(field)
    if not isinstance(value, str) or not _UUID_RE.fullmatch(value):
        return None
    return value.lower()


def _parse_utc_instant(value: str) -> datetime | None:
    if not isinstance(value, str) or not _UTC_INSTANT_RE.fullmatch(value):
        return None
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError:
        return None


def _proposal_projection(artifact: dict[str, Any]) -> dict[str, Any]:
    predecessor = artifact.get("supersedes_artifact_id")
    if isinstance(predecessor, str) and _UUID_RE.fullmatch(predecessor):
        predecessor = predecessor.lower()
    return {
        "artifact_id": str(artifact.get("artifact_id", "")).lower(),
        "artifact_path": artifact.get("artifact_path"),
        "status": artifact.get("status"),
        "artifact_kind": artifact.get("artifact_kind"),
        "write_mode": artifact.get("write_mode"),
        "supersedes_artifact_id": predecessor,
        "proposal_submitted_at": artifact.get("updated_at"),
        "proposal_body_sha256": None,
    }


def _validate_proposal_envelope(
    artifact: dict[str, Any],
    realm_id: str,
) -> dict[str, Any] | None:
    path = artifact["artifact_path"]
    if (
        path != CONSTITUTION_PATH
        and path != REGISTRY_PATH
        and (
            not isinstance(path, str)
            or _CHARTER_PATH_RE.fullmatch(path) is None
            or not _valid_slug_text(_CHARTER_PATH_RE.fullmatch(path).group("slug"))
        )
    ):
        return _issue(
            "proposal_path_unsupported",
            (
                "The proposal path is not a supported realm-agent Constitution, "
                "charter, or registry path."
            ),
        )
    if str(artifact["realm_id"]).lower() != realm_id:
        return _issue("proposal_realm_mismatch", "The proposal belongs to another realm.")
    if (
        artifact["scope_kind"] != "realm"
        or str(artifact["scope_id"]).lower() != realm_id
    ):
        return _issue(
            "proposal_scope_mismatch",
            "The proposal is not realm-scoped to the supplied realm.",
        )
    if artifact["status"] != "proposed":
        return _issue(
            "proposal_status_unsupported",
            "Only an exact proposed governance artifact is eligible.",
        )
    if artifact["artifact_kind"] != "decision":
        return _issue(
            "proposal_kind_mismatch",
            "A governance proposal must have artifact_kind=decision.",
        )
    if artifact["write_mode"] != "replace":
        return _issue(
            "proposal_write_mode_mismatch",
            "A governance proposal must have write_mode=replace.",
        )
    predecessor = artifact.get("supersedes_artifact_id")
    if predecessor is not None and not _UUID_RE.fullmatch(predecessor):
        return _issue(
            "proposal_predecessor_mismatch",
            "The supplied predecessor is not a canonical artifact UUID.",
        )
    if not isinstance(artifact["body"], str):
        return _issue("proposal_body_invalid", "The proposal body must be a string.")
    return None


def _parse_submit_electorate_capture(
    artifact: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None]:
    source_context = artifact.get("source_context")
    if not isinstance(source_context, dict) or "realm_agent_governance_submit" not in source_context:
        return None, _issue(
            "submit_electorate_missing",
            "The immutable submit-time electorate capture is missing.",
        )
    capture = source_context.get("realm_agent_governance_submit")
    if not isinstance(capture, dict):
        return None, _issue(
            "submit_electorate_invalid",
            "The submit-time electorate capture must be a closed object.",
        )
    if set(capture) != {"schema_version", "electorate_registry_artifact_id"}:
        return None, _issue(
            "submit_electorate_invalid",
            "The submit-time electorate capture has missing or extra fields.",
        )
    registry_id = capture.get("electorate_registry_artifact_id")
    if (
        capture.get("schema_version") != SCHEMA_VERSION
        or not isinstance(registry_id, str)
        or not _UUID_RE.fullmatch(registry_id)
    ):
        return None, _issue(
            "submit_electorate_invalid",
            "The submit-time electorate capture has an unsupported schema or registry id.",
        )
    return registry_id.lower(), None


def _validate_governance_envelope(
    artifact: dict[str, Any],
    realm_id: str,
    path: str,
    source: str,
    *,
    allowed_statuses: set[str],
) -> dict[str, Any] | None:
    if artifact.get("artifact_path") != path:
        return _issue(
            f"{source}_path_mismatch",
            f"The {source} artifact path does not match its required path.",
        )
    if str(artifact.get("realm_id", "")).lower() != realm_id:
        return _issue(
            f"{source}_realm_mismatch",
            f"The {source} artifact belongs to another realm.",
        )
    if (
        artifact.get("scope_kind") != "realm"
        or str(artifact.get("scope_id", "")).lower() != realm_id
    ):
        return _issue(
            f"{source}_scope_mismatch",
            f"The {source} artifact is not scoped to the supplied realm.",
        )
    if artifact.get("status") not in allowed_statuses:
        return _issue(
            f"{source}_status_unsupported",
            f"The {source} artifact has an unsupported lifecycle status.",
        )
    if artifact.get("artifact_kind") != "decision":
        return _issue(
            f"{source}_kind_mismatch",
            f"The {source} artifact must have artifact_kind=decision.",
        )
    if artifact.get("write_mode") != "replace":
        return _issue(
            f"{source}_write_mode_mismatch",
            f"The {source} artifact must have write_mode=replace.",
        )
    if not isinstance(artifact.get("body"), str) or not artifact.get("body"):
        return _issue(
            f"{source}_body_invalid",
            f"The {source} artifact body is missing or invalid.",
        )
    return None


def _untrusted_governance_record_failure(
    artifact: Any,
    realm_id: str,
    proposal_id: str,
    operation: str,
    artifact_path: str,
    proposal: dict[str, Any],
    capture: dict[str, Any],
    electorate: dict[str, Any],
) -> dict[str, Any] | None:
    required = {
        "artifact_id": str,
        "artifact_path": str,
        "realm_id": str,
        "scope_kind": str,
        "scope_id": str,
        "status": str,
        "artifact_kind": str,
        "write_mode": str,
        "body": str,
    }
    if not isinstance(artifact, dict) or any(
        not isinstance(artifact.get(field), expected)
        for field, expected in required.items()
    ) or _trusted_uuid_field(artifact, "artifact_id") is None:
        return _invalid_response_failure(
            realm_id,
            proposal_id,
            operation,
            artifact_path=artifact_path,
            proposal=proposal,
            submit_electorate_capture=capture,
            electorate_registry=electorate,
        )
    return None


def _first_registry_issue(
    rows: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if rows is None:
        return _issue(
            "registry_unparseable",
            "The canonical registry table cannot be parsed deterministically.",
        )
    if len(rows) > MAX_REGISTRY_ENTRIES:
        return _issue(
            "registry_size_limit_exceeded",
            "The realm-agent registry exceeds the approved row limit.",
        )
    _add_duplicate_issues(rows)
    for row in rows:
        _finish_row(row)
        if row["issues"]:
            return row["issues"][0]
    return None


def _read_and_validate_preflight_charter(
    realm_id: str,
    proposal_id: str,
    charter_path: str,
    expected_slug: str,
    reader: ArtifactReader,
    cache: dict[str, dict[str, Any]],
    proposal: dict[str, Any],
    capture: dict[str, Any],
    electorate: dict[str, Any],
) -> dict[str, Any] | str:
    if charter_path in cache:
        return cache[charter_path]
    try:
        artifact = reader(charter_path)
    except GovernancePreflightArtifactMissing:
        return _format_preflight_result(
            _preflight_failure(
                realm_id,
                proposal_id,
                "invalid_current_governance",
                "governance_unavailable",
                "charter_missing",
                "A charter required by the captured registry is unavailable.",
                proposal=proposal,
                submit_electorate_capture=capture,
                electorate_registry=electorate,
            )
        )
    except GovernancePreflightDependencyFailure as failure:
        return _format_preflight_result(
            _dependency_preflight_failure(
                realm_id,
                proposal_id,
                failure,
                proposal=proposal,
                submit_electorate_capture=capture,
                electorate_registry=electorate,
            )
        )
    untrusted = _untrusted_governance_record_failure(
        artifact,
        realm_id,
        proposal_id,
        "read_accepted_charter",
        charter_path,
        proposal,
        capture,
        electorate,
    )
    if untrusted is not None:
        return _format_preflight_result(untrusted)
    envelope_issue = _validate_governance_envelope(
        artifact,
        realm_id,
        charter_path,
        "charter",
        allowed_statuses={"accepted"},
    )
    if envelope_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                realm_id,
                proposal_id,
                "invalid_current_governance",
                "invalid_governance_state",
                envelope_issue["code"],
                envelope_issue["message"],
                proposal=proposal,
                submit_electorate_capture=capture,
                electorate_registry=electorate,
            )
        )
    metadata = _parse_charter_metadata(artifact["body"])
    if metadata is None:
        issue = _issue(
            "charter_unparseable",
            "Required charter metadata is missing or ambiguous.",
        )
    elif metadata["artifact_path"] != charter_path:
        issue = _issue(
            "charter_path_mismatch",
            "Charter metadata reports a different artifact path.",
        )
    elif metadata["slug"] != expected_slug:
        issue = _issue(
            "charter_slug_mismatch",
            "Charter metadata reports a different slug.",
        )
    elif metadata["realm_id"].lower() != realm_id:
        issue = _issue(
            "charter_realm_mismatch",
            "Charter metadata reports a different realm.",
        )
    else:
        issue = None
    if issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                realm_id,
                proposal_id,
                "invalid_current_governance",
                "invalid_governance_state",
                issue["code"],
                issue["message"],
                proposal=proposal,
                submit_electorate_capture=capture,
                electorate_registry=electorate,
            )
        )
    cache[charter_path] = artifact
    return artifact


def _preflight_constitution_proposal(
    realm_id: str,
    proposal_id: str,
    proposal: dict[str, Any],
    capture: dict[str, Any],
    electorate: dict[str, Any],
    constitution: dict[str, Any],
) -> str:
    expected = {
        "required": True,
        "artifact_id": str(constitution["artifact_id"]).lower(),
        "source": "current_constitution",
    }
    predecessor_issue = _predecessor_issue(
        proposal.get("supersedes_artifact_id"),
        expected,
    )
    if predecessor_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                realm_id,
                proposal_id,
                "invalid_proposal",
                "valid",
                predecessor_issue["code"],
                predecessor_issue["message"],
                proposal=proposal,
                proposal_kind="constitution",
                expected_predecessor=expected,
                submit_electorate_capture=capture,
                electorate_registry=electorate,
            )
        )
    return _format_preflight_result(
        _preflight_success(
            realm_id,
            proposal_id,
            "constitution",
            proposal,
            expected,
            None,
            capture,
            electorate,
        )
    )


def _preflight_charter_proposal(
    realm_id: str,
    proposal_id: str,
    artifact: dict[str, Any],
    proposal: dict[str, Any],
    capture: dict[str, Any],
    electorate: dict[str, Any],
    registry_rows: list[dict[str, Any]],
    baseline_charters: dict[str, dict[str, Any]],
    read_accepted_artifact: ArtifactReader,
    charter_cache: dict[str, dict[str, Any]],
) -> str:
    path_match = _CHARTER_PATH_RE.fullmatch(artifact["artifact_path"])
    assert path_match is not None
    slug = path_match.group("slug")
    metadata = _parse_charter_metadata(artifact["body"])
    if metadata is None:
        return _invalid_proposal_result(
            realm_id,
            proposal_id,
            "charter_unparseable",
            "Required charter metadata is missing or ambiguous.",
            proposal,
            capture,
            electorate,
            charter_slug=slug,
        )
    if metadata["artifact_path"] != artifact["artifact_path"]:
        return _invalid_proposal_result(
            realm_id,
            proposal_id,
            "charter_path_mismatch",
            "Charter metadata reports a different artifact path.",
            proposal,
            capture,
            electorate,
            charter_slug=slug,
        )
    if metadata["slug"] != slug:
        return _invalid_proposal_result(
            realm_id,
            proposal_id,
            "charter_slug_mismatch",
            "Charter metadata reports a different slug.",
            proposal,
            capture,
            electorate,
            charter_slug=slug,
        )
    if metadata["realm_id"].lower() != realm_id:
        return _invalid_proposal_result(
            realm_id,
            proposal_id,
            "charter_realm_mismatch",
            "Charter metadata reports a different realm.",
            proposal,
            capture,
            electorate,
            charter_slug=slug,
        )

    matching_rows = [row for row in registry_rows if row["slug"] == slug]
    if matching_rows:
        expected = {
            "required": True,
            "artifact_id": str(baseline_charters[slug]["artifact_id"]).lower(),
            "source": "current_registered_charter",
        }
        proposal_kind = "resident_charter_amendment"
    else:
        path = artifact["artifact_path"]
        try:
            existing = (
                charter_cache[path]
                if path in charter_cache
                else read_accepted_artifact(path)
            )
        except GovernancePreflightArtifactMissing:
            existing = None
        except GovernancePreflightDependencyFailure as failure:
            return _format_preflight_result(
                _dependency_preflight_failure(
                    realm_id,
                    proposal_id,
                    failure,
                    proposal=proposal,
                    submit_electorate_capture=capture,
                    electorate_registry=electorate,
                )
            )
        if existing is None:
            expected = {
                "required": False,
                "artifact_id": None,
                "source": "none",
            }
            proposal_kind = "candidate_charter"
        else:
            untrusted = _untrusted_governance_record_failure(
                existing,
                realm_id,
                proposal_id,
                "read_accepted_charter",
                path,
                proposal,
                capture,
                electorate,
            )
            if untrusted is not None:
                return _format_preflight_result(untrusted)
            envelope_issue = _validate_governance_envelope(
                existing,
                realm_id,
                path,
                "charter",
                allowed_statuses={"accepted"},
            )
            if envelope_issue is not None:
                return _format_preflight_result(
                    _preflight_failure(
                        realm_id,
                        proposal_id,
                        "invalid_current_governance",
                        "invalid_governance_state",
                        envelope_issue["code"],
                        envelope_issue["message"],
                        proposal=proposal,
                        submit_electorate_capture=capture,
                        electorate_registry=electorate,
                    )
                )
            expected = {
                "required": True,
                "artifact_id": str(existing["artifact_id"]).lower(),
                "source": "current_unregistered_charter",
            }
            proposal_kind = "candidate_charter_repair"

    predecessor_issue = _predecessor_issue(
        proposal.get("supersedes_artifact_id"),
        expected,
    )
    if predecessor_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                realm_id,
                proposal_id,
                "invalid_proposal",
                "valid",
                predecessor_issue["code"],
                predecessor_issue["message"],
                proposal=proposal,
                proposal_kind=proposal_kind,
                expected_predecessor=expected,
                charter_slug=slug,
                submit_electorate_capture=capture,
                electorate_registry=electorate,
            )
        )
    return _format_preflight_result(
        _preflight_success(
            realm_id,
            proposal_id,
            proposal_kind,
            proposal,
            expected,
            slug,
            capture,
            electorate,
        )
    )


def _preflight_registry_proposal(
    realm_id: str,
    proposal_id: str,
    artifact: dict[str, Any],
    proposal: dict[str, Any],
    capture: dict[str, Any],
    electorate: dict[str, Any],
    captured_rows: list[dict[str, Any]],
    read_accepted_artifact: ArtifactReader,
    charter_cache: dict[str, dict[str, Any]],
) -> str:
    proposed_rows = _parse_registry(artifact["body"])
    proposed_issue = _first_registry_issue(proposed_rows)
    if proposed_issue is not None:
        return _invalid_proposal_result(
            realm_id,
            proposal_id,
            proposed_issue["code"],
            proposed_issue["message"],
            proposal,
            capture,
            electorate,
            proposal_kind="registry_amendment",
        )
    assert proposed_rows is not None
    proposed_slugs = {row["slug"] for row in proposed_rows}
    if any(row["slug"] not in proposed_slugs for row in captured_rows):
        return _invalid_proposal_result(
            realm_id,
            proposal_id,
            "registry_resident_removed",
            "A registry proposal must retain every current resident slug.",
            proposal,
            capture,
            electorate,
            proposal_kind="registry_amendment",
        )

    for row in proposed_rows:
        charter_path = _charter_path(row["slug"])
        result = _read_and_validate_preflight_charter(
            realm_id,
            proposal_id,
            charter_path,
            row["slug"],
            read_accepted_artifact,
            charter_cache,
            proposal,
            capture,
            electorate,
        )
        if isinstance(result, str):
            return result

    try:
        current_registry = read_accepted_artifact(REGISTRY_PATH)
    except GovernancePreflightArtifactMissing:
        return _format_preflight_result(
            _preflight_failure(
                realm_id,
                proposal_id,
                "invalid_current_governance",
                "governance_unavailable",
                "registry_missing",
                "The accepted/current realm-agent registry is unavailable.",
                proposal=proposal,
                proposal_kind="registry_amendment",
                submit_electorate_capture=capture,
                electorate_registry=electorate,
            )
        )
    except GovernancePreflightDependencyFailure as failure:
        return _format_preflight_result(
            _dependency_preflight_failure(
                realm_id,
                proposal_id,
                failure,
                proposal=proposal,
                submit_electorate_capture=capture,
                electorate_registry=electorate,
            )
        )
    untrusted = _untrusted_governance_record_failure(
        current_registry,
        realm_id,
        proposal_id,
        "read_accepted_registry",
        REGISTRY_PATH,
        proposal,
        capture,
        electorate,
    )
    if untrusted is not None:
        return _format_preflight_result(untrusted)
    envelope_issue = _validate_governance_envelope(
        current_registry,
        realm_id,
        REGISTRY_PATH,
        "registry",
        allowed_statuses={"accepted"},
    )
    if envelope_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                realm_id,
                proposal_id,
                "invalid_current_governance",
                "invalid_governance_state",
                envelope_issue["code"],
                envelope_issue["message"],
                proposal=proposal,
                proposal_kind="registry_amendment",
                submit_electorate_capture=capture,
                electorate_registry=electorate,
            )
        )

    expected = {
        "required": True,
        "artifact_id": electorate["artifact_id"],
        "source": "current_registry",
    }
    predecessor_issue = _predecessor_issue(
        proposal.get("supersedes_artifact_id"),
        expected,
    )
    if (
        predecessor_issue is None
        and str(current_registry["artifact_id"]).lower() != electorate["artifact_id"]
    ):
        predecessor_issue = _issue(
            "proposal_predecessor_mismatch",
            "The registry proposal predecessor is no longer accepted/current.",
        )
    if predecessor_issue is not None:
        return _format_preflight_result(
            _preflight_failure(
                realm_id,
                proposal_id,
                "invalid_proposal",
                "valid",
                predecessor_issue["code"],
                predecessor_issue["message"],
                proposal=proposal,
                proposal_kind="registry_amendment",
                expected_predecessor=expected,
                submit_electorate_capture=capture,
                electorate_registry=electorate,
            )
        )
    return _format_preflight_result(
        _preflight_success(
            realm_id,
            proposal_id,
            "registry_amendment",
            proposal,
            expected,
            None,
            capture,
            electorate,
        )
    )


def _predecessor_issue(
    actual: Any,
    expected: dict[str, Any],
) -> dict[str, Any] | None:
    if expected["required"] and actual is None:
        return _issue(
            "proposal_predecessor_missing",
            "The governance successor must name its exact predecessor.",
        )
    if not expected["required"] and actual is not None:
        return _issue(
            "proposal_predecessor_unexpected",
            "An initial candidate charter must not name a predecessor.",
        )
    if expected["required"] and (
        not isinstance(actual, str)
        or actual.lower() != expected["artifact_id"]
    ):
        return _issue(
            "proposal_predecessor_mismatch",
            "The supplied predecessor does not match the exact required artifact.",
        )
    return None


def _invalid_proposal_result(
    realm_id: str,
    proposal_id: str,
    code: str,
    message: str,
    proposal: dict[str, Any],
    capture: dict[str, Any],
    electorate: dict[str, Any],
    *,
    proposal_kind: str | None = None,
    charter_slug: str | None = None,
) -> str:
    return _format_preflight_result(
        _preflight_failure(
            realm_id,
            proposal_id,
            "invalid_proposal",
            "valid",
            code,
            message,
            proposal=proposal,
            proposal_kind=proposal_kind,
            charter_slug=charter_slug,
            submit_electorate_capture=capture,
            electorate_registry=electorate,
        )
    )


def _preflight_success(
    realm_id: str,
    proposal_id: str,
    proposal_kind: str,
    proposal: dict[str, Any],
    expected_predecessor: dict[str, Any],
    charter_slug: str | None,
    capture: dict[str, Any],
    electorate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "realm_id": realm_id,
        "proposal_artifact_id": proposal_id,
        "preflight_status": "pass",
        "preflight_passed": True,
        "proposal_kind": proposal_kind,
        "proposal": proposal,
        "expected_predecessor": expected_predecessor,
        "charter_slug": charter_slug,
        "submit_electorate_capture": capture,
        "electorate_registry": electorate,
        "current_governance_status": "valid",
        "issues": [],
        "dependency": None,
    }


def _preflight_failure(
    realm_id: str,
    proposal_id: str,
    status: str,
    governance_status: str,
    issue_code: str,
    issue_message: str,
    *,
    proposal_kind: str | None = None,
    proposal: dict[str, Any] | None = None,
    expected_predecessor: dict[str, Any] | None = None,
    charter_slug: str | None = None,
    submit_electorate_capture: dict[str, Any] | None = None,
    electorate_registry: dict[str, Any] | None = None,
    dependency: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "realm_id": realm_id,
        "proposal_artifact_id": proposal_id,
        "preflight_status": status,
        "preflight_passed": False,
        "proposal_kind": proposal_kind,
        "proposal": proposal,
        "expected_predecessor": expected_predecessor,
        "charter_slug": charter_slug,
        "submit_electorate_capture": submit_electorate_capture,
        "electorate_registry": electorate_registry,
        "current_governance_status": governance_status,
        "issues": [_issue(issue_code, issue_message)],
        "dependency": dependency,
    }


def _dependency_preflight_failure(
    realm_id: str,
    proposal_id: str,
    failure: GovernancePreflightDependencyFailure,
    *,
    proposal: dict[str, Any] | None = None,
    submit_electorate_capture: dict[str, Any] | None = None,
    electorate_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _preflight_failure(
        realm_id,
        proposal_id,
        "dependency_error",
        "dependency_error",
        "dependency_error",
        "A dependency prevented a trustworthy governance preflight.",
        proposal=proposal,
        submit_electorate_capture=submit_electorate_capture,
        electorate_registry=electorate_registry,
        dependency=failure.as_dict(),
    )


def _invalid_response_failure(
    realm_id: str,
    proposal_id: str,
    operation: str,
    *,
    artifact_path: str | None = None,
    artifact_id: str | None = None,
    proposal: dict[str, Any] | None = None,
    submit_electorate_capture: dict[str, Any] | None = None,
    electorate_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _dependency_preflight_failure(
        realm_id,
        proposal_id,
        GovernancePreflightDependencyFailure(
            "invalid_response",
            operation,
            artifact_path=artifact_path,
            artifact_id=artifact_id,
        ),
        proposal=proposal,
        submit_electorate_capture=submit_electorate_capture,
        electorate_registry=electorate_registry,
    )


def _format_preflight_result(data: dict[str, Any]) -> str:
    text = _serialize_preflight_result(data)
    if len(text.encode("utf-8")) <= MAX_RESULT_BYTES:
        return text
    compact = _preflight_failure(
        str(data.get("realm_id", "")),
        str(data.get("proposal_artifact_id", "")),
        "invalid_current_governance",
        "invalid_governance_state",
        "response_size_limit_exceeded",
        "The complete governance preflight result exceeds the approved byte limit.",
    )
    compact_text = _serialize_preflight_result(compact)
    if len(compact_text.encode("utf-8")) > MAX_RESULT_BYTES:
        raise RuntimeError(
            "Compact governance preflight response exceeds the approved byte limit."
        )
    return compact_text


def _serialize_preflight_result(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (
        "Realm-agent governance proposal preflight completed.\n"
        f"{PREFLIGHT_LABEL}\n{payload}"
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

    governance_contract = _governance_contract(
        constitution_artifact, registry_artifact
    )
    if governance_contract is None:
        parsed_rows = None
    else:
        parsed_rows = _parse_discovery_registry(
            str(registry_artifact["body"]),
            governance_contract,
            registry_artifact,
        )
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
            _validate_charter(
                row,
                charter_artifact,
                realm_id,
                expected_path,
                governance_contract,
            )
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


def _governance_contract(
    constitution: dict[str, Any], registry: dict[str, Any]
) -> str | None:
    constitution_envelope = _governance_envelope(constitution)
    registry_envelope = _governance_envelope(registry)

    if not isinstance(constitution_envelope, dict) or not isinstance(
        registry_envelope, dict
    ):
        return None

    constitution_contract = _envelope_contract(constitution_envelope)
    registry_contract = _envelope_contract(registry_envelope)
    if constitution_contract != registry_contract:
        return None
    if constitution_contract == _V1_GOVERNANCE_CONTRACT:
        if (
            constitution_envelope.get("document_kind") != "constitution"
            or registry_envelope.get("document_kind") != "registry"
        ):
            return None
        return "v1"
    if constitution_contract == _V2_GOVERNANCE_CONTRACT:
        constitution_document = constitution_envelope.get("document")
        registry_document = registry_envelope.get("document")
        if not isinstance(constitution_document, dict) or not isinstance(
            registry_document, dict
        ):
            return None
        if (
            constitution_document.get("document_kind") != "constitution"
            or constitution_document.get("admission_policy")
            != _V2_ADMISSION_POLICY
            or set(registry_document) != {
                "document_kind",
                "admission_policy",
                "entries",
            }
            or registry_document.get("document_kind") != "registry"
            or registry_document.get("admission_policy") != _V2_ADMISSION_POLICY
            or not isinstance(registry_document.get("entries"), list)
        ):
            return None
        return "v2"
    return None


def _governance_envelope(artifact: dict[str, Any]) -> dict[str, Any] | None:
    source_context = artifact.get("source_context")
    if not isinstance(source_context, dict):
        return None
    envelope = source_context.get("governance_document")
    if not isinstance(envelope, dict):
        return None
    contract = _envelope_contract(envelope)
    expected_keys = (
        {
            "document_contract",
            "schema_version",
            "document_kind",
            "realm_id",
            "artifact_path",
            "body_contract_id",
            "body_contract_version",
            "body_sha256",
            "document",
        }
        if contract == _V1_GOVERNANCE_CONTRACT
        else {
            "document_contract",
            "schema_version",
            "realm_id",
            "artifact_path",
            "body_contract_id",
            "body_contract_version",
            "body_sha256",
            "document",
        }
    )
    body = artifact.get("body")
    if (
        contract not in {_V1_GOVERNANCE_CONTRACT, _V2_GOVERNANCE_CONTRACT}
        or set(envelope) != expected_keys
        or envelope.get("realm_id") != artifact.get("realm_id")
        or envelope.get("artifact_path") != artifact.get("artifact_path")
        or not isinstance(body, str)
        or envelope.get("body_sha256")
        != sha256(body.encode("utf-8")).hexdigest()
        or not isinstance(envelope.get("document"), dict)
    ):
        return None
    return envelope


def _envelope_contract(envelope: dict[str, Any]) -> tuple[str, int, str, int] | None:
    schema_version = envelope.get("schema_version")
    body_contract_version = envelope.get("body_contract_version")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or isinstance(body_contract_version, bool)
        or not isinstance(body_contract_version, int)
    ):
        return None
    return (
        str(envelope.get("document_contract", "")),
        schema_version,
        str(envelope.get("body_contract_id", "")),
        body_contract_version,
    )


def _parse_registry(body: str) -> list[dict[str, Any]] | None:
    """Parse the established v1 registry contract used by governance preflight."""
    return _parse_registry_body(body, "v1")


def _parse_discovery_registry(
    body: str,
    governance_contract: str,
    registry_artifact: dict[str, Any],
) -> list[dict[str, Any]] | None:
    rows = _parse_registry_body(body, governance_contract)
    if rows is None:
        return None
    if governance_contract == "v2" and not _v2_rows_match_document(
        rows, registry_artifact
    ):
        return None
    return rows


def _parse_registry_body(
    body: str, governance_contract: str
) -> list[dict[str, Any]] | None:
    expected_header = (
        _V1_REGISTRY_HEADER if governance_contract == "v1" else _V2_REGISTRY_HEADER
    )
    lines = body.splitlines()
    header_indexes = [
        index
        for index, line in enumerate(lines)
        if _normalized_table_cells(line) == expected_header
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
        _parse_registry_row(line, index, governance_contract)
        for index, line in enumerate(physical_lines, 1)
    ]
    return rows


def _parse_registry_row(
    line: str, row_index: int, governance_contract: str
) -> dict[str, Any]:
    cells = (
        _split_table_cells(line)
        if governance_contract == "v1"
        else _split_v2_table_cells(line)
    )
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
        "resident_state": _normalize_resident_state(
            source_state, governance_contract
        ),
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


def _v2_rows_match_document(
    rows: list[dict[str, Any]], registry_artifact: dict[str, Any]
) -> bool:
    envelope = _governance_envelope(registry_artifact)
    if not isinstance(envelope, dict):
        return False
    document = envelope.get("document")
    if not isinstance(document, dict):
        return False
    entries = document.get("entries")
    if not isinstance(entries, list) or len(entries) != len(rows):
        return False
    expected_keys = {"slug", "purpose", "territory", "mode", "charter_path", "state"}
    for row, entry in zip(rows, entries, strict=True):
        if not isinstance(entry, dict) or set(entry) != expected_keys:
            return False
        if any(not isinstance(entry[key], str) for key in expected_keys):
            return False
        if (
            row["slug"] != entry["slug"]
            or row["role"] != entry["purpose"]
            or row["path_zone"] != entry["territory"]
            or row["mode"] != entry["mode"]
            or row["charter_path"] != entry["charter_path"]
            or row["source_state"] != entry["state"]
        ):
            return False
    return True


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
    governance_contract: str,
) -> None:
    if governance_contract == "v2":
        _validate_v2_charter(row, artifact)
        metadata = {
            "artifact_path": expected_path,
            "slug": row["slug"],
            "realm_id": realm_id,
        }
    else:
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


def _validate_v2_charter(row: dict[str, Any], artifact: dict[str, Any]) -> None:
    envelope = _governance_envelope(artifact)
    if not isinstance(envelope, dict) or _envelope_contract(
        envelope
    ) != _V2_GOVERNANCE_CONTRACT:
        _append_issue(
            row,
            "charter_unparseable",
            "The v2 charter governance document is missing or invalid.",
        )
        return
    document = envelope.get("document")
    expected_keys = {
        "document_kind",
        "slug",
        "charter_path",
        "constitution_path",
        "registry_path",
        "purpose",
        "territory",
        "mode",
    }
    if (
        not isinstance(document, dict)
        or set(document) != expected_keys
        or document.get("document_kind") != "resident_charter"
        or document.get("slug") != row["slug"]
        or document.get("charter_path") != row["charter_path"]
        or document.get("constitution_path") != CONSTITUTION_PATH
        or document.get("registry_path") != REGISTRY_PATH
        or document.get("purpose") != row["role"]
        or document.get("territory") != row["path_zone"]
        or document.get("mode") != row["mode"]
    ):
        _append_issue(
            row,
            "charter_unparseable",
            "The v2 charter governance document does not match its registry entry.",
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


def _normalize_resident_state(
    source_state: str, governance_contract: str = "v1"
) -> str | None:
    if governance_contract == "v2":
        return "active" if source_state == "active" else None
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


def _split_v2_table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells: list[str] = []
    cell: list[str] = []
    index = 1
    while index < len(stripped) - 1:
        character = stripped[index]
        if character == "\\":
            if index + 1 >= len(stripped) - 1 or stripped[index + 1] not in {
                "\\",
                "|",
            }:
                return None
            cell.append(stripped[index + 1])
            index += 2
            continue
        if character == "|":
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(character)
        index += 1
    cells.append("".join(cell).strip())
    return cells


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
