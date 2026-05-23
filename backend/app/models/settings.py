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
    ollama_base_url: str = Field(default="http://ollama:11434")
    ollama_model: str = Field(default="llama3.2")
    company_name: str = Field(default="Mi Empresa")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
