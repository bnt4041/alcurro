"""Compatibilidad: TenantContext = OrgContext."""

from app.core.org_context import (
    OrgContext,
    get_company_for_user,
    get_org_context,
)

TenantContext = OrgContext
get_tenant_context = get_org_context

__all__ = [
    "TenantContext",
    "get_tenant_context",
    "OrgContext",
    "get_org_context",
    "get_company_for_user",
]
