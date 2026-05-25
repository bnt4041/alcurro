from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IncidentAutoRuleRead(BaseModel):
    tenant_id: UUID
    late_entrada_enabled: bool
    late_entrada_grace_minutes: int
    late_entrada_notify_whatsapp: bool
    late_entrada_require_justification: bool
    updated_at: datetime


class IncidentAutoRuleUpdate(BaseModel):
    late_entrada_enabled: bool | None = None
    late_entrada_grace_minutes: int | None = Field(default=None, ge=0, le=240)
    late_entrada_notify_whatsapp: bool | None = None
    late_entrada_require_justification: bool | None = None


class IncidentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    employee_name: str | None = None
    category: str
    incident_type: str
    status: str
    source: str
    title: str
    description: str | None
    clock_in_id: UUID | None
    leave_request_id: UUID | None
    minutes_late: int | None
    original_data: dict
    modified_data: dict | None
    employee_justification: str | None
    internal_notes: str | None
    public_token: str | None
    whatsapp_notified_at: datetime | None
    justified_at: datetime | None
    resolved_at: datetime | None
    resolved_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
    justify_url: str | None = None


class IncidentCreate(BaseModel):
    employee_id: UUID
    category: str = Field(pattern="^(fichaje|vacaciones|permiso)$")
    incident_type: str = "manual"
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    clock_in_id: UUID | None = None
    leave_request_id: UUID | None = None
    require_justification: bool = False
    notify_whatsapp: bool = False


class IncidentUpdate(BaseModel):
    status: str | None = None
    internal_notes: str | None = None
    title: str | None = None
    description: str | None = None


class IncidentApplyClock(BaseModel):
    recorded_at: datetime
    record_type: str | None = None
    notes: str | None = None
    project_id: UUID | None = None


class IncidentApplyLeave(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    days_requested: float | None = None
    reason: str | None = None
    status: str | None = None


class PublicIncidentMeta(BaseModel):
    title: str
    description: str | None
    category: str
    status: str
    employee_name: str
    tenant_name: str
    original_data: dict
    modified_data: dict | None
    can_justify: bool


class PublicIncidentJustify(BaseModel):
    justification: str = Field(min_length=3, max_length=3000)
