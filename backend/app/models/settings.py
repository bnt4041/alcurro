from datetime import datetime

from sqlmodel import Field, SQLModel


class SystemSettings(SQLModel, table=True):
    """Configuración persistida (goWA, Ollama, webhooks). Fila única id=1."""

    __tablename__ = "system_settings"

    id: int = Field(default=1, primary_key=True)
    gowa_send_url: str = Field(default="http://gowa:3000/send/message")
    gowa_basic_auth: str = Field(default="admin:admin")
    gowa_webhook_url: str = Field(default="http://backend:8000/webhook/whatsapp")
    gowa_ui_url: str = Field(default="http://localhost:3000")
    gowa_device_id: str | None = Field(default=None, max_length=80)
    ollama_base_url: str = Field(default="http://ollama:11434")
    ollama_model: str = Field(default="llama3.2")
    company_name: str = Field(default="Mi Empresa")
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int = Field(default=587)
    smtp_user: str | None = Field(default=None, max_length=255)
    smtp_password: str | None = Field(default=None, max_length=255)
    smtp_use_tls: bool = Field(default=True)
    mail_from_address: str | None = Field(default=None, max_length=255)
    mail_from_name: str | None = Field(default="alcurro")
    # Soporte / comercial
    whatsapp_public_number: str | None = Field(
        default=None,
        max_length=40,
        description="Número público de WhatsApp de Alcurro (widget landing + línea comercial)",
    )
    platform_alert_phone: str | None = Field(
        default=None,
        max_length=40,
        description="WhatsApp al que se avisa de nuevos tickets de soporte",
    )
    commercial_ai_enabled: bool = Field(
        default=True,
        description="Responder con IA comercial a números no registrados",
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow)
