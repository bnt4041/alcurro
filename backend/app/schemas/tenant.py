from datetime import datetime

from uuid import UUID



import re

from pydantic import BaseModel, Field, field_validator



from app.models.models import Role
from app.models.tenant import GoWAStatus





class TenantBrandingRead(BaseModel):

    slug: str

    name: str

    logo_url: str | None

    primary_color: str

    secondary_color: str

    accent_color: str





class TenantBillingUpdate(BaseModel):

    legal_name: str | None = None

    tax_id: str | None = None

    billing_email: str | None = None

    billing_phone: str | None = None

    billing_address: str | None = None

    billing_city: str | None = None

    billing_postal_code: str | None = None

    billing_province: str | None = None

    billing_country: str | None = None





class TenantCreate(BaseModel):

    slug: str | None = Field(
        default=None,
        max_length=80,
        pattern=r"^[a-z0-9-]+$",
        description="Opcional: se genera desde el nombre si no se indica",
    )

    name: str = Field(min_length=1, max_length=200)

    legal_name: str = Field(min_length=1, max_length=200)

    tax_id: str = Field(min_length=1, max_length=50)

    billing_email: str = Field(min_length=3, max_length=255)

    billing_phone: str = Field(min_length=9, max_length=30)

    billing_address: str | None = None

    billing_city: str | None = None

    billing_postal_code: str | None = None

    billing_province: str | None = None

    billing_country: str = "ES"

    primary_color: str = "#3b82f6"

    secondary_color: str = "#1e2a3a"

    accent_color: str = "#22c55e"

    gowa_basic_auth: str = "admin:admin"

    admin_password: str | None = Field(
        default=None, min_length=6, max_length=128,
        description="Contraseña para el usuario administrador inicial. Si no se indica, se genera una aleatoria."
    )

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, v: object) -> str | None:
        if v is None or str(v).strip() == "":
            return None
        from app.services.slug import normalize_slug_text

        s = normalize_slug_text(str(v))
        return s if len(s) >= 2 else None

    @field_validator("billing_phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: object) -> str:
        s = re.sub(r"[^\d+]", "", str(v or "").strip())
        if len(s) < 9:
            raise ValueError("Teléfono demasiado corto")
        return s


class TenantPlatformUpdate(BaseModel):
    """Actualización de cuenta cliente desde panel de plataforma."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=80, pattern=r"^[a-z0-9-]+$")
    legal_name: str | None = Field(default=None, min_length=1, max_length=200)
    tax_id: str | None = Field(default=None, min_length=1, max_length=50)
    billing_email: str | None = Field(default=None, min_length=3, max_length=255)
    billing_phone: str | None = Field(default=None, min_length=9, max_length=30)
    billing_address: str | None = None
    billing_city: str | None = None
    billing_postal_code: str | None = None
    billing_province: str | None = None
    billing_country: str | None = None
    is_active: bool | None = None

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug_optional(cls, v: object) -> str | None:
        if v is None or str(v).strip() == "":
            return None
        from app.services.slug import normalize_slug_text

        s = normalize_slug_text(str(v))
        return s if len(s) >= 2 else None

    @field_validator("billing_phone", mode="before")
    @classmethod
    def normalize_phone_optional(cls, v: object) -> str | None:
        if v is None or str(v).strip() == "":
            return None
        s = re.sub(r"[^\d+]", "", str(v).strip())
        if len(s) < 9:
            raise ValueError("Teléfono demasiado corto")
        return s


class TenantUpdate(BaseModel):

    name: str | None = None

    logo_url: str | None = None

    primary_color: str | None = None

    secondary_color: str | None = None

    accent_color: str | None = None

    gowa_basic_auth: str | None = None

    ollama_base_url: str | None = None

    ollama_model: str | None = None

    is_active: bool | None = None





class TenantRead(BaseModel):

    id: UUID

    slug: str

    name: str

    is_active: bool

    legal_name: str | None

    tax_id: str | None

    billing_email: str | None

    billing_phone: str | None

    billing_address: str | None

    billing_city: str | None

    billing_postal_code: str | None

    billing_province: str | None

    billing_country: str

    logo_url: str | None

    primary_color: str

    secondary_color: str

    accent_color: str

    gowa_port: int | None

    gowa_ui_url: str

    gowa_send_url: str

    gowa_status: GoWAStatus

    gowa_error: str | None

    created_at: datetime

    admin_employee_code: str | None = None
    admin_password: str | None = None

    model_config = {"from_attributes": True}


class TenantWhatsAppStatusRead(BaseModel):
    """Estado del WhatsApp compartido (vista cliente, sin QR ni credenciales)."""

    connected: bool = False
    configured: bool = False
    message: str | None = None


class WhatsAppSessionRead(BaseModel):
    """Estado de vinculación WhatsApp (QR servido por el backend, sin Basic Auth en el navegador)."""

    gowa_status: GoWAStatus
    gowa_error: str | None = None
    gowa_port: int | None = None
    connected: bool = False
    qr_image: str | None = None
    qr_expires_in: int | None = None
    message: str | None = None


class TenantUserRead(BaseModel):
    """Usuario (empleado) de una cuenta cliente — vista plataforma."""

    id: UUID
    company_id: UUID
    company_name: str
    full_name: str
    employee_code: str
    phone: str
    email: str | None
    role: Role
    is_active: bool


class TenantUserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=6, max_length=20)
    email: str | None = None
    id_document: str = Field(min_length=1, max_length=20)
    role: Role = Role.TENANT_ADMIN
    password: str = Field(min_length=6, max_length=128)


class TenantUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=6, max_length=20)
    email: str | None = None
    id_document: str | None = Field(default=None, min_length=1, max_length=20)
    role: Role | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    is_active: bool | None = None


class CompanyCreate(BaseModel):

    name: str

    tax_id: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    is_active: bool | None = None





class CompanyRead(BaseModel):

    id: UUID

    tenant_id: UUID

    name: str

    tax_id: str | None

    is_active: bool

    created_at: datetime



    model_config = {"from_attributes": True}


