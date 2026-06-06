from datetime import date, timedelta
from uuid import UUID

from sqlmodel import Session, select  # noqa: F401

from app.models.models import Employee, LeaveRequest, LeaveStatus
from app.models.tenant import Company
from app.schemas.ollama import OllamaIntentResponse
from app.services.notification_service import notify_supervisor_sync


class LeaveService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def count_business_days(self, start: date, end: date) -> float:
        if end < start:
            start, end = end, start
        days = 0
        current = start
        while current <= end:
            if current.weekday() < 5:
                days += 1
            current += timedelta(days=1)
        return float(max(days, 1))

    def create_request(
        self,
        employee: Employee,
        intent: OllamaIntentResponse,
        raw_message: str,
    ) -> tuple[LeaveRequest | None, str]:
        start = intent.get_date("fecha_inicio")
        end = intent.get_date("fecha_fin")
        if not start or not end:
            return None, (
                "No he podido identificar las fechas. "
                "Indícame el período así: 'del 1 al 31 de agosto'."
            )
        days = self.count_business_days(start, end)

        if days > employee.vacation_days_balance:
            return None, (
                f"No tienes saldo suficiente. Disponibles: "
                f"{employee.vacation_days_balance:.1f} días; solicitados: {days:.1f}."
            )

        request = LeaveRequest(
            employee_id=employee.id,
            start_date=start,
            end_date=end,
            days_requested=days,
            status=LeaveStatus.PENDING,
            reason=intent.entities.get("motivo"),
            supervisor_id=employee.supervisor_id,
            raw_message=raw_message,
        )
        self._session.add(request)
        self._session.flush()
        if employee.supervisor_id:
            company = self._session.exec(
                select(Company).where(Company.id == employee.company_id)
            ).first()
            if company:
                notify_supervisor_sync(
                    self._session,
                    tenant_id=company.tenant_id,
                    actor=employee,
                    event_type="leave_request",
                    title=f"Solicitud de vacaciones — {employee.full_name}",
                    body=f"{employee.full_name} solicita vacaciones del {start} al {end} ({days:.1f} días).",
                    link=f"/app/vacaciones",
                )
        self._session.commit()
        self._session.refresh(request)
        return request, (
            f"Solicitud registrada ({start} → {end}, {days:.1f} días). "
            "Pendiente de aprobación de tu supervisor."
        )

    def get_balance_message(self, employee: Employee) -> str:
        pending = self._session.exec(
            select(LeaveRequest).where(
                LeaveRequest.employee_id == employee.id,
                LeaveRequest.status == LeaveStatus.PENDING,
            )
        ).all()
        pending_days = sum(r.days_requested for r in pending)
        return (
            f"Saldo de vacaciones: {employee.vacation_days_balance:.1f} días. "
            f"Pendientes de aprobación: {len(pending)} ({pending_days:.1f} días)."
        )

    def acknowledge_document(
        self, employee_id: UUID, text: str
    ) -> str:
        from app.models.documents import DocumentDelivery

        statement = (
            select(DocumentDelivery)
            .where(
                DocumentDelivery.employee_id == employee_id,
                DocumentDelivery.acknowledged_at.is_(None),  # type: ignore[union-attr]
            )
            .order_by(DocumentDelivery.created_at.desc())  # type: ignore[attr-defined]
        )
        delivery = self._session.exec(statement).first()
        if not delivery:
            return "No hay documentos pendientes de confirmar."
        normalized = text.strip().lower()
        if normalized not in {"recibido", "acepto", "confirmo", "ok"}:
            return (
                'Responde "Recibido" o "Acepto" para confirmar la recepción del documento.'
            )
        from datetime import datetime

        delivery.acknowledged_at = datetime.utcnow()
        delivery.acknowledgment_text = text.strip()
        self._session.add(delivery)
        self._session.commit()
        return f"Confirmación registrada para {delivery.file_name}. Gracias."
