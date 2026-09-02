"""Mutation API guard tests."""

from fastapi import HTTPException

from app.core.config import settings
from app.core.security import require_admin


def test_admin_guard_accepts_matching_key(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "secret")
    require_admin("secret")


def test_admin_guard_rejects_wrong_key(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "secret")
    try:
        require_admin("wrong")
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("wrong admin key was accepted")
