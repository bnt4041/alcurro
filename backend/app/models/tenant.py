"""Multi-tenant: cuenta (tenant) con varias empresas y white-label."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class GoWAStatus(StrEnum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class Tenant(SQLModel, table=True):
    """
    Cuenta cliente. Cada tenant tiene su propio contenedor goWA (WhatsApp)
    y zona white-label (logo, colores).
    """

    __tablename__ = "tenants"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    slug: str = Field(index=True, unique=True, max_length=80)
    name: str = Field(max_length=200)
    is_active: bool = Field(default=True)

    # Datos mínimos de facturación (cuenta cliente)
    legal_name: str | None = Field(default=None, max_length=200)
    tax_id: str | None = Field(default=None, max_length=50, description="CIF/NIF")
    billing_email: str | None = Field(default=None, max_length=255)
    billing_phone: str | None = Field(default=None, max_length=30)
    billing_address: str | None = Field(default=None, max_length=300)
    billing_city: str | None = Field(default=None, max_length=100)
    billing_postal_code: str | None = Field(default=None, max_length=20)
    billing_province: str | None = Field(default=None, max_length=100)
    billing_country: str = Field(default="ES", max_length=2)

    logo_url: str | None = Field(default=None, max_length=500)
    primary_color: str = Field(default="#3b82f6", max_length=20)
    secondary_color: str = Field(default="#1e2a3a", max_length=20)
    accent_color: str = Field(default="#22c55e", max_length=20)

    gowa_container_name: str | None = Field(default=None, max_length=100)
    gowa_host: str = Field(default="", max_length=200)
    gowa_port: int | None = Field(default=None)
    gowa_send_url: str = Field(default="")
    gowa_ui_url: str = Field(default="")
    gowa_basic_auth: str = Field(default="admin:admin", max_length=100)
    gowa_webhook_path: str = Field(default="", max_length=200)
    gowa_device_id: str | None = Field(default=None, max_length=80)
    gowa_status: GoWAStatus = Field(default=GoWAStatus.PENDING)
    gowa_error: str | None = Field(default=None, max_length=500)

    ollama_base_url: str = Field(default="http://ollama:11434")
    ollama_model: str = Field(default="llama3.2")

    stripe_customer_id: str | None = Field(default=None, max_length=120, index=True)
    ls_customer_id: str | None = Field(default=None, max_length=80, index=True)
    ls_customer_portal_url: str | None = Field(default=None)

    # Empresa principal de facturación (los datos de esta empresa se usan en facturas)
    billing_company_id: UUID | None = Field(default=None, foreign_key="companies.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    companies: list["Company"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"foreign_keys": "Company.tenant_id"},
    )


class Company(SQLModel, table=True):
    __tablename__ = "companies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    name: str = Field(max_length=200)
    tax_id: str | None = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)

    # Datos de facturación (tomados del tenant si no se especifican; el tenant
    # factura a través de una empresa principal → Tenant.billing_company_id)
    legal_name: str | None = Field(default=None, max_length=200)
    billing_email: str | None = Field(default=None, max_length=255)
    billing_phone: str | None = Field(default=None, max_length=30)
    billing_address: str | None = Field(default=None, max_length=300)
    billing_city: str | None = Field(default=None, max_length=100)
    billing_postal_code: str | None = Field(default=None, max_length=20)
    billing_province: str | None = Field(default=None, max_length=100)
    billing_country: str = Field(default="ES", max_length=2)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    tenant: Tenant | None = Relationship(
        back_populates="companies",
        sa_relationship_kwargs={"foreign_keys": "Company.tenant_id"},
    )
