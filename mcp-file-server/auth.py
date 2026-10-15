"""Bearer-token auth with roles, as plain ASGI middleware.

Two ways to present the token:
  1. Header:      Authorization: Bearer <token>
  2. Secret path: /s/<token>/mcp   (for clients whose UI cannot send headers)

Each token maps to a role: reader, writer or admin. The role is stored in a
ContextVar so tool code can check it.
"""
from __future__ import annotations

import hmac
from contextvars import ContextVar

from config import get_settings

current_role: ContextVar[str | None] = ContextVar("current_role", default=None)


def role_for_token(token: str) -> str | None:
    found = None
    for role, secret in get_settings().tokens.items():
        # compare every secret so timing does not reveal which one matched
        if hmac.compare_digest(token.encode(), secret.encode()):
            found = role
    return found


class BearerAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/health":
            await self._json(send, 200, b'{"status":"ok"}')
            return

        token = None
        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"").decode("latin-1")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        elif path.startswith("/s/"):
            token, _, rest = path[3:].partition("/")
            new_path = "/" + rest
            scope = dict(scope)
            scope["path"] = new_path
            scope["raw_path"] = new_path.encode()

        role = role_for_token(token) if token else None
        if role is None:
            await self._json(send, 401, b'{"error":"unauthorized"}')
            return

        reset = current_role.set(role)
        try:
            await self.app(scope, receive, send)
        finally:
            current_role.reset(reset)

    @staticmethod
    async def _json(send, status: int, body: bytes):
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})
