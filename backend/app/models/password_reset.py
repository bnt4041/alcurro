"""Tokens de recuperación de contraseña."""

import secrets
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class PasswordResetToken(SQLModel, table=True):
    """Token único para restablecer contraseña. Válido 15 minutos, un solo uso."""

    __tablename__ = "password_reset_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        max_length=64,
        unique=True,
        index=True,
    )
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=15)
    )
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
