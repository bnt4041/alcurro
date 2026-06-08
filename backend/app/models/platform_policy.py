"""Políticas globales de la plataforma (límites de uso, soporte, fair-use)."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class PlatformPolicy(SQLModel, table=True):
    """Configuración global de políticas para todos los tenants."""

    __tablename__ = "platform_policies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Límite IA
    ai_monthly_limit: int = Field(
        default=500,
        description="Máximo de consultas a la IA (Ollama) por tenant al mes. 0 = sin límite.",
    )
    ai_limit_action: str = Field(
        default="warn",
        max_length=20,
        description="Acción al superar el límite IA: 'warn' (aviso) o 'block' (bloquear).",
    )

    # Fair use WhatsApp
    whatsapp_monthly_limit: int = Field(
        default=2000,
        description="Máximo de mensajes WhatsApp enviados por el bot por tenant al mes. 0 = sin límite.",
    )
    whatsapp_limit_action: str = Field(
        default="warn",
        max_length=20,
        description="Acción al superar el límite WhatsApp: 'warn' o 'block'.",
    )

    # Soporte
    support_channel: str = Field(
        default="tickets",
        max_length=50,
        description="Canal oficial de soporte: 'tickets', 'email', 'phone'.",
    )
    support_email: str | None = Field(
        default="soporte@alcurro.es",
        max_length=200,
        description="Email de soporte visible para los tenants.",
    )
    support_notice: str | None = Field(
        default=(
            "El soporte técnico se gestiona exclusivamente mediante tickets. "
            "No se atienden consultas técnicas por teléfono ni WhatsApp. "
            "El equipo responde en un máximo de 2 días hábiles."
        ),
        max_length=1000,
        description="Texto informativo del canal de soporte, visible en la cuenta del cliente.",
    )

    # ToS / abuso
    tos_notice: str | None = Field(
        default=None,
        max_length=2000,
        description="Texto adicional de condiciones de uso / fair-use visible para los tenants.",
    )

    updated_at: datetime = Field(default_factory=datetime.utcnow)
