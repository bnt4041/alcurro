from fastapi import APIRouter, Depends, HTTPException

from sqlmodel import Session, select



from app.core.deps import get_current_user

from app.core.permissions import get_employee_permissions, normalize_role
from app.core.security import can_access_panel, create_access_token, verify_password

from app.database import get_session

from app.models.models import Employee

from app.models.rbac import EmployeeGroup

from app.models.organization import Department, WorkCenter
from app.models.tenant import Company, Tenant
from app.core.org_context import resolve_department_chain

from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UnifiedLoginRequest,
    UnifiedLoginResponse,
    UserMe,
)
from app.services.unified_login import unified_login



router = APIRouter(prefix="/auth", tags=["auth"])





def _find_employee(

    session: Session, tenant: Tenant, username: str

) -> Employee | None:

    companies = session.exec(

        select(Company).where(Company.tenant_id == tenant.id)

    ).all()

    company_ids = [c.id for c in companies]

    for emp in session.exec(

        select(Employee).where(Employee.company_id.in_(company_ids))  # type: ignore[attr-defined]

    ).all():

        if emp.employee_code.lower() == username:

            return emp

        if emp.email and emp.email.lower() == username:

            return emp

    return None


@router.post("/login-unified", response_model=UnifiedLoginResponse)
def login_unified(
    data: UnifiedLoginRequest, session: Session = Depends(get_session)
) -> UnifiedLoginResponse:
    result = unified_login(session, data.login, data.password)
    return UnifiedLoginResponse(
        access_token=result.access_token,
        scope=result.scope,
        tenant_slug=result.tenant_slug,
    )


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    slug = data.tenant_slug.strip().lower()

    tenant = session.exec(select(Tenant).where(Tenant.slug == slug)).first()

    if not tenant or not tenant.is_active:

        raise HTTPException(status_code=401, detail="Cuenta no válida")



    username = data.username.strip().lower()

    row = _find_employee(session, tenant, username)

    from app.services.unified_login import _role_key

    if not row or not verify_password(data.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not can_access_panel(session, row, tenant.id):

        raise HTTPException(

            status_code=403,

            detail="Sin permisos de panel. Asigna un grupo al usuario.",

        )



    return TokenResponse(

        access_token=create_access_token(

            row.id, _role_key(row.role), tenant.id, row.company_id

        )

    )





@router.get("/me", response_model=UserMe)

def me(

    user: Employee = Depends(get_current_user),

    session: Session = Depends(get_session),

) -> UserMe:

    company = session.get(Company, user.company_id)

    tenant = session.get(Tenant, company.tenant_id) if company else None

    tenant_id = tenant.id if tenant else user.company_id

    perms = sorted(get_employee_permissions(session, user, tenant_id))

    group_ids = list(

        session.exec(

            select(EmployeeGroup.group_id).where(EmployeeGroup.employee_id == user.id)

        ).all()

    )

    ut = normalize_role(user.role)
    wc_id: UUID | None = None
    wc_name: str | None = None
    dept_id: UUID | None = user.department_id
    dept_name: str | None = None
    if user.department_id:
        try:
            dept, wc, _co = resolve_department_chain(session, user.department_id)
            dept_name = dept.name
            wc_id = wc.id
            wc_name = wc.name
        except ValueError:
            pass

    return UserMe(
        id=user.id,
        full_name=user.full_name,
        employee_code=user.employee_code,
        email=user.email,
        role=user.role,
        user_type=ut,
        permissions=perms,
        group_ids=group_ids,
        tenant_id=tenant_id,
        tenant_slug=tenant.slug if tenant else "",
        tenant_name=tenant.name if tenant else "",
        company_id=user.company_id,
        company_name=company.name if company else "",
        work_center_id=wc_id,
        work_center_name=wc_name,
        department_id=dept_id,
        department_name=dept_name,
    )

