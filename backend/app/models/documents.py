"""Tipología, etiquetas y entregas documentales."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, UniqueConstraint


class DocumentType(SQLModel, table=True):
    __tablename__ = "document_types"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_document_type_tenant_code"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    code: str = Field(max_length=50, index=True)
    name: str = Field(max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentTag(SQLModel, table=True):
    __tablename__ = "document_tags"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_document_tag_tenant_name"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    name: str = Field(max_length=80, index=True)
    color: str | None = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentDeliveryTag(SQLModel, table=True):
    __tablename__ = "document_delivery_tags"
    __table_args__ = (
        UniqueConstraint(
            "document_delivery_id", "tag_id", name="uq_document_delivery_tag"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_delivery_id: UUID = Field(
        foreign_key="document_deliveries.id", index=True
    )
    tag_id: UUID = Field(foreign_key="document_tags.id", index=True)


class DocumentDelivery(SQLModel, table=True):
    """Documento asociado a empresa o empleado."""

    __tablename__ = "document_deliveries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    company_id: UUID | None = Field(default=None, foreign_key="companies.id", index=True)
    employee_id: UUID | None = Field(default=None, foreign_key="employees.id", index=True)
    document_type_id: UUID | None = Field(
        default=None, foreign_key="document_types.id", index=True
    )
    file_path: str = Field(max_length=500)
    file_name: str = Field(max_length=255)
    document_type: str = Field(max_length=50, description="Código legacy / denormalizado")
    title: str | None = Field(default=None, max_length=255)
    expires_at: date | None = Field(default=None, index=True)
    sent_at: datetime | None = Field(default=None)
    acknowledged_at: datetime | None = Field(default=None)
    acknowledgment_text: str | None = Field(default=None, max_length=100)
    requires_acknowledgment: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentNotificationSettings(SQLModel, table=True):
    """Avisos configurables antes de la caducidad de documentos."""

    __tablename__ = "document_notification_settings"

    tenant_id: UUID = Field(foreign_key="tenants.id", primary_key=True)
    enabled: bool = Field(default=False)
    days_before: str = Field(
        default="30,7,1",
        max_length=100,
        description="Días antes de caducar separados por coma (ej. 30,7,1,0)",
    )
    channel_whatsapp: bool = Field(default=True)
    channel_email: bool = Field(default=True)
    notify_employee: bool = Field(default=True)
    notify_managers: bool = Field(
        default=True,
        description="Responsables con permiso documents.read en la empresa",
    )
    extra_emails: str | None = Field(
        default=None,
        max_length=500,
        description="Emails adicionales separados por coma",
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentExpiryNotificationLog(SQLModel, table=True):
    """Registro de avisos enviados (evita duplicados)."""

    __tablename__ = "document_expiry_notification_logs"
    __table_args__ = (
        UniqueConstraint(
            "document_delivery_id",
            "days_before",
            "channel",
            "recipient",
            name="uq_doc_expiry_notif",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    document_delivery_id: UUID = Field(foreign_key="document_deliveries.id", index=True)
    days_before: int = Field(description="Umbral de días que disparó el aviso")
    channel: str = Field(max_length=20)
    recipient: str = Field(max_length=255)
    success: bool = Field(default=True)
    detail: str | None = Field(default=None, max_length=500)
    sent_at: datetime = Field(default_factory=datetime.utcnow)
