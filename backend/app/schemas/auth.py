from uuid import UUID

from pydantic import BaseModel, Field

from app.models.models import Role


class LoginRequest(BaseModel):
    tenant_slug: str
    username: str
    password: str


class UnifiedLoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UnifiedLoginResponse(TokenResponse):
    scope: str
    tenant_slug: str | None = None


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


class ForgotPasswordRequest(BaseModel):
    email: str | None = None
    phone: str | None = None
    tenant_slug: str | None = None


class ForgotPasswordResponse(BaseModel):
    ok: bool
    message: str
    channels: list[str] = []


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=4, max_length=128)


class ResetPasswordResponse(BaseModel):
    ok: bool
    message: str
