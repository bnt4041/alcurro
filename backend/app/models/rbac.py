"""Grupos de usuarios con permisos personalizables y administradores de plataforma."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


class PlatformUser(SQLModel, table=True):
    """Administrador de la aplicación (gestión global de cuentas)."""

    __tablename__ = "platform_users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    full_name: str = Field(max_length=200)
    password_hash: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserGroup(SQLModel, table=True):
    """Grupo de permisos dentro de una cuenta (tenant)."""

    __tablename__ = "user_groups"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_group_name_tenant"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    name: str = Field(max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_system: bool = Field(
        default=False,
        description="Grupos predefinidos; no se pueden eliminar",
    )
    permissions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EmployeeGroup(SQLModel, table=True):
    __tablename__ = "employee_groups"
    __table_args__ = (
        UniqueConstraint("employee_id", "group_id", name="uq_employee_group"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    group_id: UUID = Field(foreign_key="user_groups.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
