from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MailSettingsRead(BaseModel):
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_use_tls: bool
    mail_from_address: str | None
    mail_from_name: str | None
    smtp_password_configured: bool
    updated_at: datetime


class MailSettingsUpdate(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool | None = None
    mail_from_address: str | None = None
    mail_from_name: str | None = None


class MailLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    to_address: str
    subject: str
    event_type: str
    success: bool
    detail: str | None
    tenant_id: UUID | None
    envelope_id: UUID | None
    created_at: datetime


class MailTestRequest(BaseModel):
    to_email: str = Field(min_length=5, max_length=255)
