"""Jerarquía: Empresa → Centro de trabajo → Departamento."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class WorkCenter(SQLModel, table=True):
    __tablename__ = "work_centers"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_work_center_code_company"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    company_id: UUID = Field(foreign_key="companies.id", index=True)
    name: str = Field(max_length=200)
    code: str = Field(max_length=50, index=True)
    address: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    departments: list["Department"] = Relationship(back_populates="work_center")


class Department(SQLModel, table=True):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("work_center_id", "code", name="uq_department_code_wc"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    work_center_id: UUID = Field(foreign_key="work_centers.id", index=True)
    name: str = Field(max_length=200)
    code: str = Field(max_length=50, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    work_center: WorkCenter | None = Relationship(back_populates="departments")


class GroupTemplate(SQLModel, table=True):
    """Plantillas de grupos que se clonan al crear cada tenant (monetización / onboarding)."""

    __tablename__ = "group_templates"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=120, unique=True)
    description: str | None = Field(default=None, max_length=500)
    permissions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    is_system: bool = Field(default=True)
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
