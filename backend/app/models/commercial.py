"""Historial de chat comercial por teléfono (leads/prospectos vía WhatsApp)."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class CommercialMessage(SQLModel, table=True):
    """Mensaje de la conversación comercial con un número no registrado.

    No hay tenant ni empleado: el contexto se agrupa por teléfono del lead.
    """

    __tablename__ = "commercial_messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    phone: str = Field(max_length=40, index=True)
    role: str = Field(max_length=20, description="user | assistant")
    content: str = Field(max_length=4000)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
