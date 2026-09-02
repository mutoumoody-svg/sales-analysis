"""Small API-key guard for operational mutation endpoints."""

from secrets import compare_digest

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    """Require X-Admin-Key when an admin key is configured.

    Development remains usable before a key is configured. Production fails
    closed so imports and external sync cannot be exposed accidentally.
    """
    expected = settings.ADMIN_API_KEY.strip()
    if not expected:
        if settings.ENVIRONMENT.lower() in {"development", "test"}:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY is required for production mutations",
        )
    if not x_admin_key or not compare_digest(x_admin_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Key",
        )
