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
)
from app.services.pricing_service import (
    get_active_discount,
    sync_subscription_pricing,
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
    companies_out: list[CompanyBillingRead] = []
    for row in data["companies"]:
        c: Company = row["company"]
        companies_out.append(
            CompanyBillingRead(
                id=c.id,
                name=c.name,
                tax_id=c.tax_id,
                is_active=c.is_active,
                legal_name=c.legal_name,
                billing_email=c.billing_email,
                billing_phone=c.billing_phone,
                billing_address=c.billing_address,
                billing_city=c.billing_city,
                billing_postal_code=c.billing_postal_code,
                billing_province=c.billing_province,
                billing_country=c.billing_country or "ES",
                subscription=_subscription_read(session, row["subscription"]),
                billing_methods=[
                    BillingMethodRead.model_validate(m)
                    for m in row["billing_methods"]
                ],
            )
        )
    session.commit()
    return TenantBillingOverview(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        legal_name=tenant.legal_name,
        tax_id=tenant.tax_id,
        billing_email=tenant.billing_email,
        billing_phone=tenant.billing_phone,
        billing_address=tenant.billing_address,
        billing_city=tenant.billing_city,
        billing_postal_code=tenant.billing_postal_code,
        billing_province=tenant.billing_province,
        billing_country=tenant.billing_country or "ES",
        account_billing_methods=[
            BillingMethodRead.model_validate(m) for m in data["account_methods"]
        ],
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
    sub = ensure_default_subscription(session, tenant, company)
    session.commit()
    session.refresh(company)

    return CompanyBillingRead(
        id=company.id,
        name=company.name,
        tax_id=company.tax_id,
        is_active=company.is_active,
        legal_name=company.legal_name,
        billing_email=company.billing_email,
        billing_phone=company.billing_phone,
        billing_address=company.billing_address,
        billing_city=company.billing_city,
        billing_postal_code=company.billing_postal_code,
        billing_province=company.billing_province,
        billing_country=company.billing_country or "ES",
        subscription=_subscription_read(session, sub),
        billing_methods=[],
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
    overview = get_tenant_billing_overview(session, tenant_id)
    row = next(r for r in overview["companies"] if r["company"].id == company_id)
    session.commit()
    return CompanyBillingRead(
        id=company.id,
        name=company.name,
        tax_id=company.tax_id,
        is_active=company.is_active,
        legal_name=company.legal_name,
        billing_email=company.billing_email,
        billing_phone=company.billing_phone,
        billing_address=company.billing_address,
        billing_city=company.billing_city,
        billing_postal_code=company.billing_postal_code,
        billing_province=company.billing_province,
        billing_country=company.billing_country or "ES",
        subscription=_subscription_read(session, row["subscription"]),
        billing_methods=[
            BillingMethodRead.model_validate(m) for m in row["billing_methods"]
        ],
    )


@router.patch(
    "/{tenant_id}/subscriptions/{subscription_id}", response_model=SubscriptionRead
)
def update_subscription(
    tenant_id: UUID,
    subscription_id: UUID,
    data: SubscriptionUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> Subscription:
    sub = session.get(Subscription, subscription_id)
    if not sub or sub.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")

    payload = data.model_dump(exclude_unset=True)
    plan_id = payload.pop("pricing_plan_id", None)
    discount_id = payload.pop("discount_id", None)
    cycle = payload.pop("billing_cycle", None)

    if plan_id is not None:
        plan = session.get(PricingPlan, plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail="Tarifa no encontrada")
        use_cycle = cycle or sub.billing_cycle
        discount = get_active_discount(
            session, discount_id if discount_id is not None else sub.discount_id,
            plan.id,
        )
        sync_subscription_pricing(session, sub, plan, use_cycle, discount)
    elif cycle is not None and sub.pricing_plan_id:
        plan = session.get(PricingPlan, sub.pricing_plan_id)
        if plan:
            discount = get_active_discount(session, sub.discount_id, plan.id)
            sync_subscription_pricing(session, sub, plan, cycle, discount)
    elif discount_id is not None and sub.pricing_plan_id:
        plan = session.get(PricingPlan, sub.pricing_plan_id)
        if plan:
            discount = get_active_discount(session, discount_id, plan.id)
            sync_subscription_pricing(session, sub, plan, sub.billing_cycle, discount)

    for key, value in payload.items():
        setattr(sub, key, value)
    sub.updated_at = datetime.utcnow()
    session.add(sub)
    session.commit()
    session.refresh(sub)
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
    if data.company_id:
        company = session.get(Company, data.company_id)
        if not company or company.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if data.is_default:
        stmt = select(BillingMethod).where(BillingMethod.tenant_id == tenant_id)
        if data.company_id:
            stmt = stmt.where(BillingMethod.company_id == data.company_id)
        else:
            stmt = stmt.where(BillingMethod.company_id.is_(None))  # type: ignore[union-attr]
        for m in session.exec(stmt).all():
            m.is_default = False
            session.add(m)

    row = BillingMethod(tenant_id=tenant_id, **data.model_dump())
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
