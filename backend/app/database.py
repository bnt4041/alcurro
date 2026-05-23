from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings
from app.models.settings import SystemSettings  # noqa: F401
from app.models.billing import (  # noqa: F401
    BillingMethod,
    Discount,
    PricingPlan,
    StripePayment,
    Subscription,
)
from app.models.tenant import Company, Tenant  # noqa: F401
from app.models.organization import Department, GroupTemplate, WorkCenter  # noqa: F401
from app.models.rbac import EmployeeGroup, PlatformUser, UserGroup  # noqa: F401
from app.models.legal import LegalAcceptance, LegalDocument  # noqa: F401
from app.models.models import Employee  # noqa: F401

settings = get_settings()
engine = create_engine(settings.database_url, echo=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
