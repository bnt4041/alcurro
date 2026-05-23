from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


class GroupRead(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]
    member_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupMemberUpdate(BaseModel):
    group_ids: list[UUID]


class PermCatalogItem(BaseModel):
    key: str
    label: str


class PlatformLoginRequest(BaseModel):
    email: str
    password: str


class PlatformUserMe(BaseModel):
    id: UUID
    email: str
    full_name: str
    scope: str = "platform"
