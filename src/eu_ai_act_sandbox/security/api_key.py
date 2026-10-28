"""Dependency-free validation for bearer API-key credentials."""

from __future__ import annotations

import hmac


def is_valid_bearer_key(
    scheme: str | None, credential: str | None, expected_key: str
) -> bool:
    """Return whether the supplied bearer credential matches the configured key."""
    if scheme is None or credential is None or scheme.casefold() != "bearer":
        return False
    return hmac.compare_digest(credential.encode("utf-8"), expected_key.encode("utf-8"))
