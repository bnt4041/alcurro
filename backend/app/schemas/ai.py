from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AiActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    description: str | None
    category: str
    sort_order: int
    is_active: bool


class AiProfileActionCell(BaseModel):
    profile_key: str
    enabled: bool


class AiActionMatrixRow(BaseModel):
    action: AiActionRead
    profiles: list[AiProfileActionCell]


class AiMatrixCellUpdate(BaseModel):
    action_id: UUID
    profile_key: str
    enabled: bool


class AiActionMatrixUpdate(BaseModel):
    cells: list[AiMatrixCellUpdate] = Field(default_factory=list)


class AiConversationRuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=4000)
    priority: int = Field(default=100, ge=0, le=9999)
    is_active: bool = True


class AiConversationRuleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    priority: int | None = Field(default=None, ge=0, le=9999)
    is_active: bool | None = None


class AiConversationRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    content: str
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AiRulesReorder(BaseModel):
    rule_ids: list[UUID] = Field(min_length=1)


class AiUsageSummary(BaseModel):
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    request_count: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    total_duration_ms: int
    last_used_at: datetime | None


class AiTenantUsageDetail(BaseModel):
    tenant_id: UUID
    period_label: str
    request_count: int
    total_tokens: int
    total_duration_ms: int
    by_action: list[dict]
    by_profile: list[dict]
    recent: list[dict]


class AiPlatformOverview(BaseModel):
    profiles: list[dict]
    action_matrix: list[AiActionMatrixRow]
    rules: list[AiConversationRuleRead]
    tenant_usage: list[AiUsageSummary]
