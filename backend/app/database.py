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
from app.models.legal import LegalAcceptance, LegalDocument, LegalToken  # noqa: F401
from app.models.mail import MailLog  # noqa: F401
from app.models.signature import (  # noqa: F401
    SignatureEnvelope,
    SignatureEvent,
    SignatureNotification,
    SignatureOtp,
    SignatureSigner,
)
from app.models.models import Employee  # noqa: F401
from app.models.ai import (  # noqa: F401
    AiAction,
    AiConversationRule,
    AiProfileAction,
    AiUsageRecord,
    AiWhatsappMessage,
)
from app.models.documents import (  # noqa: F401
    DocumentDelivery,
    DocumentDeliveryTag,
    DocumentExpiryNotificationLog,
    DocumentNotificationSettings,
    DocumentTag,
    DocumentType,
)
from app.models.clock_settings import (  # noqa: F401
    ClockSettings,
    EmployeeInboundDocument,
    InboundPendingUpload,
)
from app.models.project import ClockPendingFichaje, Project  # noqa: F401
from app.models.incident import Incident, IncidentAutoRule, IncidentNote  # noqa: F401
from app.models.platform_policy import PlatformPolicy  # noqa: F401

settings = get_settings()
engine = create_engine(settings.database_url, echo=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
