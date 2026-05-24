"""Registro de envíos de correo electrónico."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class MailLog(SQLModel, table=True):
    __tablename__ = "mail_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    to_address: str = Field(max_length=255, index=True)
    subject: str = Field(max_length=500)
    event_type: str = Field(max_length=50, index=True)
    success: bool = Field(default=False, index=True)
    detail: str | None = Field(default=None, max_length=1000)
    tenant_id: UUID | None = Field(default=None, foreign_key="tenants.id", index=True)
    envelope_id: UUID | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
