"""Registro y cómputo de paradas (descansos) por empleado."""

from datetime import date, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.models import BreakType, Employee, WorkBreak


class BreakService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _find_open_clock_in(self, employee_id: UUID) -> UUID | None:
        """Jornada abierta: entrada sin salida."""
        from app.models.models import ClockIn

        record = self._session.exec(
            select(ClockIn)
            .where(ClockIn.employee_id == employee_id, ClockIn.salida_at == None)  # noqa: E711
            .order_by(ClockIn.entrada_at.desc())  # type: ignore[attr-defined]
        ).first()
        return record.id if record else None

    def register_break(
        self,
        employee_id: UUID,
        record_type: BreakType,
        *,
        whatsapp_message_id: str | None = None,
        notes: str | None = None,
        source: str = "whatsapp",
    ) -> WorkBreak:
        clock_in_id = self._find_open_clock_in(employee_id)
        record = WorkBreak(
            employee_id=employee_id,
            clock_in_id=clock_in_id,
            record_type=record_type,
            recorded_at=datetime.utcnow(),
            whatsapp_message_id=whatsapp_message_id,
            notes=notes,
            source=source,
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def get_last_break(self, employee_id: UUID) -> WorkBreak | None:
        return self._session.exec(
            select(WorkBreak)
            .where(WorkBreak.employee_id == employee_id)
            .order_by(WorkBreak.recorded_at.desc())  # type: ignore[attr-defined]
        ).first()

    @staticmethod
    def compute_break_minutes(
        records: list[WorkBreak],
        *,
        day_from: date | None = None,
        day_to: date | None = None,
    ) -> int:
        """Suma minutos de paradas emparejando inicio → fin en orden cronológico."""
        filtered = sorted(records, key=lambda r: r.recorded_at)
        if day_from:
            filtered = [
                r
                for r in filtered
                if r.recorded_at.date() >= day_from
            ]
        if day_to:
            filtered = [
                r
                for r in filtered
                if r.recorded_at.date() <= day_to
            ]

        total_seconds = 0
        open_start: datetime | None = None
        for row in filtered:
            if row.record_type == BreakType.INICIO:
                open_start = row.recorded_at
            elif row.record_type == BreakType.FIN and open_start:
                delta = row.recorded_at - open_start
                if delta.total_seconds() > 0:
                    total_seconds += int(delta.total_seconds())
                open_start = None
        return total_seconds // 60

    def summary_for_employees(
        self,
        employee_ids: list[UUID],
        *,
        day_from: date | None = None,
        day_to: date | None = None,
    ) -> list[dict]:
        if not employee_ids:
            return []

        stmt = (
            select(WorkBreak)
            .where(WorkBreak.employee_id.in_(employee_ids))  # type: ignore[attr-defined]
            .order_by(WorkBreak.recorded_at)
        )
        all_rows = list(self._session.exec(stmt).all())
        by_emp: dict[UUID, list[WorkBreak]] = {}
        for row in all_rows:
            by_emp.setdefault(row.employee_id, []).append(row)

        employees = {
            e.id: e
            for e in self._session.exec(
                select(Employee).where(Employee.id.in_(employee_ids))  # type: ignore[attr-defined]
            ).all()
        }

        out: list[dict] = []
        for emp_id in employee_ids:
            emp = employees.get(emp_id)
            if not emp:
                continue
            rows = by_emp.get(emp_id, [])
            minutes = self.compute_break_minutes(
                rows, day_from=day_from, day_to=day_to
            )
            inicios = sum(1 for r in rows if r.record_type == BreakType.INICIO)
            fines = sum(1 for r in rows if r.record_type == BreakType.FIN)
            out.append(
                {
                    "employee_id": emp_id,
                    "employee_name": emp.full_name,
                    "employee_code": emp.employee_code,
                    "company_id": emp.company_id,
                    "total_minutes": minutes,
                    "total_hours": round(minutes / 60, 2),
                    "break_starts": inicios,
                    "break_ends": fines,
                    "open_breaks": max(0, inicios - fines),
                }
            )
        out.sort(key=lambda x: x["employee_name"])
        return out
