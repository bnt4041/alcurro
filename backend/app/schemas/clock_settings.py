from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InboundDocumentTypeRead(BaseModel):
    code: str
    name: str
    description: str
    optional: bool = False
    kind: str = "catalog"


class CompanySignatureDocumentRead(BaseModel):
    id: UUID
    company_id: UUID | None
    company_name: str | None
    title: str
    file_name: str
    document_type: str


class ClockSettingsRead(BaseModel):
    tenant_id: UUID
    require_geolocation: bool
    clock_reminder_minutes: int | None
    incident_reminder_enabled: bool
    incident_reminder_minutes: int | None
    inbound_documents_enabled: bool
    inbound_document_codes: list[str]
    inbound_signature_delivery_ids: list[UUID] = Field(default_factory=list)
    send_welcome_with_documents: bool
    welcome_message_extra: str | None
    daily_summary_enabled: bool
    require_project_on_clock_in: bool
    updated_at: datetime
    available_inbound_types: list[InboundDocumentTypeRead] = Field(default_factory=list)
    company_signature_documents: list[CompanySignatureDocumentRead] = Field(
        default_factory=list
    )


class ClockSettingsUpdate(BaseModel):
    require_geolocation: bool | None = None
    clock_reminder_minutes: int | None = Field(default=None, ge=0, le=1440)
    incident_reminder_enabled: bool | None = None
    incident_reminder_minutes: int | None = Field(default=None, ge=0, le=1440)
    inbound_documents_enabled: bool | None = None
    inbound_document_codes: list[str] | None = None
    inbound_signature_delivery_ids: list[UUID] | None = None
    send_welcome_with_documents: bool | None = None
    welcome_message_extra: str | None = Field(default=None, max_length=1000)
    daily_summary_enabled: bool | None = None
    require_project_on_clock_in: bool | None = None


class EmployeeInboundDocumentRead(BaseModel):
    id: UUID
    employee_id: UUID
    document_code: str
    document_name: str
    status: str
    document_delivery_id: UUID | None
    signature_envelope_id: UUID | None = None
    received_at: datetime | None
    created_at: datetime


class ClockReminderRunResult(BaseModel):
    sent: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
