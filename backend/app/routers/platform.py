from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.core.platform_deps import get_platform_user
from app.core.security import create_platform_token, hash_password, verify_password
from app.database import get_session
from app.models.rbac import PlatformUser
from app.models.tenant import Tenant
from app.schemas.rbac import (
    PlatformLoginRequest,
    PlatformUserAdminRead,
    PlatformUserCreate,
    PlatformUserMe,
    PlatformUserUpdate,
)
from app.schemas.auth import TokenResponse
from app.models.models import Employee
from app.models.tenant import Company
from app.schemas.tenant import (
    TenantCreate,
    TenantPlatformUpdate,
    TenantRead,
    TenantUserCreate,
    TenantUserRead,
)
from app.models.organization import GroupTemplate
from app.models.organization import Department, WorkCenter
from app.services.code_generator import next_employee_code
from app.services.id_document import validate_id_document
from app.services.rbac_service import assign_role_default_group, ensure_system_groups
from app.schemas.billing import InvoiceRead, TenantListItemRead
from app.schemas.organization import GroupTemplateRead, GroupTemplateUpdate
from app.services.billing_read import subscription_to_summary, tenant_account_billing
from app.services.billing_service import get_primary_subscription
from app.services.org_service import (
    clone_groups_for_tenant,
    ensure_group_templates,
    seed_tenant_organization,
)
from app.services.slug import resolve_tenant_slug, resolve_tenant_slug_update
from app.services.tenant_delete import delete_tenant_permanent

router = APIRouter(prefix="/platform", tags=["platform"])


@router.post("/auth/login", response_model=TokenResponse)
def platform_login(
    data: PlatformLoginRequest, session: Session = Depends(get_session)
) -> TokenResponse:
    email = data.email.strip().lower()
    user = session.exec(
        select(PlatformUser).where(PlatformUser.email == email)
    ).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return TokenResponse(access_token=create_platform_token(user.id))


@router.get("/auth/me", response_model=PlatformUserMe)
def platform_me(user: PlatformUser = Depends(get_platform_user)) -> PlatformUserMe:
    return PlatformUserMe(
        id=user.id, email=user.email, full_name=user.full_name, scope="platform"
    )


@router.get("/users", response_model=list[PlatformUserAdminRead])
def list_platform_users(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[PlatformUser]:
    return list(
        session.exec(
            select(PlatformUser).order_by(PlatformUser.full_name)  # type: ignore[attr-defined]
        ).all()
    )


@router.post("/users", response_model=PlatformUserAdminRead, status_code=201)
def create_platform_user(
    data: PlatformUserCreate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> PlatformUser:
    email = data.email.strip().lower()
    if session.exec(
        select(PlatformUser).where(PlatformUser.email == email)
    ).first():
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email")
    row = PlatformUser(
        email=email,
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        is_active=True,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/users/{user_id}", response_model=PlatformUserAdminRead)
def update_platform_user(
    user_id: UUID,
    data: PlatformUserUpdate,
    session: Session = Depends(get_session),
    current: PlatformUser = Depends(get_platform_user),
) -> PlatformUser:
    row = session.get(PlatformUser, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if data.is_active is False and row.id == current.id:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")
    if data.is_active is False:
        active_count = session.exec(
            select(PlatformUser).where(PlatformUser.is_active == True)  # noqa: E712
        ).all()
        if len(active_count) <= 1 and row.is_active:
            raise HTTPException(
                status_code=400, detail="Debe quedar al menos un administrador activo"
            )
    if data.full_name is not None:
        row.full_name = data.full_name.strip()
    if data.password:
        row.password_hash = hash_password(data.password)
    if data.is_active is not None:
        row.is_active = data.is_active
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("/tenants", response_model=list[TenantListItemRead])
def list_tenants(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[TenantListItemRead]:
    tenants = list(session.exec(select(Tenant).order_by(Tenant.name)).all())
    result: list[TenantListItemRead] = []
    for tenant in tenants:
        sub, company = get_primary_subscription(session, tenant.id)
        result.append(
            TenantListItemRead(
                id=tenant.id,
                slug=tenant.slug,
                name=tenant.name,
                legal_name=tenant.legal_name,
                tax_id=tenant.tax_id,
                billing_email=tenant.billing_email,
                billing_phone=tenant.billing_phone,
                is_active=tenant.is_active,
                created_at=tenant.created_at,
                subscription=subscription_to_summary(sub, company),
            )
        )
    session.commit()
    return result


@router.get("/tenants/{tenant_id}/invoices", response_model=list[InvoiceRead])
def list_tenant_invoices_platform(
    tenant_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
    limit: int = 50,
) -> list[InvoiceRead]:
    if not session.get(Tenant, tenant_id):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    data = tenant_account_billing(session, tenant_id)
    session.commit()
    return data["invoices"][: min(limit, 200)]


@router.post("/tenants", response_model=TenantRead, status_code=201)
def create_tenant_platform(
    data: TenantCreate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> Tenant:
    slug = resolve_tenant_slug(session, data.name, data.slug)
    tenant = Tenant(
        slug=slug,
        name=data.name,
        legal_name=data.legal_name,
        tax_id=data.tax_id,
        billing_email=str(data.billing_email) if data.billing_email else None,
        billing_phone=data.billing_phone,
        billing_address=data.billing_address,
        billing_city=data.billing_city,
        billing_postal_code=data.billing_postal_code,
        billing_province=data.billing_province,
        billing_country=data.billing_country or "ES",
        primary_color=data.primary_color,
        secondary_color=data.secondary_color,
        accent_color=data.accent_color,
        gowa_basic_auth=data.gowa_basic_auth,
        gowa_webhook_path=f"/webhook/whatsapp/{slug}",
    )
    session.add(tenant)
    session.flush()
    ensure_group_templates(session)
    seed_tenant_organization(session, tenant, data.name)
    clone_groups_for_tenant(session, tenant.id)
    session.commit()
    session.refresh(tenant)
    return tenant


@router.get("/tenants/{tenant_id}", response_model=TenantRead)
def get_tenant_platform(
    tenant_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> Tenant:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return tenant


@router.get("/tenants/{tenant_id}/users", response_model=list[TenantUserRead])
def list_tenant_users(
    tenant_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[TenantUserRead]:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    companies = list(
        session.exec(select(Company).where(Company.tenant_id == tenant_id)).all()
    )
    if not companies:
        return []

    by_id = {c.id: c for c in companies}
    company_ids = list(by_id.keys())
    employees = list(
        session.exec(
            select(Employee)
            .where(col(Employee.company_id).in_(company_ids))
            .order_by(Employee.full_name)
        ).all()
    )

    return [
        TenantUserRead(
            id=e.id,
            company_id=e.company_id,
            company_name=by_id[e.company_id].name,
            full_name=e.full_name,
            employee_code=e.employee_code,
            phone=e.phone,
            email=e.email,
            role=e.role,
            is_active=e.is_active,
        )
        for e in employees
    ]


@router.post("/tenants/{tenant_id}/users", response_model=TenantUserRead, status_code=201)
def create_tenant_user(
    tenant_id: UUID,
    data: TenantUserCreate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> TenantUserRead:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    company = session.exec(
        select(Company).where(Company.tenant_id == tenant_id).order_by(Company.created_at)  # type: ignore[attr-defined]
    ).first()
    if not company:
        raise HTTPException(status_code=400, detail="La cuenta no tiene empresa configurada")

    wc = session.exec(
        select(WorkCenter).where(WorkCenter.company_id == company.id)
    ).first()
    if not wc:
        raise HTTPException(status_code=400, detail="La cuenta no tiene centro de trabajo")

    dept = session.exec(
        select(Department).where(Department.work_center_id == wc.id)
    ).first()
    if not dept:
        raise HTTPException(status_code=400, detail="La cuenta no tiene departamento configurado")

    try:
        id_document = validate_id_document(data.id_document)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if session.exec(
        select(Employee).where(
            Employee.company_id == company.id,
            Employee.id_document == id_document,
        )
    ).first():
        raise HTTPException(status_code=409, detail="DNI/NIE ya registrado en la cuenta")

    employee_code = next_employee_code(session, company.id)
    ensure_system_groups(session, tenant_id)

    row = Employee(
        company_id=company.id,
        department_id=dept.id,
        phone=data.phone.strip(),
        email=data.email.strip().lower() if data.email else None,
        full_name=data.full_name.strip(),
        id_document=id_document,
        employee_code=employee_code,
        role=data.role,
        password_hash=hash_password(data.password),
        is_active=True,
    )
    session.add(row)
    session.flush()
    assign_role_default_group(session, row, tenant_id)
    session.commit()
    session.refresh(row)

    return TenantUserRead(
        id=row.id,
        company_id=row.company_id,
        company_name=company.name,
        full_name=row.full_name,
        employee_code=row.employee_code,
        phone=row.phone,
        email=row.email,
        role=row.role,
        is_active=row.is_active,
    )


@router.patch("/tenants/{tenant_id}", response_model=TenantRead)
def update_tenant_platform(
    tenant_id: UUID,
    data: TenantPlatformUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> Tenant:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    payload = data.model_dump(exclude_unset=True)
    new_slug = payload.pop("slug", None)
    if new_slug is not None:
        slug = resolve_tenant_slug_update(
            session, tenant.id, payload.get("name") or tenant.name, new_slug
        )
        if slug != tenant.slug:
            tenant.slug = slug
            tenant.gowa_webhook_path = f"/webhook/whatsapp/{slug}"

    for key, value in payload.items():
        setattr(tenant, key, value)

    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


@router.delete("/tenants/{tenant_id}", status_code=204)
def delete_tenant_platform(
    tenant_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
    permanent: bool = False,
) -> None:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    try:
        if permanent:
            delete_tenant_permanent(session, tenant_id)
        else:
            tenant.is_active = False
            session.add(tenant)
        session.commit()
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo eliminar la cuenta: tiene datos asociados",
        ) from exc


@router.get("/group-templates", response_model=list[GroupTemplateRead])
def list_group_templates(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[GroupTemplate]:
    ensure_group_templates(session)
    session.commit()
    return list(
        session.exec(
            select(GroupTemplate).order_by(GroupTemplate.sort_order)
        ).all()
    )


@router.patch("/group-templates/{template_id}", response_model=GroupTemplateRead)
def update_group_template(
    template_id: UUID,
    data: GroupTemplateUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> GroupTemplate:
    row = session.get(GroupTemplate, template_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    if data.permissions is not None:
        row.permissions = data.permissions
    if data.description is not None:
        row.description = data.description
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
