"""Contract, single-dispatch, and deterministic terminal-state tests."""

from __future__ import annotations

import asyncio
import contextvars
import json
import threading
from copy import deepcopy
from unittest.mock import Mock, patch

import pytest
import requests
from fastmcp import Client
from fastmcp.exceptions import ToolError

from onto_mcp import api_resources as api
from onto_mcp import relation_batch as batch

REALM = "a1234567-1234-1234-1234-123456789abc"


class Response:
    def __init__(self, status, body):
        self.status_code, self.body = status, body
        self.closed = False

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body

    def close(self):
        self.closed = True


def success(index=0):
    return {"index": index, "status": "SUCCESS"}


def failure(index=0, code="INVALID_ITEM"):
    return {
        "index": index,
        "status": "ERROR",
        "error": {"code": code, "message": batch.ITEM_MESSAGES[code]},
    }


def invoke(response, relations=None, state=None):
    request = Mock(return_value=response)
    result = batch.request_batch(
        realm_id=REALM,
        relations=[None] if relations is None else relations,
        api_base="https://core.invalid",
        headers={"X-API-Key": "test-only"},
        request=request,
        state=state or batch.BatchInvocation(),
    )
    return result, request


def unknown(exc):
    assert json.loads(str(exc)) == {
        "error": {
            "code": "outcome_unknown",
            "message": "Batch outcome is unknown.",
            "http_status": None,
            "retryable": False,
        }
    }


@pytest.mark.parametrize("size", [1, 100])
def test_completed_batches_preserve_raw_input_and_one_post(size):
    raw = [
        None,
        7,
        {"extra": True},
        {"type": " t ", "additionalProperties": {"a": " b "}},
    ]
    relations = (raw * 25)[:size]
    wire = {"results": [failure(i) if i % 2 else success(i) for i in range(size)]}
    response = Response(200, wire)
    result, request = invoke(response, relations)
    assert result.model_dump() == wire
    request.assert_called_once_with(
        "POST",
        f"https://core.invalid/realm/{REALM}/entity/relation/batch",
        json={"relations": relations},
        headers={"X-API-Key": "test-only"},
        allow_redirects=False,
        timeout=(5, 25),
    )
    assert response.closed


@pytest.mark.parametrize("status,code", list(batch.REFUSALS))
def test_exact_operation_refusals(status, code):
    error = {"code": code, "message": batch.REFUSALS[status, code]}
    if code == "BATCH_LIMIT_EXCEEDED":
        error["limit"] = 100
    relations = (
        []
        if code == "BATCH_EMPTY"
        else [None] * (101 if code == "BATCH_LIMIT_EXCEEDED" else 1)
    )
    request = Mock(return_value=Response(status, {"error": error}))
    with pytest.raises(ToolError) as caught:
        batch.request_batch(
            realm_id=REALM,
            relations=relations,
            api_base="https://core.invalid",
            headers={},
            request=request,
            state=batch.BatchInvocation(),
        )
    assert json.loads(str(caught.value)) == {
        "error": {
            "code": code,
            "message": error["message"],
            "http_status": status,
            "retryable": False,
        }
    }
    assert request.call_count == 1
    assert request.call_args.kwargs["json"] == {"relations": relations}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"results": []},
        {"results": [success(), success(1)]},
        {"results": [success(True)]},
        {"results": [success(1)]},
        {"results": [dict(success(), created=True)]},
        {"results": [{"index": 0, "status": "CREATED"}]},
        {"results": [dict(success(), error={})]},
        {"results": [{"index": 0, "status": "ERROR"}]},
        {
            "results": [
                {
                    "index": 0,
                    "status": "ERROR",
                    "error": {"code": "INVALID_ITEM", "message": "secret"},
                }
            ]
        },
        {
            "results": [
                {
                    "index": 0,
                    "status": "ERROR",
                    "error": {"code": "UNKNOWN", "message": "secret"},
                }
            ]
        },
        {"results": [success()], "extra": 1},
        ValueError("truncated secret"),
    ],
)
def test_untrustworthy_completed_result_is_unknown(body):
    with pytest.raises(ToolError) as caught:
        invoke(Response(200, body))
    unknown(caught.value)


@pytest.mark.parametrize(
    "results",
    [
        [success(0), success(0)],
        [success(1), success(0)],
        [success(0), success(2)],
    ],
)
def test_duplicate_out_of_order_and_missing_indexes(results):
    with pytest.raises(ToolError) as caught:
        invoke(Response(200, {"results": results}), [None, None])
    unknown(caught.value)


@pytest.mark.parametrize(
    "status,body",
    [
        (
            503,
            {
                "error": {
                    "code": "OUTCOME_UNKNOWN",
                    "message": "Batch outcome is unknown.",
                }
            },
        ),
        (500, {"error": "secret"}),
        (302, {}),
        (401, {"error": {"code": "UNAUTHENTICATED", "message": "secret"}}),
        (
            400,
            {
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Invalid batch request.",
                    "extra": 1,
                }
            },
        ),
        (
            422,
            {
                "error": {
                    "code": "BATCH_LIMIT_EXCEEDED",
                    "message": "Batch must contain at most 100 relations.",
                    "limit": True,
                }
            },
        ),
    ],
)
def test_untrusted_http_errors_do_not_become_confirmed_refusals(status, body):
    with pytest.raises(ToolError) as caught:
        invoke(Response(status, body))
    unknown(caught.value)


@pytest.mark.parametrize(
    "fault",
    [
        requests.ConnectionError("secret"),
        requests.Timeout("secret"),
        RuntimeError("secret"),
    ],
)
def test_transport_failures_never_retry(fault):
    request = Mock(side_effect=fault)
    with pytest.raises(ToolError) as caught:
        batch.request_batch(
            realm_id=REALM,
            relations=[None],
            api_base="https://core.invalid",
            headers={},
            request=request,
            state=batch.BatchInvocation(),
        )
    unknown(caught.value)
    request.assert_called_once()


def test_cancel_before_dispatch_sends_nothing():
    state = batch.BatchInvocation()
    state.cancel()
    request = Mock()
    with pytest.raises(ToolError) as caught:
        batch.request_batch(
            realm_id=REALM,
            relations=[None],
            api_base="https://core.invalid",
            headers={},
            request=request,
            state=state,
        )
    unknown(caught.value)
    assert not state.dispatched
    request.assert_not_called()


@pytest.mark.parametrize("phase", ["acquisition", "parsing", "validation"])
def test_total_deadline_covers_every_phase_and_discards_late_result(phase):
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    response = Response(200, {"results": [success()]})

    def blocked(value):
        entered.set()
        assert release.wait(2)
        return value

    def request(*args, **kwargs):
        return blocked(response) if phase == "acquisition" else response

    original_validate = batch._validated_response

    def validate(*args):
        if phase == "validation":
            blocked(None)
        return original_validate(*args)

    original_json = response.json
    if phase == "parsing":
        response.json = lambda: blocked(original_json())
    original_close = response.close

    def close():
        original_close()
        finished.set()

    response.close = close
    with patch.object(batch, "TOTAL_TIMEOUT_SECONDS", 0.05), patch.object(
        batch, "_validated_response", validate
    ):
        state = batch.BatchInvocation()
        try:
            with pytest.raises(ToolError) as caught:
                batch.request_batch(
                    realm_id=REALM,
                    relations=[None],
                    api_base="https://core.invalid",
                    headers={},
                    request=request,
                    state=state,
                )
            assert entered.is_set()
            unknown(caught.value)
            terminal = state.value
        finally:
            release.set()
        assert finished.wait(2)
        assert state.value is terminal


def test_worker_preserves_http_credential_context():
    credential = contextvars.ContextVar("test_credential")
    token = credential.set("test-only")
    request = Mock(
        side_effect=lambda *a, **k: (
            Response(200, {"results": [success()]})
            if credential.get() == "test-only"
            else None
        )
    )
    try:
        result = batch.request_batch(
            realm_id=REALM,
            relations=[None],
            api_base="https://core.invalid",
            headers={},
            request=request,
            state=batch.BatchInvocation(),
        )
        assert result.model_dump() == {"results": [success()]}
    finally:
        credential.reset(token)


def protocol_exercise(raw=None, wire=None):
    if raw is None:
        raw = [None, 3, {"type": "unfamiliar"}, []]
    if wire is None:
        wire = {"results": [failure(i) for i in range(len(raw))]}
    expected_body = {"relations": deepcopy(raw)}

    async def run():
        async with Client(api.mcp, timeout=5) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            schema = tools["create_relations_batch"].inputSchema
            assert set(schema["properties"]) == {"realm_id", "relations"}
            assert schema["properties"]["relations"]["type"] == "array"
            assert schema["properties"]["relations"].get("items", {}) == {}
            with patch.object(
                api, "_onto_headers", return_value={"X-API-Key": "test-only"}
            ), patch.object(
                api, "_request_with_canonical_auth", return_value=Response(200, wire)
            ) as request:
                result = await client.call_tool(
                    "create_relations_batch", {"realm_id": REALM, "relations": raw}
                )
            assert not result.is_error
            assert result.structured_content == wire
            request.assert_called_once_with(
                "POST",
                f"{api.ONTO_API_BASE}/realm/{REALM}/entity/relation/batch",
                json=expected_body,
                headers={"X-API-Key": "test-only"},
                allow_redirects=False,
                timeout=(5, 25),
            )
            for args in [{"realm_id": REALM, "relations": "bad"}, {"realm_id": REALM}]:
                with patch.object(api, "_request_with_canonical_auth") as request:
                    result = await client.call_tool(
                        "create_relations_batch", args, raise_on_error=False
                    )
                assert result.is_error
                request.assert_not_called()

    return run()


def test_real_mcp_schema_call_all_errors_and_protocol_validation():
    asyncio.run(protocol_exercise())


def test_real_mcp_mixed_results_preserve_valid_relations_and_one_post():
    first = {
        "type": " relates to ",
        "startRelatedEntity": {
            "id": "11111111-1111-4111-8111-111111111111",
            "role": " source ",
        },
        "endRelatedEntity": {
            "id": "22222222-2222-4222-8222-222222222222",
            "role": "",
        },
        "additionalProperties": {"note": " preserve whitespace "},
    }
    second = {
        "type": "other relation",
        "startRelatedEntity": first["endRelatedEntity"].copy(),
        "endRelatedEntity": first["startRelatedEntity"].copy(),
        "additionalProperties": {"startNodeRole": "override"},
    }
    raw = [first, None, second]
    wire = {"results": [success(0), failure(1), success(2)]}
    asyncio.run(protocol_exercise(raw, wire))


@pytest.mark.parametrize(
    "realm,headers,code",
    [
        ("../bad", {"X-API-Key": "test-only"}, "INVALID_REQUEST"),
        (REALM, RuntimeError("secret"), "UNAUTHENTICATED"),
    ],
)
def test_local_refusals_without_dispatch(realm, headers, code):
    async def run():
        async with Client(api.mcp, timeout=5) as client:
            header_patch = (
                {"side_effect": headers}
                if isinstance(headers, Exception)
                else {"return_value": headers}
            )
            with patch.object(api, "_onto_headers", **header_patch), patch.object(
                api, "_request_with_canonical_auth"
            ) as request:
                result = await client.call_tool(
                    "create_relations_batch",
                    {"realm_id": realm, "relations": [None]},
                    raise_on_error=False,
                )
            assert result.is_error
            assert json.loads(result.content[0].text)["error"]["code"] == code
            request.assert_not_called()

    asyncio.run(run())


def test_outer_guard_sets_terminal_state_and_blocks_delayed_dispatch():
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    states = []

    def delayed_batch(**kwargs):
        state = kwargs["state"]
        states.append(state)
        entered.set()
        assert release.wait(2)
        try:
            return batch.request_batch(**kwargs)
        finally:
            finished.set()

    async def run():
        async with Client(api.mcp, timeout=5) as client:
            return await client.call_tool(
                "create_relations_batch",
                {"realm_id": REALM, "relations": [None]},
                raise_on_error=False,
            )

    with patch.object(api, "_HTTP_MCP_TOOL_TIMEOUT_SECONDS", 0.05), patch.object(
        api, "_onto_headers", return_value={}
    ), patch.object(api, "request_batch", side_effect=delayed_batch), patch.object(
        api, "_request_with_canonical_auth"
    ) as request:
        try:
            result = asyncio.run(run())
            assert entered.is_set() and result.is_error
            unknown(ToolError(result.content[0].text))
        finally:
            release.set()
        assert finished.wait(2)
        assert states[0].done.is_set() and not states[0].dispatched
        request.assert_not_called()


def test_single_relation_regression_retains_original_contract():
    async def run():
        async with Client(api.mcp, timeout=5) as client:
            with patch.object(
                api, "_request_json", return_value={"status": "OK"}
            ) as request:
                result = await client.call_tool(
                    "create_relation",
                    {
                        "realm_id": REALM,
                        "start_entity_id": REALM,
                        "end_entity_id": REALM,
                        "relation_type_name": "related",
                        "start_role": "s",
                        "end_role": "e",
                        "additional_properties": {"ordinary": "value"},
                    },
                )
            assert not result.is_error
            request.assert_called_once_with(
                "POST",
                f"{api.ONTO_API_BASE}/realm/{REALM}/entity/relation",
                json_payload={
                    "type": "related",
                    "startRelatedEntity": {"id": REALM, "role": "s"},
                    "endRelatedEntity": {"id": REALM, "role": "e"},
                    "additionalProperties": {"ordinary": "value"},
                },
                timeout=30,
            )

    asyncio.run(run())


def test_outer_guard_after_dispatch_discards_late_success():
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    states = []
    original_batch = api.request_batch

    def capture(**kwargs):
        states.append(kwargs["state"])
        return original_batch(**kwargs)

    def request(*args, **kwargs):
        entered.set()
        assert release.wait(2)
        finished.set()
        return Response(200, {"results": [success()]})

    async def run():
        async with Client(api.mcp, timeout=5) as client:
            return await client.call_tool(
                "create_relations_batch",
                {"realm_id": REALM, "relations": [None]},
                raise_on_error=False,
            )

    with patch.object(api, "_HTTP_MCP_TOOL_TIMEOUT_SECONDS", 0.05), patch.object(
        api, "_onto_headers", return_value={}
    ), patch.object(api, "request_batch", side_effect=capture), patch.object(
        api, "_request_with_canonical_auth", side_effect=request
    ) as sender:
        try:
            result = asyncio.run(run())
            assert entered.is_set() and result.is_error
            unknown(ToolError(result.content[0].text))
            terminal = states[0].value
        finally:
            release.set()
        assert finished.wait(2)
        assert states[0].value is terminal
        sender.assert_called_once()


def test_protocol_cancellation_cancels_before_dispatch():
    from types import SimpleNamespace

    state = None

    async def run():
        async def cancelled(context):
            nonlocal state
            state = batch.invocation_context.get()
            raise asyncio.CancelledError

        context = SimpleNamespace(
            method="tools/call", message=SimpleNamespace(name="create_relations_batch")
        )
        with pytest.raises(asyncio.CancelledError):
            await batch.BatchCancellationBoundary()(context, cancelled)

    asyncio.run(run())
    assert state.done.is_set() and not state.begin_dispatch()
    unknown(state.value)


@pytest.mark.parametrize("http_transport", [False, True])
def test_actual_canonical_sender_preserves_transport_credential(http_transport):
    from onto_mcp.http_auth import set_http_api_key, reset_http_api_key

    token = set_http_api_key(b"caller-key")

    async def run():
        async with Client(api.mcp, timeout=5) as client:
            with patch.object(api, "IS_HTTP_TRANSPORT", http_transport), patch.object(
                api, "ONTO_API_KEY", "configured-key"
            ), patch.object(
                api.requests,
                "request",
                return_value=Response(200, {"results": [success()]}),
            ) as sender:
                result = await client.call_tool(
                    "create_relations_batch",
                    {"realm_id": REALM.upper(), "relations": [None]},
                )
            assert not result.is_error
            sender.assert_called_once()
            headers = sender.call_args.kwargs["headers"]
            assert headers["X-API-Key"] == (
                "caller-key" if http_transport else "configured-key"
            )
            assert not {"Authorization", "X-Onto-Api-Key"} & headers.keys()

    try:
        asyncio.run(run())
    finally:
        reset_http_api_key(token)


@pytest.mark.parametrize(
    "status,body,code",
    [
        (
            401,
            {
                "error": {
                    "code": "UNAUTHENTICATED",
                    "message": "Authentication is required.",
                }
            },
            "UNAUTHENTICATED",
        ),
        (
            422,
            {
                "error": {
                    "code": "BATCH_EMPTY",
                    "message": "Batch must contain at least one relation.",
                }
            },
            "BATCH_EMPTY",
        ),
        (200, {"results": []}, "outcome_unknown"),
    ],
)
def test_real_protocol_tool_errors_are_json_without_completed_results(
    status, body, code
):
    async def run():
        async with Client(api.mcp, timeout=5) as client:
            with patch.object(api, "_onto_headers", return_value={}), patch.object(
                api, "_request_with_canonical_auth", return_value=Response(status, body)
            ) as sender:
                result = await client.call_tool(
                    "create_relations_batch",
                    {"realm_id": REALM, "relations": [None]},
                    raise_on_error=False,
                )
            assert result.is_error
            assert result.structured_content is None
            assert len(result.content) == 1
            error = json.loads(result.content[0].text)
            assert set(error) == {"error"}
            assert error["error"]["code"] == code
            assert error["error"]["retryable"] is False
            sender.assert_called_once()

    asyncio.run(run())
