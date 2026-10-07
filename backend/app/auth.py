"""FastAPI security dependencies for CreditPath admin endpoints."""
from __future__ import annotations

import secrets
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_config

# Header-based API key auth: X-Admin-API-Key: <secret>
api_key_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)

# Bearer token auth: Authorization: Bearer <token>
bearer_auth = HTTPBearer(auto_error=False)


def require_admin_auth(
    api_key: str | None = Security(api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_auth),
) -> str:
    """
    Authenticate administrative requests via either:
    1. 'X-Admin-API-Key' header matching configured admin_api_key, OR
    2. 'Authorization: Bearer <token>' header matching admin_token.
    """
    cfg = get_config()
    expected_api_key = cfg.admin_api_key
    expected_token = cfg.admin_token

    is_api_key_valid = False
    if api_key and expected_api_key:
        is_api_key_valid = secrets.compare_digest(api_key, expected_api_key)

    is_token_valid = False
    if credentials and credentials.credentials and expected_token:
        is_token_valid = secrets.compare_digest(credentials.credentials, expected_token)

    if not (is_api_key_valid or is_token_valid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required. Provide a valid 'X-Admin-API-Key' or 'Authorization: Bearer <token>' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return "admin"
