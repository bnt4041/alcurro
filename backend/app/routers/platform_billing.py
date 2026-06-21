from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.billing import BillingMethod, PricingPlan, Subscription
from app.models.rbac import PlatformUser
from app.models.tenant import Company, Tenant
from app.schemas.billing import (
    BillingMethodCreate,
    BillingMethodRead,
    BillingMethodUpdate,
    CompanyBillingCreate,
    CompanyBillingRead,
    CompanyBillingUpdate,
    SubscriptionRead,
    SubscriptionUpdate,
    TenantBillingOverview,
)
from app.services.billing_service import (
    copy_tenant_billing_to_company,
    ensure_default_subscription,
    get_tenant_billing_overview,
    resolve_billing_company,
)
from app.services.pricing_service import (
    get_active_discount,
    sync_subscription_pricing,
)
from app.services.paddle_service import (
    apply_paddle_discount_to_subscription,
    update_paddle_subscription_variant,
)
from app.services.org_service import seed_company_organization

router = APIRouter(prefix="/platform/tenants", tags=["platform-billing"])


def _subscription_read(session: Session, sub: Subscription) -> SubscriptionRead:
    plan = (
        session.get(PricingPlan, sub.pricing_plan_id) if sub.pricing_plan_id else None
    )
    read = SubscriptionRead.model_validate(sub)
    read.max_active_users = plan.max_active_users if plan else None
    return read


def _overview_response(session: Session, tenant_id: UUID) -> TenantBillingOverview:
    data = get_tenant_billing_overview(session, tenant_id)
    tenant: Tenant = data["tenant"]
    billing_company: Company | None = data.get("billing_company")
    sub: Subscription | None = data.get("subscription")
    methods: list[BillingMethod] = data.get("billing_methods", [])

    companies_out: list[CompanyBillingRead] = []
    for row in data["companies"]:
        c: Company = row["company"]
        companies_out.append(
            CompanyBillingRead(
                id=c.id,
                name=c.name,
                tax_id=c.tax_id,
                is_active=c.is_active,
                is_billing_company=row.get("is_billing_company", False),
                legal_name=c.legal_name,
                billing_email=c.billing_email,
                billing_phone=c.billing_phone,
                billing_address=c.billing_address,
                billing_city=c.billing_city,
                billing_postal_code=c.billing_postal_code,
                billing_province=c.billing_province,
                billing_country=c.billing_country or "ES",
            )
        )
    session.commit()
    return TenantBillingOverview(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        billing_company_id=tenant.billing_company_id,
        legal_name=tenant.legal_name,
        tax_id=tenant.tax_id,
        billing_email=tenant.billing_email,
        billing_phone=tenant.billing_phone,
        billing_address=tenant.billing_address,
        billing_city=tenant.billing_city,
        billing_postal_code=tenant.billing_postal_code,
        billing_province=tenant.billing_province,
        billing_country=tenant.billing_country or "ES",
        subscription=_subscription_read(session, sub) if sub else None,
        billing_methods=[BillingMethodRead.model_validate(m) for m in methods],
        companies=companies_out,
    )


@router.get("/{tenant_id}/billing", response_model=TenantBillingOverview)
def get_tenant_billing(
    tenant_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> TenantBillingOverview:
    if not session.get(Tenant, tenant_id):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return _overview_response(session, tenant_id)


@router.put("/{tenant_id}/billing-company/{company_id}", response_model=TenantBillingOverview)
def set_billing_company(
    tenant_id: UUID,
    company_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> TenantBillingOverview:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    company = session.get(Company, company_id)
    if not company or company.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Empresa no encontrada en esta cuenta")
    tenant.billing_company_id = company_id
    session.add(tenant)
    session.commit()
    return _overview_response(session, tenant_id)


@router.post("/{tenant_id}/companies", response_model=CompanyBillingRead, status_code=201)
def add_tenant_company(
    tenant_id: UUID,
    data: CompanyBillingCreate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> CompanyBillingRead:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    company = Company(
        tenant_id=tenant.id,
        name=data.name,
        tax_id=data.tax_id,
        legal_name=data.legal_name or data.name,
        billing_email=data.billing_email or tenant.billing_email,
        billing_phone=data.billing_phone or tenant.billing_phone,
        billing_country=tenant.billing_country or "ES",
    )
    copy_tenant_billing_to_company(tenant, company)
    session.add(company)
    session.flush()
    seed_company_organization(session, company)
    # Si es la primera empresa, la marcamos como empresa de facturación
    if tenant.billing_company_id is None:
        tenant.billing_company_id = company.id
        session.add(tenant)
    session.commit()
    session.refresh(company)

    return CompanyBillingRead(
        id=company.id,
        name=company.name,
        tax_id=company.tax_id,
        is_active=company.is_active,
        is_billing_company=(tenant.billing_company_id == company.id),
        legal_name=company.legal_name,
        billing_email=company.billing_email,
        billing_phone=company.billing_phone,
        billing_address=company.billing_address,
        billing_city=company.billing_city,
        billing_postal_code=company.billing_postal_code,
        billing_province=company.billing_province,
        billing_country=company.billing_country or "ES",
    )


@router.patch("/{tenant_id}/companies/{company_id}", response_model=CompanyBillingRead)
def update_tenant_company_billing(
    tenant_id: UUID,
    company_id: UUID,
    data: CompanyBillingUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> CompanyBillingRead:
    company = session.get(Company, company_id)
    if not company or company.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    session.add(company)
    session.commit()
    session.refresh(company)
    tenant = session.get(Tenant, tenant_id)
    return CompanyBillingRead(
        id=company.id,
        name=company.name,
        tax_id=company.tax_id,
        is_active=company.is_active,
        is_billing_company=(tenant.billing_company_id == company.id if tenant else False),
        legal_name=company.legal_name,
        billing_email=company.billing_email,
        billing_phone=company.billing_phone,
        billing_address=company.billing_address,
        billing_city=company.billing_city,
        billing_postal_code=company.billing_postal_code,
        billing_province=company.billing_province,
        billing_country=company.billing_country or "ES",
    )


@router.patch(
    "/{tenant_id}/subscription", response_model=SubscriptionRead
)
def update_subscription(
    tenant_id: UUID,
    data: SubscriptionUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> SubscriptionRead:
    sub = session.exec(
        select(Subscription).where(Subscription.tenant_id == tenant_id)
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")

    payload = data.model_dump(exclude_unset=True)
    plan_id = payload.pop("pricing_plan_id", None)
    discount_id = payload.pop("discount_id", None)
    cycle = payload.pop("billing_cycle", None)

    ls_sync_plan: PricingPlan | None = None
    ls_sync_cycle: str | None = None
    ls_apply_discount_code: str | None | bool = False  # False=skip, None=remove, str=apply

    if plan_id is not None:
        plan = session.get(PricingPlan, plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail="Tarifa no encontrada")
        use_cycle = cycle or sub.billing_cycle
        effective_discount_id = discount_id if discount_id is not None else sub.discount_id
        discount = get_active_discount(session, effective_discount_id, plan.id)
        sync_subscription_pricing(session, sub, plan, use_cycle, discount)
        ls_sync_plan, ls_sync_cycle = plan, use_cycle
        if discount_id is not None:
            ls_apply_discount_code = discount.code if discount else None
    elif cycle is not None and sub.pricing_plan_id:
        plan = session.get(PricingPlan, sub.pricing_plan_id)
        if plan:
            discount = get_active_discount(session, sub.discount_id, plan.id)
            sync_subscription_pricing(session, sub, plan, cycle, discount)
            ls_sync_plan, ls_sync_cycle = plan, cycle
    elif discount_id is not None and sub.pricing_plan_id:
        plan = session.get(PricingPlan, sub.pricing_plan_id)
        if plan:
            discount = get_active_discount(session, discount_id, plan.id)
            sync_subscription_pricing(session, sub, plan, sub.billing_cycle, discount)
            ls_apply_discount_code = discount.code if discount else None

    for key, value in payload.items():
        setattr(sub, key, value)
    sub.updated_at = datetime.utcnow()
    session.add(sub)
    session.commit()
    session.refresh(sub)

    if ls_sync_plan and ls_sync_cycle:
        tenant = session.get(Tenant, tenant_id)
        if tenant:
            update_paddle_subscription_variant(session, tenant, sub, ls_sync_plan, ls_sync_cycle)

    if ls_apply_discount_code is not False and sub.paddle_subscription_id:
        apply_paddle_discount_to_subscription(
            sub.paddle_subscription_id,
            ls_apply_discount_code if ls_apply_discount_code else None,
        )

    return _subscription_read(session, sub)


@router.post(
    "/{tenant_id}/billing-methods",
    response_model=BillingMethodRead,
    status_code=201,
)
def create_billing_method(
    tenant_id: UUID,
    data: BillingMethodCreate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> BillingMethod:
    if not session.get(Tenant, tenant_id):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    if data.is_default:
        for m in session.exec(
            select(BillingMethod).where(BillingMethod.tenant_id == tenant_id)
        ).all():
            m.is_default = False
            session.add(m)

    row = BillingMethod(
        tenant_id=tenant_id,
        label=data.label,
        method_type=data.method_type,
        is_default=data.is_default,
        holder_name=data.holder_name,
        iban_masked=data.iban_masked,
        card_brand=data.card_brand,
        card_last4=data.card_last4,
        notes=data.notes,
        company_id=None,  # deprecated: siempre a nivel cuenta
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch(
    "/{tenant_id}/billing-methods/{method_id}",
    response_model=BillingMethodRead,
)
def update_billing_method(
    tenant_id: UUID,
    method_id: UUID,
    data: BillingMethodUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> BillingMethod:
    row = session.get(BillingMethod, method_id)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Método de pago no encontrado")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{tenant_id}/billing-methods/{method_id}", status_code=204)
def delete_billing_method(
    tenant_id: UUID,
    method_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> None:
    row = session.get(BillingMethod, method_id)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Método de pago no encontrado")
    session.delete(row)
    session.commit()
