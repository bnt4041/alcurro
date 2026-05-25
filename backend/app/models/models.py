"""Modelos de dominio HRM — fichajes inalterables, vacaciones, turnos y RBAC."""

from datetime import date, datetime, time
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PgENUM
from sqlalchemy.types import TypeDecorator
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


_PG_ROLE_ENUM = PgENUM(
    "EMPLOYEE",
    "SUPERVISOR",
    "ADMIN",
    "LABOR_INSPECTOR",
    "tenant_admin",
    "manager",
    name="role",
    create_type=False,
)


class RoleType(TypeDecorator):
    """PostgreSQL enum `role`: etiquetas legacy en MAYÚSCULAS + tenant_admin/manager."""

    impl = _PG_ROLE_ENUM
    cache_ok = True

    _TO_DB: dict[str, str] = {
        "employee": "EMPLOYEE",
        "supervisor": "SUPERVISOR",
        "admin": "ADMIN",
        "labor_inspector": "LABOR_INSPECTOR",
        "tenant_admin": "tenant_admin",
        "manager": "manager",
    }
    _FROM_DB: dict[str, Role] = {
        "EMPLOYEE": Role.EMPLOYEE,
        "SUPERVISOR": Role.SUPERVISOR,
        "ADMIN": Role.ADMIN,
        "LABOR_INSPECTOR": Role.LABOR_INSPECTOR,
        "tenant_admin": Role.TENANT_ADMIN,
        "manager": Role.MANAGER,
    }

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        raw = value.value if isinstance(value, Role) else str(value)
        return self._TO_DB.get(raw, raw)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value in self._FROM_DB:
            return self._FROM_DB[value]
        try:
            return Role(value)
        except ValueError:
            return Role.EMPLOYEE


class ClockInType(StrEnum):
    ENTRADA = "entrada"
    SALIDA = "salida"


class BreakType(StrEnum):
    INICIO = "inicio_parada"
    FIN = "fin_parada"


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
        UniqueConstraint(
            "company_id", "id_document", name="uq_employee_id_document_company"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    company_id: UUID = Field(foreign_key="companies.id", index=True)
    department_id: UUID | None = Field(
        default=None, foreign_key="departments.id", index=True
    )
    phone: str = Field(index=True, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    full_name: str = Field(max_length=200)
    id_document: str | None = Field(default=None, max_length=20, index=True)
    employee_code: str = Field(index=True, max_length=50)
    role: Role = Field(
        default=Role.EMPLOYEE,
        sa_column=Column(RoleType, nullable=False),
    )
    supervisor_id: UUID | None = Field(default=None, foreign_key="employees.id")
    vacation_days_balance: float = Field(default=22.0, ge=0)
    is_active: bool = Field(default=True)
    password_hash: str | None = Field(default=None, max_length=255)
    shift_configuration_id: UUID | None = Field(
        default=None, foreign_key="shift_configurations.id", index=True
    )
    work_start_time: time | None = Field(default=None)
    work_end_time: time | None = Field(default=None)
    work_days: list[int] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4],
        sa_column=Column(JSON, nullable=False),
        description="Días laborables 0=lunes … 6=domingo",
    )
    work_schedule_blocks: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
        description="Resumen legacy del periodo activo",
    )
    work_schedule_periods: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
        description=(
            "Periodos: [{valid_from, valid_to, blocks:[{work_days, slots:[...]}]}]"
        ),
    )
    rotating_shift: bool = Field(
        default=False,
        description="Horario vía turno complejo; sin franjas fijas en este formulario",
    )
    weekly_hours: float | None = Field(
        default=None,
        ge=0,
        le=168,
        description="Horas semanales pactadas (turno rotativo/complejo)",
    )
    welcome_sent_at: datetime | None = Field(default=None)
    last_clock_reminder_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    clock_ins: list["ClockIn"] = Relationship(back_populates="employee")
    work_breaks: list["WorkBreak"] = Relationship(back_populates="employee")
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
    project_id: UUID | None = Field(default=None, foreign_key="projects.id", index=True)

    employee: Employee | None = Relationship(back_populates="clock_ins")


class WorkBreak(SQLModel, table=True):
    """Paradas / descansos durante la jornada (inalterables, sin borrado)."""

    __tablename__ = "work_breaks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    record_type: BreakType
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="panel", max_length=50)
    notes: str | None = Field(default=None, max_length=500)
    whatsapp_message_id: str | None = Field(default=None, max_length=100)

    employee: Employee | None = Relationship(back_populates="work_breaks")


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

