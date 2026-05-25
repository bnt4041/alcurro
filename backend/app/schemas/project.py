from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    planned_hours: float | None = Field(default=None, ge=0, le=100000)
    is_active: bool = True
    active_for_clock: bool = True


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    planned_hours: float | None = Field(default=None, ge=0, le=100000)
    is_active: bool | None = None
    active_for_clock: bool | None = None


class ProjectBulkImportRow(BaseModel):
    name: str = ""
    address: str = ""
    planned_hours: str = ""
    is_active: str = "si"


class ProjectBulkImportRequest(BaseModel):
    rows: list[ProjectBulkImportRow] = Field(min_length=1, max_length=500)


class ProjectBulkImportResponse(BaseModel):
    created: int
    errors: list[str] = Field(default_factory=list)


class ProjectRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    company_id: UUID
    name: str
    code: str
    address: str | None
    planned_hours: float | None
    is_active: bool
    active_for_clock: bool
    created_at: datetime
    updated_at: datetime
