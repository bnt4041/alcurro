from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AudienceFilter(BaseModel):
    company: bool = False
    company_ids: list[UUID] = Field(default_factory=list)
    work_center_ids: list[UUID] = Field(default_factory=list)
    department_ids: list[UUID] = Field(default_factory=list)
    supervisor_ids: list[UUID] = Field(default_factory=list)
    employee_ids: list[UUID] = Field(default_factory=list)


class ExternalRecipient(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = None
    email: str | None = None
    id_document: str | None = None


class CommunicationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    mode: str = "open"  # open | signature
    audience: AudienceFilter = Field(default_factory=AudienceFilter)
    externals: list[ExternalRecipient] = Field(default_factory=list)
    expires_in_days: int = Field(default=14, ge=1, le=90)


class CommunicationAddRecipients(BaseModel):
    audience: AudienceFilter = Field(default_factory=AudienceFilter)
    externals: list[ExternalRecipient] = Field(default_factory=list)


class CommunicationCancel(BaseModel):
    reason: str | None = None


class RecipientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    employee_id: UUID | None
    is_external: bool
    full_name: str
    phone: str | None
    email: str | None
    id_document: str | None
    status: str
    sent_at: datetime | None
    read_at: datetime | None
    signed_at: datetime | None
    error: str | None


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    file_name: str
    mimetype: str | None


class CommunicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    body: str
    mode: str
    status: str
    created_at: datetime
    sent_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    recipient_count: int = 0
    sent_count: int = 0
    signed_count: int = 0


class CommunicationDetail(CommunicationRead):
    recipients: list[RecipientRead] = Field(default_factory=list)
    attachments: list[AttachmentRead] = Field(default_factory=list)
