from datetime import date, datetime, time
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.models import (
    LeaveStatus,
    Role,
    ShiftPatternType,
    BreakType,
)


class EmployeeCreate(BaseModel):
    phone: str
    email: str | None = None
    full_name: str
    id_document: str
    employee_code: str | None = None
    department_id: UUID | None = None
    role: Role = Role.EMPLOYEE
    supervisor_id: UUID | None = None
    job_title: str | None = None
    vacation_days_balance: float = 22.0
    is_active: bool = True
    password: str | None = None
    shift_configuration_id: UUID | None = None
    work_start_time: time | None = None
    work_end_time: time | None = None
    work_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    work_schedule_blocks: list[dict[str, Any]] | None = None
    work_schedule_periods: list[dict[str, Any]] | None = None
    rotating_shift: bool = False
    weekly_hours: float | None = Field(default=None, ge=0, le=168)


class EmployeeBulkScheduleUpdate(BaseModel):
    employee_ids: list[UUID] = Field(min_length=1, max_length=500)
    rotating_shift: bool
    shift_configuration_id: UUID | None = None
    weekly_hours: float | None = Field(default=None, ge=0, le=168)
    work_schedule_periods: list[dict[str, Any]] | None = None


class EmployeeBulkScheduleItemError(BaseModel):
    employee_id: UUID
    employee_name: str | None = None
    message: str


class EmployeeBulkImportRow(BaseModel):
    full_name: str | None = None
    id_document: str | None = None
    phone: str | None = None
    email: str | None = None
    role: str | None = None
    employee_code: str | None = None
    vacation_days_balance: str | None = None
    is_active: str | None = None


class EmployeeBulkImportRequest(BaseModel):
    rows: list[EmployeeBulkImportRow] = Field(min_length=1, max_length=500)


class EmployeeBulkImportResponse(BaseModel):
    created: int
    errors: list[str] = Field(default_factory=list)


class EmployeeBulkScheduleResult(BaseModel):
    updated: int
    skipped: int
    errors: list[EmployeeBulkScheduleItemError] = Field(default_factory=list)


class EmployeeUpdate(BaseModel):
    phone: str | None = None
    email: str | None = None
    full_name: str | None = None
    id_document: str | None = None
    department_id: UUID | None = None
    role: Role | None = None
    supervisor_id: UUID | None = None
    job_title: str | None = None
    vacation_days_balance: float | None = None
    is_active: bool | None = None
    password: str | None = None
    shift_configuration_id: UUID | None = None
    work_start_time: time | None = None
    work_end_time: time | None = None
    work_days: list[int] | None = None
    work_schedule_blocks: list[dict[str, Any]] | None = None
    work_schedule_periods: list[dict[str, Any]] | None = None
    rotating_shift: bool | None = None
    weekly_hours: float | None = Field(default=None, ge=0, le=168)


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    department_id: UUID | None = None
    phone: str
    email: str | None = None
    full_name: str
    id_document: str | None = None
    employee_code: str
    role: Role
    supervisor_id: UUID | None = None
    job_title: str | None = None
    vacation_days_balance: float
    is_active: bool
    avatar_delivery_id: UUID | None = None
    avatar_url: str | None = None
    shift_configuration_id: UUID | None = None

    @model_validator(mode="after")
    def set_avatar_url(self) -> "EmployeeRead":
        if self.avatar_delivery_id and not self.avatar_url:
            self.avatar_url = f"/api/employees/{self.id}/avatar"
        return self
    work_start_time: time | None = None
    work_end_time: time | None = None
    work_days: list[int] = Field(default_factory=list)
    work_schedule_blocks: list[dict[str, Any]] = Field(default_factory=list)
    work_schedule_periods: list[dict[str, Any]] = Field(default_factory=list)
    rotating_shift: bool = False
    weekly_hours: float | None = None
    created_at: datetime
    updated_at: datetime


class ClockInCreate(BaseModel):
    employee_id: UUID | None = None
    employee_ref: str | None = None  # alternative: employee_code, phone or email
    entrada_at: datetime
    salida_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    latitude_out: float | None = None
    longitude_out: float | None = None
    address_out: str | None = None
    source: str = "panel"
    notes: str | None = None
    work_summary: str | None = None
    project_id: UUID | None = None


class ClockInRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    employee_id: UUID
    entrada_at: datetime
    salida_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    latitude_out: float | None = None
    longitude_out: float | None = None
    address_out: str | None = None
    source: str
    notes: str | None = None
    work_summary: str | None = None
    project_id: UUID | None = None
    whatsapp_message_id: str | None = None
    project_name: str | None = None


class BreakCreate(BaseModel):
    employee_id: UUID
    record_type: BreakType
    notes: str | None = None


class BreakRead(BreakCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    recorded_at: datetime
    source: str
    whatsapp_message_id: str | None = None


class BreakSummaryRow(BaseModel):
    employee_id: UUID
    employee_name: str
    employee_code: str
    company_id: UUID
    total_minutes: int
    total_hours: float
    break_starts: int
    break_ends: int
    open_breaks: int


class BreakCompanySummary(BaseModel):
    company_id: UUID
    company_name: str
    total_minutes: int
    total_hours: float
    employee_count: int


class BreakSummaryResponse(BaseModel):
    rows: list[BreakSummaryRow]
    by_company: list[BreakCompanySummary]
    period_from: date | None = None
    period_to: date | None = None


class LeaveTypeCreate(BaseModel):
    name: str
    deducts_balance: bool = True
    has_own_balance: bool = False
    default_days: float | None = None


class LeaveTypeUpdate(BaseModel):
    name: str | None = None
    deducts_balance: bool | None = None
    has_own_balance: bool | None = None
    default_days: float | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class LeaveTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    deducts_balance: bool
    has_own_balance: bool
    default_days: float | None
    is_default: bool
    is_active: bool
    sort_order: int


class EmployeeLeaveBalanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    employee_id: UUID
    leave_type_id: UUID
    leave_type_name: str | None = None
    total_days: float
    used_days: float = 0.0
    remaining_days: float = 0.0
    notes: str | None


class EmployeeLeaveBalanceUpdate(BaseModel):
    total_days: float = Field(ge=0)
    notes: str | None = None


class LeaveRequestCreate(BaseModel):
    employee_id: UUID | None = None
    employee_ref: str | None = None  # alternative: employee_code, phone or email
    start_date: date
    end_date: date
    days_requested: float = Field(ge=0.5)
    status: LeaveStatus = LeaveStatus.PENDING
    leave_type_id: UUID | None = None
    leave_type_name: str | None = None  # alternative to leave_type_id
    reason: str | None = None
    supervisor_id: UUID | None = None


class LeaveRequestUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    days_requested: float | None = None
    status: LeaveStatus | None = None
    leave_type_id: UUID | None = None
    reason: str | None = None
    supervisor_id: UUID | None = None
    review_notes: str | None = None


class LeaveRequestRead(LeaveRequestCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    created_at: datetime
    raw_message: str | None = None
    leave_type_name: str | None = None


class ShiftConfigurationCreate(BaseModel):
    name: str
    pattern_type: ShiftPatternType
    description: str | None = None
    weekly_hours: float | None = None
    pattern_definition: dict[str, Any] = Field(default_factory=dict)
    default_start_time: time | None = None
    default_end_time: time | None = None
    is_active: bool = True


class ShiftConfigurationUpdate(BaseModel):
    name: str | None = None
    pattern_type: ShiftPatternType | None = None
    description: str | None = None
    weekly_hours: float | None = None
    pattern_definition: dict[str, Any] | None = None
    default_start_time: time | None = None
    default_end_time: time | None = None
    is_active: bool | None = None


class ShiftConfigurationRead(ShiftConfigurationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime


class ShiftAssignmentCreate(BaseModel):
    employee_id: UUID
    shift_configuration_id: UUID
    valid_from: date
    valid_to: date | None = None
    calendar_overrides: dict[str, Any] = Field(default_factory=dict)


class ShiftAssignmentUpdate(BaseModel):
    employee_id: UUID | None = None
    shift_configuration_id: UUID | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    calendar_overrides: dict[str, Any] | None = None


class ShiftAssignmentRead(ShiftAssignmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime


class DocumentDeliveryCreate(BaseModel):
    employee_id: UUID | None = None
    company_id: UUID | None = None
    file_name: str
    document_type: str
    requires_acknowledgment: bool = True


class DocumentDeliveryUpdate(BaseModel):
    document_type: str | None = None
    requires_acknowledgment: bool | None = None
    sent_at: datetime | None = None


class DocumentDeliveryRead(DocumentDeliveryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    file_path: str
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledgment_text: str | None = None
    created_at: datetime


class SystemSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    gowa_send_url: str
    gowa_basic_auth: str
    gowa_webhook_url: str
    gowa_ui_url: str
    ollama_base_url: str
    ollama_model: str
    company_name: str
    updated_at: datetime


class SystemSettingsUpdate(BaseModel):
    gowa_send_url: str | None = None
    gowa_basic_auth: str | None = None
    gowa_webhook_url: str | None = None
    gowa_ui_url: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    company_name: str | None = None


class ConnectionTestResult(BaseModel):
    ok: bool
    message: str
    detail: str | None = None
