"""Dual HTTP transport: existing key sessions and MCP-owned OAuth sessions."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager

from .http_auth import InvalidHttpCredentials, classify_http_credentials
from .oauth import (
    OAuthConfig,
    OAuthError,
    OAuthService,
    current_authority,
)
from .oauth_state import SWEEP_INTERVAL, configured_store
from .utils import safe_print


async def respond(send, status, payload, config=None):
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
    ]
    if config and status in {401, 403}:
        error = payload["error"]
        challenge = f'Bearer resource_metadata="{config.metadata_url}", error="{error}"'
        headers.append((b"www-authenticate", challenge.encode("ascii")))
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class DualAuthASGIApp:
    def __init__(self, key_app, oauth_app=None, *, service=None, store=None):
        self.key_app, self.oauth_app, self.service, self.store = (
            key_app,
            oauth_app,
            service,
            store,
        )

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.key_app(scope, receive, send)
            return
        config = self.service.config if self.service else None
        if config and scope.get("path") == "/.well-known/oauth-protected-resource/mcp":
            await respond(send, 200, config.metadata())
            return
        if scope.get("path") != "/mcp":
            await self.key_app(scope, receive, send)
            return
        try:
            key, bearer = classify_http_credentials(scope.get("headers", ()))
        except InvalidHttpCredentials:
            await respond(send, 400, {"error": "Invalid authentication credentials."})
            return
        if key is not None:
            # A key never inherits a session initialized under OAuth.
            ids = [
                v for k, v in scope.get("headers", ()) if k.lower() == b"mcp-session-id"
            ]
            if any(len(v) == 43 for v in ids):
                await respond(send, 401, {"error": "unauthorized"})
                return
            await self.key_app(scope, receive, send)
            return
        if bearer is None:
            await respond(send, 401, {"error": "unauthorized"}, config)
            return
        if self.service is None:
            await respond(send, 401, {"error": "invalid_token"})
            return
        authority = None
        context_token = None
        started = False

        async def tracked_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                if authority and new_session:
                    message = {
                        **message,
                        "headers": list(message.get("headers", ()))
                        + [(b"mcp-session-id", authority.session_id.encode("ascii"))],
                    }
            await send(message)

        async def tracked_receive():
            message = await receive()
            if message["type"] == "http.disconnect" and authority:
                authority.cancelled.set()
            return message

        try:
            authority = await asyncio.to_thread(self.service.authenticate, bearer)
            await asyncio.to_thread(self.service.authorize, authority)
            authority.state_store = self.store
            values = [
                v for k, v in scope.get("headers", ()) if k.lower() == b"mcp-session-id"
            ]
            if len(values) > 1:
                raise OAuthError("Invalid authentication credentials.", 400)
            new_session = not values
            replay = []
            if new_session:
                if scope.get("method") != "POST":
                    raise OAuthError()
                body = bytearray()
                while True:
                    message = await tracked_receive()
                    replay.append(message)
                    if message["type"] != "http.request":
                        raise OAuthError()
                    body.extend(message.get("body", b""))
                    if len(body) > 4194304:
                        raise OAuthError("invalid_request", 400)
                    if not message.get("more_body"):
                        break
                try:
                    payload = json.loads(body)
                    if (
                        not isinstance(payload, dict)
                        or payload.get("method") != "initialize"
                    ):
                        raise ValueError()
                except (ValueError, TypeError):
                    raise OAuthError("invalid_request", 400) from None
                authority.session_id = await asyncio.to_thread(
                    self.store.initialize, authority.claims.connection_key
                )
            else:
                try:
                    authority.session_id = values[0].decode("ascii")
                except UnicodeError:
                    raise OAuthError() from None
                await asyncio.to_thread(
                    self.store.require,
                    authority.session_id,
                    authority.claims.connection_key,
                )
            if scope.get("method") == "DELETE":
                await asyncio.to_thread(
                    self.store.remove,
                    authority.session_id,
                    authority.claims.connection_key,
                )
                await respond(send, 200, {})
                return

            async def replay_receive():
                if replay:
                    return replay.pop(0)
                return await tracked_receive()

            context_token = current_authority.set(authority)
            await self.oauth_app(scope, replay_receive, tracked_send)
        except OAuthError as exc:
            if not started:
                await respond(send, exc.status, exc.payload, config)
            else:
                raise
        finally:
            if authority:
                authority.cancelled.set()
            if context_token is not None:
                current_authority.reset(context_token)


def build_dual_app(mcp, key_app, **app_options):
    config = OAuthConfig.from_env()
    if not config.enabled:
        return DualAuthASGIApp(key_app)
    service = OAuthService(config)
    store = configured_store(service, os.environ)
    oauth_app = mcp.http_app(stateless_http=True, **app_options)
    # Both transports run their own declared lifespans; the OAuth transport is
    # stateless because the durable binding/ownership is exclusively MCP-owned.
    original_lifespan = key_app.router.lifespan_context

    async def maintenance():
        while True:
            await asyncio.sleep(SWEEP_INTERVAL)
            try:
                if await asyncio.to_thread(store.sweep):
                    safe_print(
                        "[oauth-state] maintenance bound missed; complete catch-up finished."
                    )
            except OAuthError:
                safe_print(
                    "[oauth-state] maintenance unavailable; protected state use denied."
                )

    @asynccontextmanager
    async def lifespan(app):
        await asyncio.to_thread(store.sweep)
        worker = asyncio.create_task(maintenance())
        try:
            async with original_lifespan(app), oauth_app.router.lifespan_context(
                oauth_app
            ):
                yield
        finally:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass

    key_app.router.lifespan_context = lifespan
    return DualAuthASGIApp(key_app, oauth_app, service=service, store=store)
