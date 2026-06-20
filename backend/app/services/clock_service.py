from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.models import ClockIn, Employee
from app.models.tenant import Company
from app.services.clock_incident_hook import process_clock_in_incidents
from app.services.notification_service import notify_supervisor_sync


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

    def get_open_clock(self, employee_id: UUID) -> ClockIn | None:
        """Jornada abierta: entrada sin salida."""
        return self._session.exec(
            select(ClockIn)
            .where(ClockIn.employee_id == employee_id, ClockIn.salida_at == None)  # noqa: E711
            .order_by(ClockIn.entrada_at.desc())  # type: ignore[attr-defined]
        ).first()

    def is_open_clock_expired(self, employee_id: UUID) -> bool:
        """True si el fichaje abierto supera el umbral de omisión de salida del tenant.

        Usa la regla configurable `missing_clock_out_hours` (omisión de salida). Si la
        regla está desactivada, no se considera caducado y se permite cerrar con normalidad.
        """
        if not self._tenant_id:
            return False
        record = self.get_open_clock(employee_id)
        if not record:
            return False
        from app.services.incident_service import get_or_create_rules

        rules = get_or_create_rules(self._session, self._tenant_id)
        if not rules.missing_clock_out_enabled:
            return False
        elapsed = (datetime.utcnow() - record.entrada_at).total_seconds() / 3600
        return elapsed >= rules.missing_clock_out_hours

    def get_last_clock(self, employee_id: UUID) -> ClockIn | None:
        """Último registro de jornada (abierto o cerrado)."""
        return self._session.exec(
            select(ClockIn)
            .where(ClockIn.employee_id == employee_id)
            .order_by(ClockIn.entrada_at.desc())  # type: ignore[attr-defined]
        ).first()

    def open_clock(
        self,
        employee_id: UUID,
        latitude: float | None = None,
        longitude: float | None = None,
        address: str | None = None,
        whatsapp_message_id: str | None = None,
        notes: str | None = None,
        project_id: UUID | None = None,
        *,
        commit: bool = True,
    ) -> ClockIn:
        record = ClockIn(
            employee_id=employee_id,
            entrada_at=datetime.utcnow(),
            latitude=latitude,
            longitude=longitude,
            address=address,
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
                if emp.supervisor_id:
                    notify_supervisor_sync(
                        self._session,
                        tenant_id=self._tenant_id,
                        actor=emp,
                        event_type="clock_in",
                        title=f"Fichaje de entrada — {emp.full_name}",
                        body=f"{emp.full_name} ha fichado la entrada.",
                        link=f"/app/fichajes?employee_id={emp.id}",
                    )
        return record

    def close_clock(
        self,
        employee_id: UUID,
        work_summary: str | None = None,
        whatsapp_message_id: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        address: str | None = None,
        *,
        commit: bool = True,
    ) -> ClockIn | None:
        """Cierra la jornada abierta. Devuelve None si no hay jornada abierta."""
        record = self.get_open_clock(employee_id)
        if not record:
            return None
        record.salida_at = datetime.utcnow()
        if work_summary:
            record.work_summary = work_summary
        if whatsapp_message_id:
            record.whatsapp_message_id = whatsapp_message_id
        if latitude is not None:
            record.latitude_out = latitude
        if longitude is not None:
            record.longitude_out = longitude
        if address:
            record.address_out = address
        self._session.add(record)
        if self._tenant_id:
            emp = self._session.get(Employee, employee_id)
            if emp and emp.supervisor_id:
                notify_supervisor_sync(
                    self._session,
                    tenant_id=self._tenant_id,
                    actor=emp,
                    event_type="clock_out",
                    title=f"Fichaje de salida — {emp.full_name}",
                    body=f"{emp.full_name} ha fichado la salida.",
                    link=f"/app/fichajes?employee_id={emp.id}",
                )
        if commit:
            self._session.commit()
            self._session.refresh(record)
        else:
            self._session.flush()
        return record
