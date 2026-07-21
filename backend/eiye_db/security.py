"""API-key authentication."""

from dataclasses import dataclass

from fastapi import Header, HTTPException

from eiye_db.config import settings


@dataclass
class Identity:
    key_id: str
    is_admin: bool


def require_api_key(x_api_key: str | None = Header(None)) -> Identity:
    """FastAPI dependency. Unset EIYE_API_KEY means open dev mode."""
    if settings.api_key is None:
        return Identity(key_id="dev", is_admin=True)
    if x_api_key is not None and settings.admin_api_key is not None and x_api_key == settings.admin_api_key:
        return Identity(key_id="admin", is_admin=True)
    if x_api_key is not None and x_api_key == settings.api_key:
        return Identity(key_id="primary", is_admin=False)
    raise HTTPException(status_code=401, detail="Invalid or missing API key")
