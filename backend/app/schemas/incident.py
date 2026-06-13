from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.models import BreakType


class IncidentAutoRuleRead(BaseModel):
    model_config = {"from_attributes": True}

    tenant_id: UUID
    late_entrada_enabled: bool
    late_entrada_grace_minutes: int
    late_entrada_notify_whatsapp: bool
    late_entrada_require_justification: bool
    missing_clock_in_enabled: bool
    missing_clock_in_hours: float
    missing_clock_in_notify_whatsapp: bool
    missing_clock_in_require_justification: bool
    missing_clock_out_enabled: bool
    missing_clock_out_hours: float
    missing_clock_out_notify_whatsapp: bool
    missing_clock_out_require_justification: bool
    updated_at: datetime


class IncidentAutoRuleUpdate(BaseModel):
    late_entrada_enabled: bool | None = None
    late_entrada_grace_minutes: int | None = Field(default=None, ge=0, le=240)
    late_entrada_notify_whatsapp: bool | None = None
    late_entrada_require_justification: bool | None = None
    missing_clock_in_enabled: bool | None = None
    missing_clock_in_hours: float | None = Field(default=None, ge=0.5, le=24.0)
    missing_clock_in_notify_whatsapp: bool | None = None
    missing_clock_in_require_justification: bool | None = None
    missing_clock_out_enabled: bool | None = None
    missing_clock_out_hours: float | None = Field(default=None, ge=1.0, le=48.0)
    missing_clock_out_notify_whatsapp: bool | None = None
    missing_clock_out_require_justification: bool | None = None


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
    incident_date: date | None = None
    clock_in_id: UUID | None
    leave_request_id: UUID | None
    break_id: UUID | None = None
    minutes_late: int | None
    original_data: dict
    modified_data: dict | None
    employee_justification: str | None
    internal_notes: str | None
    public_token: str | None
    managed: bool = False
    whatsapp_notified_at: datetime | None
    justified_at: datetime | None
    resolved_at: datetime | None
    resolved_by_id: UUID | None
    created_by_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    justify_url: str | None = None


class IncidentCreate(BaseModel):
    employee_id: UUID | None = None
    employee_ref: str | None = None  # alternative: employee_code, phone or email
    category: str = Field(pattern="^(fichaje|vacaciones|permiso)$")
    incident_type: str = "manual"
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    incident_date: date | None = None
    clock_in_id: UUID | None = None
    leave_request_id: UUID | None = None
    break_id: UUID | None = None
    require_justification: bool = False
    notify_whatsapp: bool = False


class IncidentUpdate(BaseModel):
    status: str | None = None
    internal_notes: str | None = None
    title: str | None = None
    description: str | None = None
    incident_date: date | None = None
    managed: bool | None = None


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


# ── Notas ──────────────────────────────────────────────────────────────────────

class IncidentNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class IncidentNoteRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    incident_id: UUID
    author_id: UUID | None = None
    author_name: str | None = None
    content: str
    created_at: datetime


# ── Envío de mensajes desde incidencia ─────────────────────────────────────────

class IncidentSendMessage(BaseModel):
    channel: str = Field(pattern="^(whatsapp|email)$")
    message: str = Field(min_length=1, max_length=2000)
    recipient_email: str | None = Field(default=None, max_length=255)


# ── Acciones sobre incidencias ─────────────────────────────────────────────────

class IncidentActionClock(BaseModel):
    """Crear o modificar un fichaje desde una incidencia."""
    action: str = Field(pattern="^(create|modify)$")
    clock_in_id: UUID | None = None  # ID explícito del fichaje a modificar
    entrada_at: datetime
    salida_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)
    project_id: UUID | None = None


class IncidentActionBreak(BaseModel):
    """Crear o modificar una parada desde una incidencia."""
    action: str = Field(pattern="^(create|modify)$")
    break_id: UUID | None = None     # ID explícito de la parada a modificar
    clock_in_id: UUID | None = None  # fichaje al que vincular (create) o fallback
    record_type: BreakType = BreakType.INICIO
    recorded_at: datetime
    notes: str | None = Field(default=None, max_length=500)


class IncidentActionLeave(BaseModel):
    """Crear o modificar un permiso desde una incidencia."""
    action: str = Field(pattern="^(create|modify)$")
    leave_id: UUID | None = None     # ID explícito del permiso a modificar
    start_date: date
    end_date: date
    days_requested: float = Field(ge=0.5)
    reason: str | None = Field(default=None, max_length=1000)
    leave_type_id: UUID | None = None
