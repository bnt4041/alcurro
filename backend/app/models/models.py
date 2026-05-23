"""Modelos de dominio HRM — fichajes inalterables, vacaciones, turnos y RBAC."""

from datetime import date, datetime, time
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class Role(StrEnum):
    """Tipo de usuario: categoría para acceso al panel y permisos por defecto."""

    EMPLOYEE = "employee"
    MANAGER = "manager"
    TENANT_ADMIN = "tenant_admin"
    LABOR_INSPECTOR = "labor_inspector"
    # Alias legacy (migración)
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class ClockInType(StrEnum):
    ENTRADA = "entrada"
    SALIDA = "salida"


class LeaveStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ShiftPatternType(StrEnum):
    """Tipos de configuración de turno según normativa laboral española."""

    RIGID = "rigid"
    ROTATING = "rotating"
    SPLIT = "split"
    NIGHT = "night"
    MIXED = "mixed"


class Employee(SQLModel, table=True):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("company_id", "employee_code", name="uq_employee_code_company"),
        UniqueConstraint("company_id", "phone", name="uq_employee_phone_company"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    company_id: UUID = Field(foreign_key="companies.id", index=True)
    department_id: UUID | None = Field(
        default=None, foreign_key="departments.id", index=True
    )
    phone: str = Field(index=True, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    full_name: str = Field(max_length=200)
    employee_code: str = Field(index=True, max_length=50)
    role: Role = Field(default=Role.EMPLOYEE)
    supervisor_id: UUID | None = Field(default=None, foreign_key="employees.id")
    vacation_days_balance: float = Field(default=22.0, ge=0)
    is_active: bool = Field(default=True)
    password_hash: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    clock_ins: list["ClockIn"] = Relationship(back_populates="employee")
    leave_requests: list["LeaveRequest"] = Relationship(
        back_populates="employee",
        sa_relationship_kwargs={"foreign_keys": "LeaveRequest.employee_id"},
    )
    shift_assignments: list["ShiftAssignment"] = Relationship(
        back_populates="employee"
    )


class ClockIn(SQLModel, table=True):
    """
    Registro de jornada inalterable (normativa española).
    Sin borrado físico — DELETE prohibido a nivel de API.
    """

    __tablename__ = "clock_ins"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    record_type: ClockInType
    recorded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Hora del servidor en el momento del fichaje",
    )
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    source: str = Field(default="whatsapp", max_length=50)
    notes: str | None = Field(default=None, max_length=500)
    whatsapp_message_id: str | None = Field(default=None, max_length=100)

    employee: Employee | None = Relationship(back_populates="clock_ins")


class LeaveRequest(SQLModel, table=True):
    __tablename__ = "leave_requests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    start_date: date
    end_date: date
    days_requested: float = Field(ge=0.5)
    status: LeaveStatus = Field(default=LeaveStatus.PENDING)
    reason: str | None = Field(default=None, max_length=1000)
    supervisor_id: UUID | None = Field(default=None, foreign_key="employees.id")
    reviewed_at: datetime | None = Field(default=None)
    review_notes: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_message: str | None = Field(default=None)

    employee: Employee | None = Relationship(
        back_populates="leave_requests",
        sa_relationship_kwargs={"foreign_keys": "LeaveRequest.employee_id"},
    )


class ShiftConfiguration(SQLModel, table=True):
    """
    Configuración de turnos complejos: rígidos, rotativos, partidos, nocturnidad.
    `pattern_definition` almacena la lógica en JSON (ciclos, franjas, excepciones).
    """

    __tablename__ = "shift_configurations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    company_id: UUID = Field(foreign_key="companies.id", index=True)
    name: str = Field(max_length=100)
    pattern_type: ShiftPatternType
    description: str | None = Field(default=None, max_length=500)
    weekly_hours: float | None = Field(default=None)
    pattern_definition: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
        description=(
            "Ej: rigid -> {slots: [{day:0,start:'08:00',end:'17:00'}]}; "
            "rotating -> {cycle_days:14, blocks:[...]}; "
            "split -> {slots:[{start:'09:00',end:'14:00'},{start:'16:00',end:'19:00'}]}; "
            "night -> {start:'22:00',end:'06:00', crosses_midnight: true}"
        ),
    )
    default_start_time: time | None = Field(default=None)
    default_end_time: time | None = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    assignments: list["ShiftAssignment"] = Relationship(
        back_populates="shift_configuration"
    )


class ShiftAssignment(SQLModel, table=True):
    """Asignación de calendario de turnos mensual/anual a un empleado."""

    __tablename__ = "shift_assignments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    shift_configuration_id: UUID = Field(
        foreign_key="shift_configurations.id", index=True
    )
    valid_from: date
    valid_to: date | None = Field(default=None)
    calendar_overrides: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
        description="Excepciones por fecha ISO: {'2025-06-01': 'festivo', ...}",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    employee: Employee | None = Relationship(back_populates="shift_assignments")
    shift_configuration: ShiftConfiguration | None = Relationship(
        back_populates="assignments"
    )


class DocumentDelivery(SQLModel, table=True):
    """Distribución formal de documentación vía WhatsApp con acuse de recibo."""

    __tablename__ = "document_deliveries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    file_path: str = Field(max_length=500)
    file_name: str = Field(max_length=255)
    document_type: str = Field(max_length=50)
    sent_at: datetime | None = Field(default=None)
    acknowledged_at: datetime | None = Field(default=None)
    acknowledgment_text: str | None = Field(default=None, max_length=100)
    requires_acknowledgment: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
