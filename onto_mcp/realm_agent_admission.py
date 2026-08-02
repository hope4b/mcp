from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, ValidationError

ADMISSION_PATH_TEMPLATE = "/realm/{realm_id}/agent-population/admissions"

_HASH_PATTERN = r"^[0-9a-f]{64}$"
_SLUG_PATTERN = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RealmAgentCharterDocumentV1(_ClosedModel):
    document_kind: Literal["resident_charter"]
    slug: str = Field(pattern=_SLUG_PATTERN, max_length=64)
    charter_path: str
    constitution_path: str
    registry_path: str
    purpose: str
    territory: str
    mode: Literal["execution"]


class RealmAgentRegistryEntryV1(_ClosedModel):
    slug: str = Field(pattern=_SLUG_PATTERN, max_length=64)
    purpose: str
    territory: str
    mode: Literal["execution"]
    charter_path: str
    state: Literal["active"]


class RealmAgentAdmissionCandidateV1(_ClosedModel):
    contract_id: Literal["realm_agent_admission_candidate_v1"]
    contract_version: Literal[1]
    realm_id: str
    expected_constitution_artifact_id: str
    expected_registry_artifact_id: str
    slug: str = Field(pattern=_SLUG_PATTERN, max_length=64)
    charter_body: str
    charter_body_sha256: str = Field(pattern=_HASH_PATTERN)
    charter_document: RealmAgentCharterDocumentV1
    registry_entry: RealmAgentRegistryEntryV1
    proposed_registry_body_sha256: str = Field(pattern=_HASH_PATTERN)


class RealmAgentAdmissionPredecessorSnapshot(_ClosedModel):
    constitution_artifact_id: str
    registry_artifact_id: str


class RealmAgentAdmissionCharter(_ClosedModel):
    artifact_id: str
    artifact_path: str
    status: Literal["accepted"]
    body_sha256: str = Field(pattern=_HASH_PATTERN)


class RealmAgentAdmissionRegistry(_ClosedModel):
    artifact_id: str
    artifact_path: Literal["realm/agents/registry"]
    status: Literal["accepted"]
    body_sha256: str = Field(pattern=_HASH_PATTERN)
    predecessor_artifact_id: str


class RealmAgentAdmissionResident(_ClosedModel):
    slug: str = Field(pattern=_SLUG_PATTERN, max_length=64)
    state: Literal["active"]
    validity: Literal["valid_active_resident"]
    boot_allowed: Literal[True]


class RealmAgentAdmitted(_ClosedModel):
    result: Literal["admitted"]
    candidate_fingerprint: str = Field(pattern=_HASH_PATTERN)
    predecessor_snapshot: RealmAgentAdmissionPredecessorSnapshot
    charter: RealmAgentAdmissionCharter
    registry: RealmAgentAdmissionRegistry
    resident: RealmAgentAdmissionResident
    writes_performed: Literal[True]
    strict_readback_passed: Literal[True]


class RealmAgentAlreadyAdmittedExact(_ClosedModel):
    result: Literal["already_admitted_exact"]
    candidate_fingerprint: str = Field(pattern=_HASH_PATTERN)
    predecessor_snapshot: RealmAgentAdmissionPredecessorSnapshot
    charter: RealmAgentAdmissionCharter
    registry: RealmAgentAdmissionRegistry
    resident: RealmAgentAdmissionResident
    writes_performed: Literal[False]
    strict_readback_passed: Literal[True]


class EmptyAdmissionErrorDetails(_ClosedModel):
    pass


class FieldRuleAdmissionErrorDetails(_ClosedModel):
    field: str
    rule: str


class FieldViolationAdmissionErrorDetails(_ClosedModel):
    field: str
    violation: str


class CharterRegistryMismatchDetails(_ClosedModel):
    charter_field: str
    registry_field: str


class RegistryDeltaInvalidDetails(_ClosedModel):
    violation: str


class UnsupportedAdmissionPolicyDetails(_ClosedModel):
    actual_contract: str | int
    actual_version: str | int
    actual_policy: str | int


class StaleGovernanceSnapshotDetails(_ClosedModel):
    expected_constitution_artifact_id: str
    current_constitution_artifact_id: str
    expected_registry_artifact_id: str
    current_registry_artifact_id: str


class ResidentSlugAlreadyRegisteredDetails(_ClosedModel):
    slug: str


class ResidentCharterPathOccupiedDetails(_ClosedModel):
    charter_path: str


class AgentAdmissionPartialStateConflictDetails(_ClosedModel):
    slug: str
    charter_path: str
    charter_present: bool
    registry_entry_present: bool


class AgentAdmissionDependencyUnavailableDetails(_ClosedModel):
    dependency: str
    phase: str


class AgentAdmissionStrictReadbackFailedDetails(_ClosedModel):
    phase: Literal["strict_readback"]


class OutcomeUnknownDetails(_ClosedModel):
    recovery: Literal["retry_exact_admission"]


class InvalidBackendResponseDetails(_ClosedModel):
    violation: Literal["closed_contract_mismatch"]


AdmissionErrorDetails: TypeAlias = (
    EmptyAdmissionErrorDetails
    | FieldRuleAdmissionErrorDetails
    | FieldViolationAdmissionErrorDetails
    | CharterRegistryMismatchDetails
    | RegistryDeltaInvalidDetails
    | UnsupportedAdmissionPolicyDetails
    | StaleGovernanceSnapshotDetails
    | ResidentSlugAlreadyRegisteredDetails
    | ResidentCharterPathOccupiedDetails
    | AgentAdmissionPartialStateConflictDetails
    | AgentAdmissionDependencyUnavailableDetails
    | AgentAdmissionStrictReadbackFailedDetails
    | OutcomeUnknownDetails
    | InvalidBackendResponseDetails
)

AdmissionErrorCode: TypeAlias = Literal[
    "malformed_resident_slug",
    "candidate_schema_invalid",
    "realm_id_mismatch",
    "charter_registry_mismatch",
    "registry_delta_invalid",
    "unsupported_agent_admission_policy",
    "stale_governance_snapshot",
    "resident_slug_already_registered",
    "resident_charter_path_occupied",
    "agent_admission_partial_state_conflict",
    "unauthenticated",
    "forbidden",
    "agent_admission_dependency_unavailable",
    "agent_admission_strict_readback_failed",
    "outcome_unknown",
    "invalid_backend_response",
]


class RealmAgentAdmissionError(_ClosedModel):
    code: AdmissionErrorCode
    backend_http_status: int | None
    retryable: bool
    correlation_id: str
    request_sent: bool
    response_received: bool
    details: AdmissionErrorDetails


RealmAgentAdmissionResponse: TypeAlias = (
    RealmAgentAdmitted | RealmAgentAlreadyAdmittedExact | RealmAgentAdmissionError
)


_SUCCESS_KEYS = [
    "result",
    "candidate_fingerprint",
    "predecessor_snapshot",
    "charter",
    "registry",
    "resident",
    "writes_performed",
    "strict_readback_passed",
]
_SUCCESS_NESTED_KEYS = {
    "predecessor_snapshot": ["constitution_artifact_id", "registry_artifact_id"],
    "charter": ["artifact_id", "artifact_path", "status", "body_sha256"],
    "registry": [
        "artifact_id",
        "artifact_path",
        "status",
        "body_sha256",
        "predecessor_artifact_id",
    ],
    "resident": ["slug", "state", "validity", "boot_allowed"],
}

_BACKEND_ERROR_SPECS: dict[str, tuple[int, bool, type[_ClosedModel]]] = {
    "malformed_resident_slug": (400, False, FieldRuleAdmissionErrorDetails),
    "candidate_schema_invalid": (400, False, FieldViolationAdmissionErrorDetails),
    "charter_registry_mismatch": (400, False, CharterRegistryMismatchDetails),
    "registry_delta_invalid": (400, False, RegistryDeltaInvalidDetails),
    "unsupported_agent_admission_policy": (
        409,
        False,
        UnsupportedAdmissionPolicyDetails,
    ),
    "stale_governance_snapshot": (409, True, StaleGovernanceSnapshotDetails),
    "resident_slug_already_registered": (
        409,
        False,
        ResidentSlugAlreadyRegisteredDetails,
    ),
    "resident_charter_path_occupied": (409, False, ResidentCharterPathOccupiedDetails),
    "agent_admission_partial_state_conflict": (
        409,
        False,
        AgentAdmissionPartialStateConflictDetails,
    ),
    "unauthenticated": (401, False, EmptyAdmissionErrorDetails),
    "forbidden": (403, False, EmptyAdmissionErrorDetails),
    "agent_admission_dependency_unavailable": (
        503,
        True,
        AgentAdmissionDependencyUnavailableDetails,
    ),
    "agent_admission_strict_readback_failed": (
        500,
        False,
        AgentAdmissionStrictReadbackFailedDetails,
    ),
}


def _correlation_id(observability: Mapping[str, Any] | None) -> str:
    if observability and observability.get("correlation_id"):
        return str(observability["correlation_id"])
    return str(uuid.uuid4())


def realm_id_mismatch_error(
    correlation_id: str | None = None,
) -> RealmAgentAdmissionError:
    return RealmAgentAdmissionError(
        code="realm_id_mismatch",
        backend_http_status=None,
        retryable=False,
        correlation_id=correlation_id or str(uuid.uuid4()),
        request_sent=False,
        response_received=False,
        details=FieldViolationAdmissionErrorDetails(
            field="candidate.realm_id",
            violation="must_equal_tool_realm_id",
        ),
    )


def outcome_unknown_error(correlation_id: str) -> RealmAgentAdmissionError:
    return RealmAgentAdmissionError(
        code="outcome_unknown",
        backend_http_status=None,
        retryable=True,
        correlation_id=correlation_id,
        request_sent=True,
        response_received=False,
        details=OutcomeUnknownDetails(recovery="retry_exact_admission"),
    )


def _invalid_backend_response(
    correlation_id: str,
    backend_http_status: int | None,
) -> RealmAgentAdmissionError:
    return RealmAgentAdmissionError(
        code="invalid_backend_response",
        backend_http_status=backend_http_status,
        retryable=False,
        correlation_id=correlation_id,
        request_sent=True,
        response_received=True,
        details=InvalidBackendResponseDetails(
            violation="closed_contract_mismatch",
        ),
    )


def _parse_success(
    payload: Any,
    correlation_id: str,
    backend_http_status: int,
) -> RealmAgentAdmissionResponse:
    if not isinstance(payload, dict) or list(payload) != _SUCCESS_KEYS:
        return _invalid_backend_response(correlation_id, backend_http_status)
    for key, ordered_keys in _SUCCESS_NESTED_KEYS.items():
        nested = payload.get(key)
        if not isinstance(nested, dict) or list(nested) != ordered_keys:
            return _invalid_backend_response(correlation_id, backend_http_status)
    try:
        if payload.get("result") == "admitted":
            parsed: RealmAgentAdmissionResponse = RealmAgentAdmitted.model_validate(
                payload
            )
        elif payload.get("result") == "already_admitted_exact":
            parsed = RealmAgentAlreadyAdmittedExact.model_validate(payload)
        else:
            return _invalid_backend_response(correlation_id, backend_http_status)
        if (
            parsed.charter.artifact_path
            != f"realm/agents/{parsed.resident.slug}/charter"
            or parsed.registry.predecessor_artifact_id
            != parsed.predecessor_snapshot.registry_artifact_id
        ):
            return _invalid_backend_response(correlation_id, backend_http_status)
        return parsed
    except ValidationError:
        pass
    return _invalid_backend_response(correlation_id, backend_http_status)


def _parse_backend_error(
    payload: Any,
    correlation_id: str,
    backend_http_status: int,
) -> RealmAgentAdmissionResponse:
    if not isinstance(payload, dict) or list(payload) != ["error"]:
        return _invalid_backend_response(correlation_id, backend_http_status)
    backend_error = payload.get("error")
    if not isinstance(backend_error, dict) or list(backend_error) != [
        "code",
        "http_status",
        "retryable",
        "correlation_id",
        "details",
    ]:
        return _invalid_backend_response(correlation_id, backend_http_status)

    code = backend_error.get("code")
    spec = _BACKEND_ERROR_SPECS.get(code) if isinstance(code, str) else None
    if spec is None:
        return _invalid_backend_response(correlation_id, backend_http_status)
    expected_status, expected_retryable, details_model = spec
    details_payload = backend_error.get("details")
    if (
        backend_http_status != expected_status
        or type(backend_error.get("http_status")) is not int
        or backend_error.get("http_status") != expected_status
        or type(backend_error.get("retryable")) is not bool
        or backend_error.get("retryable") is not expected_retryable
        or not isinstance(backend_error.get("correlation_id"), str)
        or not backend_error.get("correlation_id")
        or not isinstance(details_payload, dict)
        or list(details_payload) != list(details_model.model_fields)
    ):
        return _invalid_backend_response(correlation_id, backend_http_status)
    try:
        details = details_model.model_validate(details_payload)
    except ValidationError:
        return _invalid_backend_response(correlation_id, backend_http_status)
    return RealmAgentAdmissionError(
        code=code,
        backend_http_status=expected_status,
        retryable=expected_retryable,
        correlation_id=backend_error["correlation_id"],
        request_sent=True,
        response_received=True,
        details=details,
    )


def parse_realm_agent_admission_response(
    response: Any,
    correlation_id: str,
) -> RealmAgentAdmissionResponse:
    status_value = getattr(response, "status_code", None)
    status = status_value if type(status_value) is int else None
    if status is None:
        return _invalid_backend_response(correlation_id, None)
    # Invalid response objects must not leak parser details.
    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        return _invalid_backend_response(correlation_id, status)
    if status == 200:
        return _parse_success(payload, correlation_id, status)
    return _parse_backend_error(payload, correlation_id, status)


def admit_realm_agent_result(
    realm_id: str,
    candidate: RealmAgentAdmissionCandidateV1,
    *,
    api_base: str,
    headers: Callable[[], dict[str, str]],
    request: Callable[..., Any],
    observability: dict[str, Any] | None = None,
) -> RealmAgentAdmissionResponse:
    correlation_id = _correlation_id(observability)
    if realm_id != candidate.realm_id:
        return realm_id_mismatch_error(correlation_id)

    # Any failure after dispatch has an ambiguous mutation outcome.
    try:
        request_headers = headers()
    except RuntimeError:
        return RealmAgentAdmissionError(
            code="unauthenticated",
            backend_http_status=None,
            retryable=False,
            correlation_id=correlation_id,
            request_sent=False,
            response_received=False,
            details=EmptyAdmissionErrorDetails(),
        )

    try:
        if observability is not None:
            observability["backend_request_sent"] = True
        response = request(
            "POST",
            f"{api_base}{ADMISSION_PATH_TEMPLATE.format(realm_id=realm_id)}",
            json=candidate.model_dump(mode="json"),
            headers=request_headers,
            timeout=30,
        )
        if observability is not None:
            observability["backend_response_received"] = True
    except Exception:  # noqa: BLE001
        return outcome_unknown_error(correlation_id)

    return parse_realm_agent_admission_response(response, correlation_id)
