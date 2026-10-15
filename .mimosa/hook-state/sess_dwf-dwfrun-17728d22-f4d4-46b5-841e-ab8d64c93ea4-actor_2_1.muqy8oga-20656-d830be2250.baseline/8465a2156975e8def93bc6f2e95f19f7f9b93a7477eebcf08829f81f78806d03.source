import logging
import os
import time
from typing import Any

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Enterprise Security: JWT secret is loaded LAZILY at request time, not at import time.
# This allows pytest and local dev environments to import the module without a full .env.
# Security is MAINTAINED (fail-closed): any actual JWT operation will raise
# RuntimeError if SCP_JWT_SECRET is missing, blocking the request completely.
# To start SCP: set SCP_JWT_SECRET in .env (see .env.example).


def _get_jwt_secret() -> str:
    secret = os.environ.get("SCP_JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "[SECURITY FATAL] SCP_JWT_SECRET is not set. "
            "Set it in .env before starting SCP. See .env.example for details."
        )
    return secret


JWT_ALGORITHM = "HS256"
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: int = 3600) -> str:
    to_encode = data.copy()
    expire = time.time() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict[str, Any]:
    token = credentials.credentials.strip() if hasattr(credentials, "credentials") else str(credentials).strip()
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except (jwt.InvalidTokenError, Exception):
        logger.debug("JWT verification failed (invalid or malformed token)", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_api_key(credentials: HTTPAuthorizationCredentials | str = Security(security)) -> dict[str, Any]:
    token = credentials.credentials.strip() if hasattr(credentials, "credentials") else str(credentials).strip()
    import secrets as _secrets
    for env_key in ("SCP_ADMIN_KEY", "SCP_AUTH_TOKEN_SECRET"):
        expected = os.environ.get(env_key, "").strip()
        if expected and _secrets.compare_digest(token.encode("utf-8"), expected.encode("utf-8")):
            return {"sub": "admin", "role": "admin", "auth_type": "api_key"}

    expected_user = os.environ.get("SCP_API_KEY", "").strip()
    if expected_user and _secrets.compare_digest(token.encode("utf-8"), expected_user.encode("utf-8")):
        return {"sub": "user", "role": "user", "auth_type": "api_key"}

    raise HTTPException(status_code=401, detail="Invalid API key")


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    # 1. Try JWT
    try:
        payload = verify_jwt_token(credentials)
        user = payload.get("sub")
        if user:
            return user
    except HTTPException as exc:
        logger.debug("JWT verification failed in get_current_user fallback: %s", exc)

    # 2. Try API key (SCP_ADMIN_KEY, SCP_AUTH_TOKEN_SECRET, SCP_API_KEY)
    try:
        api_payload = verify_api_key(credentials)
        return api_payload.get("sub", "admin")
    except HTTPException as exc:
        logger.debug("API key verification failed in get_current_user fallback: %s", exc)

    raise HTTPException(status_code=401, detail="Invalid token")
