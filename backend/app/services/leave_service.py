from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select  # noqa: F401

from app.models.models import Employee, EmployeeLeaveBalance, LeaveRequest, LeaveStatus, LeaveType
from app.models.tenant import Company
from app.schemas.ollama import OllamaIntentResponse
from app.services.notification_service import notify_leave_request_created


def get_or_create_balance(
    session: Session,
    employee_id: UUID,
    leave_type: LeaveType,
) -> EmployeeLeaveBalance:
    bal = session.exec(
        select(EmployeeLeaveBalance).where(
            EmployeeLeaveBalance.employee_id == employee_id,
            EmployeeLeaveBalance.leave_type_id == leave_type.id,
        )
    ).first()
    if not bal:
        bal = EmployeeLeaveBalance(
            employee_id=employee_id,
            leave_type_id=leave_type.id,
            total_days=leave_type.default_days or 0.0,
        )
        session.add(bal)
        session.flush()
    return bal


def get_remaining_days(
    session: Session,
    employee_id: UUID,
    leave_type_id: UUID,
    balance: EmployeeLeaveBalance,
) -> float:
    used = session.exec(
        select(func.coalesce(func.sum(LeaveRequest.days_requested), 0.0)).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type_id == leave_type_id,
            LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),  # type: ignore[attr-defined]
        )
    ).one()
    return float(balance.total_days) - float(used)


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

    def _resolve_leave_type(
        self,
        company_tenant_id: UUID,
        hint_name: str | None,
        fallback_name: str = "Vacaciones",
    ) -> LeaveType | None:
        """Busca un LeaveType por nombre (hint) o por nombre de fallback."""
        if hint_name:
            lt = self._session.exec(
                select(LeaveType).where(
                    LeaveType.tenant_id == company_tenant_id,
                    LeaveType.is_active == True,  # noqa: E712
                )
            ).all()
            hint_lower = hint_name.lower().strip()
            # Exact match first, then partial
            for candidate in lt:
                if candidate.name.lower() == hint_lower:
                    return candidate
            for candidate in lt:
                if hint_lower in candidate.name.lower() or candidate.name.lower() in hint_lower:
                    return candidate
        # Fallback by name
        return self._session.exec(
            select(LeaveType).where(
                LeaveType.tenant_id == company_tenant_id,
                LeaveType.name == fallback_name,
                LeaveType.is_active == True,  # noqa: E712
            )
        ).first()

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

        company = self._session.exec(
            select(Company).where(Company.id == employee.company_id)
        ).first()
        leave_type_id = None
        lt: LeaveType | None = None
        if company:
            hint_name = intent.entities.get("leave_type_name") or intent.entities.get("tipo")
            fallback = "Vacaciones" if intent.intent == "solicitar_vacaciones" else None
            lt = self._resolve_leave_type(company.tenant_id, hint_name, fallback or "Vacaciones")
            if lt:
                leave_type_id = lt.id
                if lt.has_own_balance:
                    bal = get_or_create_balance(self._session, employee.id, lt)
                    remaining = get_remaining_days(self._session, employee.id, lt.id, bal)
                    if days > remaining:
                        return None, (
                            f"No tienes saldo de {lt.name} suficiente. "
                            f"Disponibles: {remaining:.1f} días; solicitados: {days:.1f}."
                        )
                elif lt.deducts_balance and days > employee.vacation_days_balance:
                    return None, (
                        f"No tienes saldo suficiente de vacaciones. Disponibles: "
                        f"{employee.vacation_days_balance:.1f} días; solicitados: {days:.1f}."
                    )
        elif days > employee.vacation_days_balance:
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
            leave_type_id=leave_type_id,
            reason=intent.entities.get("motivo"),
            supervisor_id=employee.supervisor_id,
            raw_message=raw_message,
        )
        self._session.add(request)
        self._session.flush()
        if company:
            notify_leave_request_created(
                self._session,
                tenant_id=company.tenant_id,
                employee=employee,
                start_date=str(start),
                end_date=str(end),
                days=days,
                leave_type_name=lt.name if lt else None,
                reason=request.reason,
            )
        self._session.commit()
        self._session.refresh(request)
        motivo = intent.entities.get("motivo")
        type_label = f" [{lt.name}]" if lt else ""
        return request, (
            f"Solicitud registrada{type_label} ({start} → {end}, {days:.1f} días)"
            + (f" — {motivo}" if motivo else "")
            + ". Pendiente de aprobación de tu supervisor."
        )

    def get_balance_message(self, employee: Employee) -> str:
        company = self._session.exec(
            select(Company).where(Company.id == employee.company_id)
        ).first()

        lines: list[str] = []

        # Vacation balance (global)
        pending_vac = self._session.exec(
            select(LeaveRequest).where(
                LeaveRequest.employee_id == employee.id,
                LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),  # type: ignore[attr-defined]
                LeaveRequest.leave_type_id.is_(None)  # type: ignore[union-attr]
                | LeaveRequest.leave_type_id.in_(  # type: ignore[union-attr]
                    select(LeaveType.id).where(
                        LeaveType.deducts_balance == True,  # noqa: E712
                        LeaveType.has_own_balance == False,  # noqa: E712
                    )
                ),
            )
        ).all()
        pending_days = sum(r.days_requested for r in pending_vac)
        lines.append(
            f"• Vacaciones: {employee.vacation_days_balance:.1f} días disponibles"
            + (f" ({pending_days:.1f} en proceso de aprobación)" if pending_days else "")
        )

        # Own-balance types
        if company:
            own_types = self._session.exec(
                select(LeaveType).where(
                    LeaveType.tenant_id == company.tenant_id,
                    LeaveType.has_own_balance == True,  # noqa: E712
                    LeaveType.is_active == True,  # noqa: E712
                )
            ).all()
            for lt in own_types:
                bal = self._session.exec(
                    select(EmployeeLeaveBalance).where(
                        EmployeeLeaveBalance.employee_id == employee.id,
                        EmployeeLeaveBalance.leave_type_id == lt.id,
                    )
                ).first()
                total = float(bal.total_days) if bal else float(lt.default_days or 0)
                remaining = get_remaining_days(self._session, employee.id, lt.id, bal) if bal else total
                lines.append(f"• {lt.name}: {remaining:.1f} días disponibles (de {total:.1f} asignados)")

        if len(lines) == 1:
            return lines[0]
        return "Tus saldos de permiso:\n" + "\n".join(lines)

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
