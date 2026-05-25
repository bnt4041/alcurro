from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.models import ClockIn, ClockInType, Employee
from app.models.tenant import Company
from app.services.clock_incident_hook import process_clock_in_incidents


class ClockService:
    def __init__(self, session: Session, tenant_id: UUID | None = None) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self.last_incident = None

    def _company_ids(self) -> list[UUID]:
        if not self._tenant_id:
            return []
        return [
            c.id
            for c in self._session.exec(
                select(Company).where(Company.tenant_id == self._tenant_id)
            ).all()
        ]

    def get_employee_by_phone(self, phone: str) -> Employee | None:
        normalized = "".join(c for c in phone if c.isdigit())
        company_ids = self._company_ids()
        stmt = select(Employee).where(Employee.is_active == True)  # noqa: E712
        if company_ids:
            stmt = stmt.where(Employee.company_id.in_(company_ids))  # type: ignore[attr-defined]
        for emp in self._session.exec(stmt).all():
            emp_digits = "".join(c for c in emp.phone if c.isdigit())
            if emp_digits.endswith(normalized[-9:]) or normalized.endswith(
                emp_digits[-9:]
            ):
                return emp
        return None

    def register_clock(
        self,
        employee_id: UUID,
        record_type: ClockInType,
        latitude: float | None = None,
        longitude: float | None = None,
        whatsapp_message_id: str | None = None,
        notes: str | None = None,
        project_id: UUID | None = None,
        *,
        commit: bool = True,
    ) -> ClockIn:
        record = ClockIn(
            employee_id=employee_id,
            record_type=record_type,
            recorded_at=datetime.utcnow(),
            latitude=latitude,
            longitude=longitude,
            whatsapp_message_id=whatsapp_message_id,
            notes=notes,
            project_id=project_id,
            source="whatsapp",
        )
        self._session.add(record)
        if commit:
            self._session.commit()
            self._session.refresh(record)
        else:
            self._session.flush()
        self.last_incident = None
        if self._tenant_id:
            emp = self._session.get(Employee, employee_id)
            if emp:
                self.last_incident = process_clock_in_incidents(
                    self._session,
                    tenant_id=self._tenant_id,
                    employee=emp,
                    clock=record,
                )
        return record

    def get_last_clock(self, employee_id: UUID) -> ClockIn | None:
        statement = (
            select(ClockIn)
            .where(ClockIn.employee_id == employee_id)
            .order_by(ClockIn.recorded_at.desc())  # type: ignore[attr-defined]
        )
        return self._session.exec(statement).first()
