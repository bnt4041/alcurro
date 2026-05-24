"""Tokens de firma (hash + OTP)."""

import hashlib
import secrets
from datetime import datetime, timedelta

from app.config import get_settings


def hash_token(token: str) -> str:
    pepper = get_settings().jwt_secret
    return hashlib.sha256(f"{pepper}:{token}".encode()).hexdigest()


def generate_signer_token() -> tuple[str, str]:
    plain = secrets.token_urlsafe(32)
    return plain, hash_token(plain)


def generate_otp() -> tuple[str, str]:
    code = f"{secrets.randbelow(1_000_000):06d}"
    return code, hash_otp(code)


def hash_otp(code: str) -> str:
    pepper = get_settings().jwt_secret
    return hashlib.sha256(f"otp:{pepper}:{code}".encode()).hexdigest()


def otp_expires_at(minutes: int = 10) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutes)
