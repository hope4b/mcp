from __future__ import annotations

import json
import queue
import re
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from typing import Any, Literal

import requests
from pydantic import BaseModel, ConfigDict


CLONE_POST_TIMEOUT_SECONDS = 35
CLONE_RESULT_TIMEOUT_SECONDS = 10
CLONE_POST_CONNECT_TIMEOUT_SECONDS = 10
CLONE_POST_READ_TIMEOUT_SECONDS = 25
CLONE_RESULT_CONNECT_TIMEOUT_SECONDS = 3
CLONE_RESULT_READ_TIMEOUT_SECONDS = 7
CLONE_PATH_TEMPLATE = "/realm/{target_realm_id}/entity/clone-from-realm"
CLONE_RESULT_PATH_TEMPLATE = "/realm/{target_realm_id}/entity/clone-from-realm/result"

_CORRELATION_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$", re.ASCII)


class _TotalDeadlineExceeded(requests.exceptions.Timeout):
    pass


def _request_with_total_deadline(
    send: Callable[..., Any],
    method: str,
    url: str,
    *,
    total_timeout_seconds: float,
    **kwargs: Any,
) -> Any:
    """Run one transport call behind a monotonic wall-clock deadline.

    Requests' connect/read tuple does not cap total elapsed time. The daemon
    worker keeps a timed-out transport result from being returned later, while
    the caller can immediately apply the operation-specific recovery contract.
    """
    deadline = time.monotonic() + total_timeout_seconds
    outcome: queue.Queue[tuple[float, Any, BaseException | None]] = queue.Queue(maxsize=1)

    def run() -> None:
        try:
            value = send(method, url, **kwargs)
        except BaseException as exc:
            outcome.put((time.monotonic(), None, exc))
        else:
            outcome.put((time.monotonic(), value, None))

    threading.Thread(target=run, daemon=True).start()
    try:
        completed_at, value, error = outcome.get(timeout=max(0.0, deadline - time.monotonic()))
    except queue.Empty as exc:
        raise _TotalDeadlineExceeded from exc
    if completed_at > deadline or time.monotonic() > deadline:
        raise _TotalDeadlineExceeded
    if error is not None:
        raise error
    return value


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CloneObjectToRealmResult(_ClosedModel):
    target_realm_id: str
    target_object_id: str
    primary_realm_id: str
    primary_object_id: str
    created: bool


class CloneObjectToRealmNotFound(_ClosedModel):
    found: Literal[False]


CloneObjectToRealmLookupResult = CloneObjectToRealmResult | CloneObjectToRealmNotFound


class CloneRecovery(_ClosedModel):
    action: str


class CloneErrorBody(_ClosedModel):
    code: str
    message: str
    correlation_id: str
    retryable: bool
    recovery: CloneRecovery


class CloneToolError(_ClosedModel):
    schema_version: Literal[1]
    error: CloneErrorBody

    def serialized(self) -> str:
        return json.dumps(self.model_dump(), ensure_ascii=False, separators=(",", ":"))


_PUBLIC_ERRORS: dict[str, tuple[str, bool, str]] = {
    "invalid_request": ("Clone request is invalid.", False, "none"),
    "unauthenticated": ("Authentication is required.", False, "none"),
    "source_access_denied": ("Source realm access is denied.", False, "none"),
    "target_create_denied": ("Target realm create access is denied.", False, "none"),
    "target_read_denied": ("Target realm read access is denied.", False, "none"),
    "source_realm_not_found": ("Source realm was not found.", False, "none"),
    "target_realm_not_found": ("Target realm was not found.", False, "none"),
    "source_object_not_found": ("Source object was not found.", False, "none"),
    "target_template_not_found": ("Target template was not found.", False, "none"),
    "clone_failed": ("Clone operation failed.", False, "none"),
    "clone_dependency_unavailable": (
        "Clone dependency is temporarily unavailable.",
        True,
        "retry_clone_object_to_realm",
    ),
    "outcome_unknown": (
        "Clone outcome is unknown.",
        False,
        "call_get_clone_object_to_realm_result",
    ),
    "invalid_backend_response": ("Clone service returned an invalid response.", False, "none"),
    "result_dependency_unavailable": (
        "Clone result service is temporarily unavailable.",
        True,
        "retry_get_clone_object_to_realm_result",
    ),
}

_POST_ERRORS = {
    "invalid_request": (400, False),
    "unauthenticated": (401, False),
    "source_access_denied": (403, False),
    "target_create_denied": (403, False),
    "source_realm_not_found": (404, False),
    "target_realm_not_found": (404, False),
    "source_object_not_found": (404, False),
    "target_template_not_found": (404, False),
    "clone_failed": (500, False),
    "clone_dependency_unavailable": (503, True),
}

_RESULT_ERRORS = {
    "invalid_request": (400, False),
    "unauthenticated": (401, False),
    "source_access_denied": (403, False),
    "target_read_denied": (403, False),
    "source_realm_not_found": (404, False),
    "target_realm_not_found": (404, False),
    "source_object_not_found": (404, False),
    "clone_failed": (500, False),
    "clone_dependency_unavailable": (503, True),
}

_RESULT_KEYS = {
    "targetRealmId",
    "targetObjectId",
    "primaryRealmId",
    "primaryObjectId",
    "created",
}


def clone_tool_error(code: str, correlation_id: str) -> CloneToolError:
    message, retryable, action = _PUBLIC_ERRORS[code]
    return CloneToolError(
        schema_version=1,
        error=CloneErrorBody(
            code=code,
            message=message,
            correlation_id=correlation_id,
            retryable=retryable,
            recovery=CloneRecovery(action=action),
        ),
    )


def _canonical_uuid(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        return str(uuid.UUID(value)) == value
    except (ValueError, AttributeError, TypeError):
        return False


def _safe_correlation_id(value: Any, invocation_correlation_id: str) -> str:
    if isinstance(value, str) and _CORRELATION_ID_RE.fullmatch(value):
        return value
    return invocation_correlation_id


def _response_json(response: Any) -> Any:
    try:
        return response.json()
    except (TypeError, ValueError):
        return None


def _parse_result(
    data: Any,
    *,
    source_realm_id: str,
    source_object_id: str,
    target_realm_id: str,
    required_created: bool | None,
) -> CloneObjectToRealmResult | None:
    if not isinstance(data, Mapping) or set(data) != _RESULT_KEYS:
        return None
    values = {key: data.get(key) for key in _RESULT_KEYS}
    if not all(_canonical_uuid(values[key]) for key in _RESULT_KEYS - {"created"}):
        return None
    if type(values["created"]) is not bool:
        return None
    if required_created is not None and values["created"] is not required_created:
        return None
    if (
        values["targetRealmId"] != target_realm_id
        or values["primaryRealmId"] != source_realm_id
        or values["primaryObjectId"] != source_object_id
    ):
        return None
    return CloneObjectToRealmResult(
        target_realm_id=values["targetRealmId"],
        target_object_id=values["targetObjectId"],
        primary_realm_id=values["primaryRealmId"],
        primary_object_id=values["primaryObjectId"],
        created=values["created"],
    )


def _parse_backend_error(
    response: Any,
    *,
    operation: Literal["post", "result_get"],
    invocation_correlation_id: str,
) -> CloneToolError:
    data = _response_json(response)
    if not isinstance(data, Mapping) or set(data) != {"error"}:
        return clone_tool_error("invalid_backend_response", invocation_correlation_id)
    error = data.get("error")
    expected_keys = {"code", "httpStatus", "retryable", "correlationId", "details"}
    if not isinstance(error, Mapping) or set(error) != expected_keys:
        return clone_tool_error("invalid_backend_response", invocation_correlation_id)
    code = error.get("code")
    status = getattr(response, "status_code", None)
    allowlist = _POST_ERRORS if operation == "post" else _RESULT_ERRORS
    expected = allowlist.get(code) if isinstance(code, str) else None
    if (
        expected is None
        or type(status) is not int
        or type(error.get("httpStatus")) is not int
        or type(error.get("retryable")) is not bool
        or error.get("httpStatus") != status
        or expected != (status, error.get("retryable"))
        or not isinstance(error.get("details"), Mapping)
        or bool(error.get("details"))
    ):
        return clone_tool_error("invalid_backend_response", invocation_correlation_id)
    correlation_id = _safe_correlation_id(error.get("correlationId"), invocation_correlation_id)
    public_code = (
        "result_dependency_unavailable"
        if operation == "result_get" and code == "clone_dependency_unavailable"
        else code
    )
    return clone_tool_error(public_code, correlation_id)


def _lookup_response(
    response: Any,
    *,
    source_realm_id: str,
    source_object_id: str,
    target_realm_id: str,
    invocation_correlation_id: str,
) -> CloneObjectToRealmLookupResult | CloneToolError:
    status = getattr(response, "status_code", 0)
    if status != 200:
        return _parse_backend_error(
            response,
            operation="result_get",
            invocation_correlation_id=invocation_correlation_id,
        )
    data = _response_json(response)
    if not isinstance(data, Mapping):
        return clone_tool_error("invalid_backend_response", invocation_correlation_id)
    if set(data) == {"found"} and data.get("found") is False:
        return CloneObjectToRealmNotFound(found=False)
    if set(data) != {"found", "result"} or data.get("found") is not True:
        return clone_tool_error("invalid_backend_response", invocation_correlation_id)
    result = _parse_result(
        data.get("result"),
        source_realm_id=source_realm_id,
        source_object_id=source_object_id,
        target_realm_id=target_realm_id,
        required_created=False,
    )
    if result is None:
        return clone_tool_error("invalid_backend_response", invocation_correlation_id)
    return result


def get_clone_object_to_realm_result_request(
    *,
    source_realm_id: str,
    source_object_id: str,
    target_realm_id: str,
    api_base: str,
    headers: Mapping[str, str],
    invocation_correlation_id: str,
    request: Callable[..., Any] | None = None,
) -> CloneObjectToRealmLookupResult | CloneToolError:
    if not all(_canonical_uuid(value) for value in (source_realm_id, source_object_id, target_realm_id)):
        return clone_tool_error("invalid_request", invocation_correlation_id)
    try:
        send = request or requests.request
        response = _request_with_total_deadline(
            send,
            "GET",
            api_base + CLONE_RESULT_PATH_TEMPLATE.format(target_realm_id=target_realm_id),
            total_timeout_seconds=CLONE_RESULT_TIMEOUT_SECONDS,
            params={"sourceRealmId": source_realm_id, "sourceObjectId": source_object_id},
            headers=dict(headers),
            allow_redirects=False,
            timeout=(
                CLONE_RESULT_CONNECT_TIMEOUT_SECONDS,
                CLONE_RESULT_READ_TIMEOUT_SECONDS,
            ),
        )
    except requests.exceptions.RequestException:
        return clone_tool_error("result_dependency_unavailable", invocation_correlation_id)
    return _lookup_response(
        response,
        source_realm_id=source_realm_id,
        source_object_id=source_object_id,
        target_realm_id=target_realm_id,
        invocation_correlation_id=invocation_correlation_id,
    )


def clone_object_to_realm_request(
    *,
    source_realm_id: str,
    source_object_id: str,
    target_realm_id: str,
    target_template_id: str,
    api_base: str,
    headers: Mapping[str, str],
    invocation_correlation_id: str,
    request: Callable[..., Any] | None = None,
) -> CloneObjectToRealmResult | CloneToolError:
    if not all(
        _canonical_uuid(value)
        for value in (source_realm_id, source_object_id, target_realm_id, target_template_id)
    ):
        return clone_tool_error("invalid_request", invocation_correlation_id)
    try:
        send = request or requests.request
        response = _request_with_total_deadline(
            send,
            "POST",
            api_base + CLONE_PATH_TEMPLATE.format(target_realm_id=target_realm_id),
            total_timeout_seconds=CLONE_POST_TIMEOUT_SECONDS,
            json={
                "sourceRealmId": source_realm_id,
                "sourceObjectId": source_object_id,
                "targetTemplateId": target_template_id,
            },
            headers=dict(headers),
            allow_redirects=False,
            timeout=(
                CLONE_POST_CONNECT_TIMEOUT_SECONDS,
                CLONE_POST_READ_TIMEOUT_SECONDS,
            ),
        )
    except (
        requests.exceptions.ConnectTimeout,
        requests.exceptions.InvalidURL,
        requests.exceptions.InvalidSchema,
        requests.exceptions.MissingSchema,
    ):
        return clone_tool_error("clone_dependency_unavailable", invocation_correlation_id)
    except requests.exceptions.RequestException:
        lookup = get_clone_object_to_realm_result_request(
            source_realm_id=source_realm_id,
            source_object_id=source_object_id,
            target_realm_id=target_realm_id,
            api_base=api_base,
            headers=headers,
            invocation_correlation_id=invocation_correlation_id,
            request=send,
        )
        if isinstance(lookup, CloneObjectToRealmResult):
            return lookup
        return clone_tool_error("outcome_unknown", invocation_correlation_id)

    status = getattr(response, "status_code", 0)
    if status in (200, 201):
        result = _parse_result(
            _response_json(response),
            source_realm_id=source_realm_id,
            source_object_id=source_object_id,
            target_realm_id=target_realm_id,
            required_created=status == 201,
        )
        return result or clone_tool_error("outcome_unknown", invocation_correlation_id)
    if isinstance(status, int) and 200 <= status < 300:
        return clone_tool_error("outcome_unknown", invocation_correlation_id)
    return _parse_backend_error(
        response,
        operation="post",
        invocation_correlation_id=invocation_correlation_id,
    )
