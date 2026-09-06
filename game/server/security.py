import secrets
from typing import Any

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="token", auto_error=False)


class ApiKeyManager:
    # Per-process fallback used before any campaign is loaded (server up, no game yet).
    KEY = secrets.token_urlsafe()

    @classmethod
    def current_key(cls) -> str:
        """The active campaign's persisted OPFOR-AI token, so the connect URL stays the
        same across restarts of the same save. Falls back to the per-process key when no
        game is loaded (or in headless/test contexts without a GameModel)."""
        try:
            from game.server.dependencies import GameContext

            game = GameContext.get()
        except Exception:
            game = None
        token = getattr(game, "opfor_ai_token", None) if game is not None else None
        return token or cls.KEY

    @classmethod
    def verify(
        cls,
        api_key_header: str | None = Security(API_KEY_HEADER),
        api_key_query: str | None = Security(API_KEY_QUERY),
    ) -> None:
        # Accept the campaign token via the X-API-Key header OR a ?token= query param,
        # so an LLM agent can authenticate with nothing but a pasted URL.
        if cls.current_key() not in (api_key_header, api_key_query):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


class TokenAuthMiddleware:
    """ASGI middleware gating a mounted sub-app (e.g. the MCP app) on the
    per-process key — supplied as ``?token=`` or the ``X-API-Key`` header.
    Non-HTTP scopes (lifespan) pass through untouched."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            from urllib.parse import parse_qs

            params = parse_qs(scope.get("query_string", b"").decode())
            token = params.get("token", [None])[0]
            if token is None:
                headers = dict(scope.get("headers") or [])
                raw = headers.get(b"x-api-key")
                token = raw.decode() if raw else None
            if token != ApiKeyManager.current_key():
                await send(
                    {
                        "type": "http.response.start",
                        "status": status.HTTP_403_FORBIDDEN,
                        "headers": [(b"content-type", b"text/plain")],
                    }
                )
                await send({"type": "http.response.body", "body": b"Forbidden"})
                return
        await self.app(scope, receive, send)
