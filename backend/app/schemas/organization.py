from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WorkCenterCreate(BaseModel):
    name: str
    code: str | None = Field(default=None, max_length=50)
    address: str | None = None
    city: str | None = None


class WorkCenterRead(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    code: str
    address: str | None
    city: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    name: str
    code: str | None = Field(default=None, max_length=50)
    work_center_id: UUID | None = None


class DepartmentRead(BaseModel):
    id: UUID
    work_center_id: UUID
    name: str
    code: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgTreeCompany(BaseModel):
    id: UUID
    name: str
    work_centers: list["OrgTreeWorkCenter"]


class OrgTreeWorkCenter(BaseModel):
    id: UUID
    name: str
    code: str
    departments: list[DepartmentRead]


class GroupTemplateRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    permissions: list[str]
    is_system: bool
    sort_order: int

    model_config = {"from_attributes": True}


class GroupTemplateUpdate(BaseModel):
    permissions: list[str] | None = None
    description: str | None = None
