from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
from typing_extensions import TypedDict

DECLARATION_PATH = "realm/declaration"
DECLARATION_CONTRACT_ID = "realm_declaration"
DECLARATION_CONTRACT_VERSION = 1
MAX_DECLARATION_BODY_BYTES = 65_536

_CANONICAL_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_TOOL_NAME_RE = re.compile(r"[a-z][a-z0-9_]*")
_BACKEND_SUCCESS_FIELDS = {
    "realm_id",
    "artifact_path",
    "artifact_id",
    "artifact_kind",
    "declaration_contract_id",
    "declaration_contract_version",
    "status",
    "accepted_at",
    "lifecycle",
    "body_sha256",
    "body",
}
_PUBLIC_SUCCESS_FIELDS = (
    "realm_id",
    "artifact_path",
    "artifact_id",
    "artifact_kind",
    "declaration_contract_id",
    "declaration_contract_version",
    "status",
    "accepted_at",
    "body_sha256",
    "body",
)
_BODY_FIELDS = {
    "declaration_contract_id",
    "declaration_contract_version",
    "realm_id",
    "purpose",
    "boundaries",
    "routes",
}
_ROUTE_REQUIRED_FIELDS = {
    "need",
    "tool_entry_point",
    "authoritative_result",
    "stop_condition",
}
_ROUTE_OPTIONAL_FIELDS = {"next_discovery_step"}

_ERRORS: dict[str, tuple[str, bool]] = {
    "invalid_request": ("Invalid request.", False),
    "realm_not_accessible": ("Realm is not accessible.", False),
    "declaration_not_found": ("Realm declaration was not found.", False),
    "declaration_not_current": ("Realm declaration is not current.", False),
    "declaration_ambiguous": ("Realm declaration current state is ambiguous.", False),
    "unsupported_declaration_contract": (
        "Realm declaration contract is unsupported.",
        False,
    ),
    "declaration_body_invalid": ("Realm declaration body is invalid.", False),
    "declaration_body_too_large": ("Realm declaration body is too large.", False),
    "dependency_unavailable": ("Realm declaration dependency is unavailable.", False),
}
_BACKEND_OUTCOME_TO_PUBLIC = {
    "realm_not_accessible": "realm_not_accessible",
    "not_found": "declaration_not_found",
    "not_current": "declaration_not_current",
    "ambiguous": "declaration_ambiguous",
    "unsupported_declaration_contract": "unsupported_declaration_contract",
    "body_invalid": "declaration_body_invalid",
    "body_too_large": "declaration_body_too_large",
    "dependency_unavailable": "dependency_unavailable",
}


class RealmDeclarationSuccess(TypedDict):
    schema_version: str
    realm_id: str
    artifact_path: str
    artifact_id: str
    artifact_kind: str
    declaration_contract_id: str
    declaration_contract_version: int
    status: str
    accepted_at: str
    body_sha256: str
    body: str


@dataclass(frozen=True)
class RealmDeclarationError(Exception):
    code: str
    retryable: bool = False
    correlation_id: str = ""

    def envelope(self) -> dict[str, Any]:
        message, default_retryable = _ERRORS[self.code]
        return {
            "schema_version": "1",
            "error": {
                "code": self.code,
                "message": message,
                "correlation_id": self.correlation_id or str(uuid.uuid4()),
                "retryable": self.retryable
                if self.code == "dependency_unavailable"
                else default_retryable,
            },
        }

    def serialized(self) -> str:
        return json.dumps(self.envelope(), ensure_ascii=False, separators=(",", ":"))


def _error(code: str, *, retryable: bool = False) -> RealmDeclarationError:
    return RealmDeclarationError(
        code=code, retryable=retryable, correlation_id=str(uuid.uuid4())
    )


def _canonical_uuid(value: Any) -> bool:
    if not isinstance(value, str) or not _CANONICAL_UUID_RE.fullmatch(value):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def is_canonical_realm_id(value: Any) -> bool:
    return _canonical_uuid(value)


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_closed_json(body: str) -> Any:
    def closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    return json.loads(body, object_pairs_hook=closed_object)


def _validate_body(body: Any, realm_id: str, expected_sha256: str) -> None:
    if not isinstance(body, str):
        raise _error("declaration_body_invalid")
    try:
        body_bytes = body.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise _error("declaration_body_invalid") from exc
    if len(body_bytes) > MAX_DECLARATION_BODY_BYTES:
        raise _error("declaration_body_too_large")
    if (
        not _SHA256_RE.fullmatch(expected_sha256)
        or hashlib.sha256(body_bytes).hexdigest() != expected_sha256
    ):
        raise _error("declaration_body_invalid")
    try:
        document = _load_closed_json(body)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise _error("declaration_body_invalid") from exc
    if not isinstance(document, dict) or set(document) != _BODY_FIELDS:
        raise _error("declaration_body_invalid")
    if document.get("declaration_contract_id") != DECLARATION_CONTRACT_ID:
        raise _error("unsupported_declaration_contract")
    if (
        type(document.get("declaration_contract_version")) is not int
        or document["declaration_contract_version"] != 1
    ):
        raise _error("unsupported_declaration_contract")
    if document.get("realm_id") != realm_id or not _canonical_uuid(
        document.get("realm_id")
    ):
        raise _error("declaration_body_invalid")
    if not _non_empty_string(document.get("purpose")):
        raise _error("declaration_body_invalid")
    boundaries = document.get("boundaries")
    if (
        not isinstance(boundaries, list)
        or not boundaries
        or any(not _non_empty_string(item) for item in boundaries)
        or len(set(boundaries)) != len(boundaries)
    ):
        raise _error("declaration_body_invalid")
    routes = document.get("routes")
    if not isinstance(routes, list) or not routes:
        raise _error("declaration_body_invalid")
    for route in routes:
        if not isinstance(route, dict):
            raise _error("declaration_body_invalid")
        keys = set(route)
        if not _ROUTE_REQUIRED_FIELDS.issubset(keys) or not keys.issubset(
            _ROUTE_REQUIRED_FIELDS | _ROUTE_OPTIONAL_FIELDS
        ):
            raise _error("declaration_body_invalid")
        if any(not _non_empty_string(route.get(key)) for key in keys):
            raise _error("declaration_body_invalid")
        if not _TOOL_NAME_RE.fullmatch(route["tool_entry_point"]):
            raise _error("declaration_body_invalid")
    canonical = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if canonical != body:
        raise _error("declaration_body_invalid")


def _validate_success(data: Any, realm_id: str) -> RealmDeclarationSuccess:
    if not isinstance(data, dict) or set(data) != _BACKEND_SUCCESS_FIELDS:
        raise _error("dependency_unavailable")
    if (
        data.get("realm_id") != realm_id
        or data.get("artifact_path") != DECLARATION_PATH
    ):
        raise _error("dependency_unavailable")
    if not _canonical_uuid(data.get("artifact_id")):
        raise _error("dependency_unavailable")
    if data.get("artifact_kind") != "decision" or data.get("status") != "accepted":
        raise _error("declaration_not_current")
    if data.get("lifecycle") != "accepted_current":
        raise _error("declaration_not_current")
    if data.get("declaration_contract_id") != DECLARATION_CONTRACT_ID:
        raise _error("unsupported_declaration_contract")
    if (
        type(data.get("declaration_contract_version")) is not int
        or data["declaration_contract_version"] != 1
    ):
        raise _error("unsupported_declaration_contract")
    accepted_at = data.get("accepted_at")
    if not isinstance(accepted_at, str) or not accepted_at.endswith("Z"):
        raise _error("dependency_unavailable")
    try:
        datetime.fromisoformat(accepted_at[:-1] + "+00:00")
    except ValueError as exc:
        raise _error("dependency_unavailable") from exc
    body_sha256 = data.get("body_sha256")
    if not isinstance(body_sha256, str):
        raise _error("declaration_body_invalid")
    _validate_body(data.get("body"), realm_id, body_sha256)
    return {
        "schema_version": "1",
        **{field: data[field] for field in _PUBLIC_SUCCESS_FIELDS},
    }


def resolve_realm_declaration(
    realm_id: str,
    *,
    api_base: str,
    headers: dict[str, str],
    request: Callable[..., Any] = requests.request,
) -> RealmDeclarationSuccess:
    if not _canonical_uuid(realm_id):
        raise _error("invalid_request")
    try:
        response = request(
            "GET",
            f"{api_base}/realm/{realm_id}/declaration",
            headers=headers,
            timeout=30,
        )
    except Exception as exc:
        transient = isinstance(
            exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
        )
        raise _error("dependency_unavailable", retryable=transient) from exc
    status = int(getattr(response, "status_code", 0) or 0)
    if status in {401, 403, 404}:
        raise _error("realm_not_accessible")
    if status == 429 or status >= 500:
        raise _error("dependency_unavailable", retryable=True)
    if status < 200 or status >= 300:
        raise _error("dependency_unavailable")
    try:
        data = response.json()
    except (TypeError, ValueError) as exc:
        raise _error("dependency_unavailable") from exc
    if isinstance(data, dict) and set(data) == {"outcome"}:
        outcome = data.get("outcome")
        code = _BACKEND_OUTCOME_TO_PUBLIC.get(outcome)
        if code is None:
            raise _error("dependency_unavailable")
        raise _error(code, retryable=outcome == "dependency_unavailable")
    return _validate_success(data, realm_id)
