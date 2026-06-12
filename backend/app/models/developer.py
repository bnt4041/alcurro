from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    name: str = Field(max_length=100)
    key_prefix: str = Field(max_length=24)
    key_hash: str = Field(max_length=64)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = Field(default=None)
    created_by_id: UUID | None = Field(default=None, foreign_key="employees.id")


class WebhookEndpoint(SQLModel, table=True):
    __tablename__ = "webhook_endpoints"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    url: str = Field(max_length=500)
    description: str | None = Field(default=None, max_length=200)
    events: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    secret: str = Field(max_length=64)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered_at: datetime | None = Field(default=None)
    failure_count: int = Field(default=0)


class WebhookDelivery(SQLModel, table=True):
    __tablename__ = "webhook_deliveries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    webhook_id: UUID = Field(foreign_key="webhook_endpoints.id", index=True)
    event_type: str = Field(max_length=50)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    status: str = Field(default="pending", max_length=20)
    response_status: int | None = Field(default=None)
    response_body: str | None = Field(default=None, max_length=2000)
    attempts: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    delivered_at: datetime | None = Field(default=None)
