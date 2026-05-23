from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_HOURS = 12

PANEL_ROLES = frozenset(
    {
        "tenant_admin",
        "manager",
        "labor_inspector",
        "admin",
        "supervisor",
    }
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(
    subject: UUID,
    role: str,
    tenant_id: UUID,
    company_id: UUID,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_HOURS)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "employee",
        "role": role,
        "tenant_id": str(tenant_id),
        "company_id": str(company_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_platform_token(subject: UUID) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_HOURS)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "platform",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Token inválido") from exc
