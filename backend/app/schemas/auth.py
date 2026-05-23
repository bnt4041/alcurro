from uuid import UUID

from pydantic import BaseModel

from app.models.models import Role


class LoginRequest(BaseModel):
    tenant_slug: str
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserMe(BaseModel):
    id: UUID
    full_name: str
    employee_code: str
    email: str | None
    role: Role
    user_type: Role
    scope: str = "tenant"
    permissions: list[str]
    group_ids: list[UUID]
    tenant_id: UUID
    tenant_slug: str
    tenant_name: str
    company_id: UUID
    company_name: str
    work_center_id: UUID | None = None
    work_center_name: str | None = None
    department_id: UUID | None = None
    department_name: str | None = None
