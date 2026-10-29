"""Thin, single-dispatch adapter for the canonical relation batch operation."""

from __future__ import annotations

import contextvars
import json
import re
import threading
import time
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, StrictInt

TOTAL_TIMEOUT_SECONDS = 35
CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 25

ITEM_MESSAGES = {
    "INVALID_ITEM": "Invalid relation item.",
    "ENTITY_NOT_FOUND": "An endpoint is unavailable in the requested realm.",
    "RELATION_TYPE_NOT_FOUND": "Relation type was not found.",
    "FORBIDDEN": "Relation operation is forbidden.",
    "CONSTRAINT_VIOLATION": "Relation constraint was violated.",
    "INTERNAL_ERROR": "Relation operation failed.",
}
REFUSALS = {
    (400, "INVALID_REQUEST"): "Invalid batch request.",
    (401, "UNAUTHENTICATED"): "Authentication is required.",
    (403, "FORBIDDEN"): "Batch operation is forbidden.",
    (422, "BATCH_EMPTY"): "Batch must contain at least one relation.",
    (422, "BATCH_LIMIT_EXCEEDED"): "Batch must contain at most 100 relations.",
}


class _Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class BatchItemError(_Closed):
    code: Literal[
        "INVALID_ITEM",
        "ENTITY_NOT_FOUND",
        "RELATION_TYPE_NOT_FOUND",
        "FORBIDDEN",
        "CONSTRAINT_VIOLATION",
        "INTERNAL_ERROR",
    ]
    message: str


class BatchSuccess(_Closed):
    index: StrictInt
    status: Literal["SUCCESS"]


class BatchFailure(_Closed):
    index: StrictInt
    status: Literal["ERROR"]
    error: BatchItemError


class BatchResult(_Closed):
    results: list[BatchSuccess | BatchFailure]


def tool_error(
    code="outcome_unknown", message="Batch outcome is unknown.", http_status=None
):
    from fastmcp.exceptions import ToolError

    return ToolError(
        json.dumps(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "http_status": http_status,
                    "retryable": False,
                }
            },
            separators=(",", ":"),
        )
    )


class BatchInvocation:
    """One terminal outcome shared by dispatch, total deadline and outer guard."""

    def __init__(self):
        self.deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
        self.lock = threading.Lock()
        self.done = threading.Event()
        self.value = None
        self.dispatched = False

    def cancel(self):
        with self.lock:
            if not self.done.is_set():
                self.value = tool_error()
                self.done.set()

    def begin_dispatch(self):
        with self.lock:
            if self.done.is_set() or time.monotonic() >= self.deadline:
                return False
            self.dispatched = True
            return True

    def complete(self, value):
        with self.lock:
            if not self.done.is_set():
                self.value = value if time.monotonic() < self.deadline else tool_error()
                self.done.set()


invocation_context: contextvars.ContextVar[BatchInvocation | None] = (
    contextvars.ContextVar(
        "relation_batch_invocation",
        default=None,
    )
)


class BatchCancellationBoundary:
    async def __call__(self, context, call_next):
        if (
            context.method != "tools/call"
            or getattr(context.message, "name", None) != "create_relations_batch"
        ):
            return await call_next(context)
        state = BatchInvocation()
        token = invocation_context.set(state)
        try:
            return await call_next(context)
        finally:
            state.cancel()
            invocation_context.reset(token)


def valid_realm_id(value):
    return (
        isinstance(value, str)
        and re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            value,
        )
        is not None
    )


def _validated_response(response, count):
    data = response.json()
    status = response.status_code
    if type(status) is not int or not isinstance(data, dict):
        raise ValueError
    if status == 200:
        result = BatchResult.model_validate(data)
        if len(result.results) != count:
            raise ValueError
        for index, item in enumerate(result.results):
            if item.index != index:
                raise ValueError
            if (
                isinstance(item, BatchFailure)
                and item.error.message != ITEM_MESSAGES[item.error.code]
            ):
                raise ValueError
        return result
    if set(data) != {"error"} or not isinstance(data["error"], dict):
        raise ValueError
    error = data["error"]
    code = error.get("code")
    if not isinstance(code, str):
        raise ValueError
    message = REFUSALS.get((status, code))
    expected_keys = (
        {"code", "message", "limit"}
        if code == "BATCH_LIMIT_EXCEEDED"
        else {"code", "message"}
    )
    if (
        message is None
        or set(error) != expected_keys
        or error.get("message") != message
    ):
        raise ValueError
    if code == "BATCH_LIMIT_EXCEEDED" and (
        type(error["limit"]) is not int or error["limit"] != 100
    ):
        raise ValueError
    return tool_error(code, message, status)


def request_batch(
    *,
    realm_id: str,
    relations: list[Any],
    api_base: str,
    request: Callable[..., Any],
    headers: dict[str, str],
    state: BatchInvocation,
):
    """Acquire, parse and validate the entire response inside one total deadline."""

    def run():
        if not state.begin_dispatch():
            state.cancel()
            return
        response = None
        try:
            response = request(
                "POST",
                f"{api_base}/realm/{realm_id}/entity/relation/batch",
                json={"relations": relations},
                headers=headers,
                allow_redirects=False,
                timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
            )
            value = _validated_response(response, len(relations))
        except Exception:
            value = tool_error()
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
        state.complete(value)

    # Carry HTTP credential context into the transport worker. No retries.
    context = contextvars.copy_context()
    threading.Thread(target=context.run, args=(run,), daemon=True).start()
    if not state.done.wait(max(0, state.deadline - time.monotonic())):
        state.cancel()
    value = state.value
    if isinstance(value, BaseException):
        raise value
    return value
