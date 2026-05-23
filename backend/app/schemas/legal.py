from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LegalDocumentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    is_active: bool = True
    is_required: bool = True
    sort_order: int = 0


class LegalDocumentUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    is_active: bool | None = None
    is_required: bool | None = None
    sort_order: int | None = None
    bump_version: bool = False


class LegalDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    title: str
    body: str
    version: int
    is_active: bool
    is_required: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class LegalAcceptanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    legal_document_id: UUID
    document_version: int
    accepted_at: datetime


class EmployeeLegalStatusItem(BaseModel):
    document_id: UUID
    code: str
    title: str
    body: str
    version: int
    is_required: bool
    accepted: bool
    accepted_at: datetime | None
    accepted_version: int | None
    needs_reaccept: bool = False


class EmployeeLegalStatusRead(BaseModel):
    employee_id: UUID
    all_required_accepted: bool
    items: list[EmployeeLegalStatusItem]


class LegalAcceptRequest(BaseModel):
    employee_id: UUID | None = None
