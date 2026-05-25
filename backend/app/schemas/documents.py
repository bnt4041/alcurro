from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    sort_order: int = 0


class DocumentTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class DocumentTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    sort_order: int
    created_at: datetime


class DocumentTagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str | None = Field(default=None, max_length=20)


class DocumentTagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    is_active: bool | None = None


class DocumentTagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    name: str
    color: str | None
    is_active: bool
    created_at: datetime


class DocumentDeliveryRead(BaseModel):
    id: UUID
    tenant_id: UUID
    company_id: UUID | None = None
    employee_id: UUID | None = None
    document_type_id: UUID | None = None
    document_type: str
    document_type_name: str | None = None
    file_path: str
    file_name: str
    title: str | None = None
    expires_at: date | None = None
    is_expired: bool = False
    tag_ids: list[UUID] = Field(default_factory=list)
    tags: list[DocumentTagRead] = Field(default_factory=list)
    requires_acknowledgment: bool = True
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledgment_text: str | None = None
    created_at: datetime


class DocumentDeliveryUpdate(BaseModel):
    document_type_id: UUID | None = None
    title: str | None = None
    expires_at: date | None = None
    requires_acknowledgment: bool | None = None
    tag_ids: list[UUID] | None = None


class BulkPayrollItemResult(BaseModel):
    source_file: str
    page: int | None = None
    id_document: str | None = None
    employee_id: UUID | None = None
    employee_name: str | None = None
    status: str
    document_id: UUID | None = None
    message: str | None = None


class BulkPayrollResponse(BaseModel):
    total_files: int
    total_pages: int
    assigned: int
    skipped: int
    errors: int
    items: list[BulkPayrollItemResult]


class DocumentNotificationSettingsRead(BaseModel):
    tenant_id: UUID
    enabled: bool
    days_before: list[int]
    channel_whatsapp: bool
    channel_email: bool
    notify_employee: bool
    notify_managers: bool
    extra_emails: list[str]
    updated_at: datetime


class DocumentNotificationSettingsUpdate(BaseModel):
    enabled: bool | None = None
    days_before: list[int] | None = None
    channel_whatsapp: bool | None = None
    channel_email: bool | None = None
    notify_employee: bool | None = None
    notify_managers: bool | None = None
    extra_emails: list[str] | None = None


class ExpiryNotificationRunResult(BaseModel):
    checked: int
    sent: int
    skipped: int
    errors: int
    details: list[str] = Field(default_factory=list)


class DownloadZipRequest(BaseModel):
    ids: list[UUID] | None = None
