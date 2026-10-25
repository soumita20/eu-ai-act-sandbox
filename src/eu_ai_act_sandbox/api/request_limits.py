"""ASGI request-body size guard for the HTTP API."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

ASGIMessage = dict[str, Any]
ASGIReceive = Callable[[], Awaitable[ASGIMessage]]
ASGISend = Callable[[ASGIMessage], Awaitable[None]]
ASGIApp = Callable[[dict[str, Any], ASGIReceive, ASGISend], Awaitable[None]]
REQUEST_BODY_TOO_LARGE_SCOPE_KEY = "eu_ai_act_request_body_too_large"
DEFAULT_MAX_REQUEST_BODY_BYTES = 65_536


class RequestBodyLimitMiddleware:
    """Buffer at most the configured limit before dispatching an HTTP request.

    Oversized requests are marked in the ASGI scope. The application middleware
    converts that marker into its normal sanitized 413 response and telemetry.
    """

    def __init__(
        self, app: ASGIApp, *, max_body_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES
    ) -> None:
        if max_body_bytes < 1:
            raise ValueError("max_body_bytes must be positive")
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(
        self, scope: dict[str, Any], receive: ASGIReceive, send: ASGISend
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        content_length = _content_length(scope)
        oversized = content_length is not None and content_length > self.max_body_bytes
        messages: list[ASGIMessage] = []
        body_size = 0

        while not oversized:
            message = await receive()
            if message.get("type") == "http.disconnect":
                messages.append(message)
                break
            if message.get("type") == "http.request":
                body_size += len(message.get("body", b""))
                if body_size > self.max_body_bytes:
                    oversized = True
                    messages.clear()
                    break
                messages.append(message)
                if not message.get("more_body", False):
                    break
            else:
                messages.append(message)

        if oversized:
            scope[REQUEST_BODY_TOO_LARGE_SCOPE_KEY] = True
            replayed = False

            async def receive_bounded() -> ASGIMessage:
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": b"", "more_body": False}
                return await receive()

            await self.app(scope, receive_bounded, send)
            return

        message_index = 0
        disconnected = False

        async def receive_buffered() -> ASGIMessage:
            nonlocal message_index, disconnected
            if disconnected:
                return {"type": "http.disconnect"}
            if message_index < len(messages):
                message = messages[message_index]
                message_index += 1
                disconnected = message.get("type") == "http.disconnect"
                return message
            return await receive()

        await self.app(scope, receive_buffered, send)


def _content_length(scope: dict[str, Any]) -> int | None:
    for name, value in scope.get("headers", []):
        if name.lower() == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None
