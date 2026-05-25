"""Configuración global de IA, reglas conversacionales y uso por cuenta."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, UniqueConstraint


class AiAction(SQLModel, table=True):
    """Catálogo de acciones que la IA puede ejecutar."""

    __tablename__ = "ai_actions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=120)
    description: str | None = Field(default=None, max_length=500)
    category: str = Field(default="general", max_length=50, index=True)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AiProfileAction(SQLModel, table=True):
    """Qué perfiles (roles) pueden usar cada acción."""

    __tablename__ = "ai_profile_actions"
    __table_args__ = (
        UniqueConstraint("action_id", "profile_key", name="uq_ai_profile_action"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    action_id: UUID = Field(foreign_key="ai_actions.id", index=True)
    profile_key: str = Field(max_length=50, index=True)
    enabled: bool = Field(default=True)


class AiConversationRule(SQLModel, table=True):
    """Reglas conversacionales ordenadas por prioridad (menor = más preferente)."""

    __tablename__ = "ai_conversation_rules"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=120)
    content: str = Field(max_length=4000)
    priority: int = Field(default=100, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AiUsageRecord(SQLModel, table=True):
    """Registro de consumo de IA por cuenta."""

    __tablename__ = "ai_usage_records"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    profile_key: str | None = Field(default=None, max_length=50, index=True)
    action_code: str | None = Field(default=None, max_length=50, index=True)
    source: str = Field(default="whatsapp", max_length=40)
    model: str = Field(default="", max_length=80)
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    duration_ms: int = Field(default=0)
    success: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
