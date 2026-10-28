"""Local bearer-key authentication for protected API operations."""

from __future__ import annotations

from collections.abc import Callable
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from eu_ai_act_sandbox.security.api_key import is_valid_bearer_key

def create_bearer_key_dependency(
    expected_key: str,
    *,
    scheme_name: str = "SandboxBearerKey",
    description: str = "Local API key sent as an HTTP bearer token.",
) -> Callable[..., None]:
    """Return a FastAPI dependency that validates the configured API key."""
    if len(expected_key) < 32:
        raise ValueError("bearer API keys must contain at least 32 characters")
    bearer_scheme = HTTPBearer(
        auto_error=False,
        scheme_name=scheme_name,
        description=description,
    )

    def authenticate(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> None:
        if (
            credentials is None
            or not is_valid_bearer_key(
                credentials.scheme, credentials.credentials, expected_key
            )
        ):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return authenticate
