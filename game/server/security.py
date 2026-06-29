import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="token", auto_error=False)


class ApiKeyManager:
    KEY = secrets.token_urlsafe()

    @classmethod
    def verify(
        cls,
        api_key_header: str | None = Security(API_KEY_HEADER),
        api_key_query: str | None = Security(API_KEY_QUERY),
    ) -> None:
        # Accept the per-process key via the X-API-Key header OR a ?token= query
        # param, so an LLM agent can authenticate with nothing but a pasted URL.
        if cls.KEY not in (api_key_header, api_key_query):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
