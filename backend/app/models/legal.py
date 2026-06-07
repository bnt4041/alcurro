"""Textos legales y aceptaciones por empleado."""

import secrets
from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, UniqueConstraint


class LegalDocument(SQLModel, table=True):
    """Texto legal que la empresa exige aceptar (por tenant)."""

    __tablename__ = "legal_documents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_legal_doc_tenant_code"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    code: str = Field(max_length=50, index=True)
    title: str = Field(max_length=200)
    body: str = Field(description="Contenido en texto o HTML")
    version: int = Field(default=1, ge=1)
    is_active: bool = Field(default=True)
    is_required: bool = Field(
        default=True,
        description="Si es obligatorio que el empleado lo acepte",
    )
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LegalAcceptance(SQLModel, table=True):
    __tablename__ = "legal_acceptances"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "legal_document_id",
            name="uq_legal_acceptance_employee_doc",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    legal_document_id: UUID = Field(foreign_key="legal_documents.id", index=True)
    document_version: int = Field(ge=1)
    accepted_at: datetime = Field(default_factory=datetime.utcnow)
    channel: str = Field(default="web", max_length=20)  # "web" | "whatsapp"


class LegalToken(SQLModel, table=True):
    """Token de corta duración para que el empleado acepte legales desde WhatsApp."""

    __tablename__ = "legal_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        max_length=64,
        index=True,
        unique=True,
    )
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    tenant_id: UUID = Field(foreign_key="tenants.id")
    expires_at: datetime
    used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
