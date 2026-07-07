from __future__ import annotations

import json
import platform
from importlib import metadata
from typing import Any, Awaitable, Callable

from .api_resources import mcp
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


def _build_http_app() -> HealthCheckASGIApp:
    app = mcp.http_app(
        allowed_hosts=_parse_csv_setting(MCP_ALLOWED_HOSTS),
        allowed_origins=_parse_csv_setting(MCP_ALLOWED_ORIGINS),
    )
    return HealthCheckASGIApp(app)


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
