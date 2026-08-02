from __future__ import annotations

import json
import platform
from collections.abc import Awaitable, Callable
from importlib import metadata
from typing import Any

from pydantic import ValidationError

from .api_resources import mcp
from .realm_agent_admission import RealmAgentAdmissionToolArguments
from .settings import (
    MCP_ALLOWED_HOSTS,
    MCP_ALLOWED_ORIGINS,
    MCP_HEALTH_PATH,
    MCP_REF,
    MCP_TRANSPORT,
    PORT,
    validate_runtime_settings,
)
from .utils import safe_print

ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]
ASGIApp = Callable[[dict[str, Any], ASGIReceive, ASGISend], Awaitable[None]]

_ADMISSION_TOOL_NAME = "admit_realm_agent"
_INVALID_PARAMS_CODE = -32602
_INVALID_PARAMS_MESSAGE = "Invalid params"


def _parse_csv_setting(value: str) -> list[str] | None:
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def _package_version(package_name: str) -> str:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return "not-installed"


def _runtime_metadata() -> dict[str, str]:
    return {
        "app": "Onto MCP Server",
        "transport": MCP_TRANSPORT,
        "port": str(PORT),
        "mcp_ref": MCP_REF or "unknown",
        "package_version": _package_version("onto-mcp-server"),
        "fastmcp_version": _package_version("fastmcp"),
        "python_version": platform.python_version(),
    }


def _startup_message() -> str:
    metadata_items = ", ".join(f"{key}={value}" for key, value in _runtime_metadata().items())
    return f"[server] {metadata_items}"


async def _send_json_response(send: ASGISend, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class HealthCheckASGIApp:
    def __init__(self, app: ASGIApp, health_path: str = MCP_HEALTH_PATH) -> None:
        self.app = app
        self.health_path = health_path if health_path.startswith("/") else f"/{health_path}"

    async def __call__(self, scope: dict[str, Any], receive: ASGIReceive, send: ASGISend) -> None:
        if scope.get("type") == "http" and scope.get("path") == self.health_path:
            await _send_json_response(
                send,
                200,
                {
                    "status": "ok",
                    "app": "Onto MCP Server",
                    "transport": MCP_TRANSPORT,
                    "mcp_ref": MCP_REF or "unknown",
                },
            )
            return

        await self.app(scope, receive, send)


def _invalid_admission_request_id(payload: Any) -> str | int | None:
    if (
        not isinstance(payload, dict)
        or payload.get("jsonrpc") != "2.0"
        or payload.get("method") != "tools/call"
        or "id" not in payload
    ):
        return None
    params = payload.get("params")
    if not isinstance(params, dict) or params.get("name") != _ADMISSION_TOOL_NAME:
        return None
    try:
        RealmAgentAdmissionToolArguments.model_validate(params.get("arguments"))
    except ValidationError:
        request_id = payload["id"]
        if isinstance(request_id, (str, int)) and not isinstance(request_id, bool):
            return request_id
    return None


def _json_rpc_payload_from_response(body: bytes, content_type: str) -> Any:
    try:
        if content_type.startswith("text/event-stream"):
            for line in body.splitlines():
                if line.startswith(b"data: "):
                    return json.loads(line[6:])
            return None
        return json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _invalid_params_response_body(request_id: str | int, content_type: str) -> bytes:
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": _INVALID_PARAMS_CODE,
            "message": _INVALID_PARAMS_MESSAGE,
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    if content_type.startswith("text/event-stream"):
        return b"event: message\r\ndata: " + encoded + b"\r\n\r\n"
    return encoded


class RealmAgentAdmissionInvalidParamsASGIApp:
    """Preserve FastMCP transport handling while normalizing one tool's schema error."""

    def __init__(self, app: ASGIApp, mcp_path: str = "/mcp") -> None:
        self.app = app
        self.mcp_path = mcp_path

    async def __call__(
        self, scope: dict[str, Any], receive: ASGIReceive, send: ASGISend
    ) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != self.mcp_path
        ):
            await self.app(scope, receive, send)
            return

        received: list[dict[str, Any]] = []
        body_parts: list[bytes] = []
        while True:
            message = await receive()
            received.append(message)
            if message.get("type") != "http.request":
                break
            body_parts.append(message.get("body", b""))
            if not message.get("more_body", False):
                break

        request_id: str | int | None = None
        try:
            request_id = _invalid_admission_request_id(json.loads(b"".join(body_parts)))
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

        replay_index = 0

        async def replay_receive() -> dict[str, Any]:
            nonlocal replay_index
            if replay_index < len(received):
                message = received[replay_index]
                replay_index += 1
                return message
            return await receive()

        if request_id is None:
            await self.app(scope, replay_receive, send)
            return

        sent: list[dict[str, Any]] = []

        async def capture_send(message: dict[str, Any]) -> None:
            sent.append(message)

        await self.app(scope, replay_receive, capture_send)

        start = next(
            (item for item in sent if item.get("type") == "http.response.start"), None
        )
        if start is None or start.get("status") != 200:
            for message in sent:
                await send(message)
            return

        headers = list(start.get("headers", []))
        content_type = next(
            (
                value.decode("latin-1")
                for name, value in headers
                if name.lower() == b"content-type"
            ),
            "",
        )
        response_body = b"".join(
            item.get("body", b"")
            for item in sent
            if item.get("type") == "http.response.body"
        )
        response_payload = _json_rpc_payload_from_response(response_body, content_type)
        if not (
            isinstance(response_payload, dict)
            and response_payload.get("jsonrpc") == "2.0"
            and response_payload.get("id") == request_id
            and "error" not in response_payload
            and isinstance(response_payload.get("result"), dict)
            and response_payload["result"].get("isError") is True
        ):
            for message in sent:
                await send(message)
            return

        replacement_body = _invalid_params_response_body(request_id, content_type)
        replacement_headers = [
            (name, value)
            for name, value in headers
            if name.lower() != b"content-length"
        ]
        if any(name.lower() == b"content-length" for name, _ in headers):
            replacement_headers.append(
                (b"content-length", str(len(replacement_body)).encode("ascii"))
            )
        await send({**start, "headers": replacement_headers})
        await send({"type": "http.response.body", "body": replacement_body})


def _build_http_app() -> HealthCheckASGIApp:
    app = mcp.http_app(
        allowed_hosts=_parse_csv_setting(MCP_ALLOWED_HOSTS),
        allowed_origins=_parse_csv_setting(MCP_ALLOWED_ORIGINS),
    )
    return HealthCheckASGIApp(RealmAgentAdmissionInvalidParamsASGIApp(app))


def run() -> None:
    """Entry-point for both CLI (stdio) and HTTP server."""
    validate_runtime_settings()

    if MCP_TRANSPORT == "stdio":
        safe_print(_startup_message())
        mcp.run()
    elif MCP_TRANSPORT == "http":
        safe_print(_startup_message())
        import uvicorn

        uvicorn.run(_build_http_app(), host="0.0.0.0", port=PORT)
    else:
        raise ValueError("MCP_TRANSPORT must be 'stdio' or 'http'")


if __name__ == "__main__":
    run()
