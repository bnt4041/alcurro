"""Validación y normalización de horarios de empleado (periodos, bloques, franjas)."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from app.models.models import Employee


class WorkScheduleTimeSlot(BaseModel):
    work_start_time: time
    work_end_time: time
    break_minutes: int = Field(default=0, ge=0, le=480)


class WorkScheduleDayBlock(BaseModel):
    work_days: list[int] = Field(min_length=1)
    slots: list[WorkScheduleTimeSlot] = Field(min_length=1)


class WorkSchedulePeriod(BaseModel):
    valid_from: date
    valid_to: date | None = None
    blocks: list[WorkScheduleDayBlock] = Field(min_length=1)

    @model_validator(mode="after")
    def check_dates(self) -> WorkSchedulePeriod:
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("La fecha fin debe ser posterior o igual a la de inicio")
        return self


def _time_str(value: time) -> str:
    return value.strftime("%H:%M:%S")


def _normalize_day_block(raw: dict) -> dict:
    if raw.get("slots"):
        return {
            "work_days": raw["work_days"],
            "slots": [
                {
                    "work_start_time": s.get("work_start_time"),
                    "work_end_time": s.get("work_end_time"),
                    "break_minutes": s.get("break_minutes", 0),
                }
                for s in raw["slots"]
            ],
        }
    return {
        "work_days": raw["work_days"],
        "slots": [
            {
                "work_start_time": raw.get("work_start_time", "09:00:00"),
                "work_end_time": raw.get("work_end_time", "18:00:00"),
                "break_minutes": raw.get("break_minutes", 0),
            }
        ],
    }


def period_from_legacy_blocks(blocks: list[dict]) -> dict:
    today = date.today().isoformat()
    return {
        "valid_from": today,
        "valid_to": None,
        "blocks": [_normalize_day_block(b) for b in blocks],
    }


def blocks_from_legacy(
    work_days: list[int] | None,
    work_start_time: time | None,
    work_end_time: time | None,
    break_minutes: int = 0,
) -> list[dict]:
    days = work_days or [0, 1, 2, 3, 4]
    start = work_start_time or time(9, 0)
    end = work_end_time or time(18, 0)
    return [
        {
            "work_days": days,
            "slots": [
                {
                    "work_start_time": _time_str(start),
                    "work_end_time": _time_str(end),
                    "break_minutes": break_minutes,
                }
            ],
        }
    ]


def validate_periods(periods: list[WorkSchedulePeriod]) -> None:
    if not periods:
        raise ValueError("Añade al menos un periodo de horario")

    for pi, period in enumerate(periods):
        seen_days: set[int] = set()
        for block in period.blocks:
            for day in block.work_days:
                if day < 0 or day > 6:
                    raise ValueError(
                        "Día inválido en el horario (0=lunes … 6=domingo)"
                    )
                if day in seen_days:
                    raise ValueError(
                        f"En el periodo {pi + 1}, un mismo día no puede repetirse en varios bloques"
                    )
                seen_days.add(day)
            for slot in block.slots:
                if slot.work_start_time >= slot.work_end_time:
                    raise ValueError(
                        "Cada franja horaria debe tener inicio anterior al fin"
                    )

    sorted_periods = sorted(periods, key=lambda p: p.valid_from)
    for i in range(len(sorted_periods) - 1):
        a, b = sorted_periods[i], sorted_periods[i + 1]
        a_end = a.valid_to or date.max
        if b.valid_from <= a_end:
            raise ValueError(
                "Los periodos de horario no pueden solaparse en fechas"
            )


def _flatten_legacy_from_periods(periods: list[WorkSchedulePeriod]) -> dict:
    """Primer bloque del primer periodo → columnas legacy."""
    first_block = periods[0].blocks[0]
    first_slot = first_block.slots[0]
    return {
        "work_days": first_block.work_days,
        "work_start_time": first_slot.work_start_time,
        "work_end_time": first_slot.work_end_time,
        "work_schedule_blocks": [
            {
                "work_days": b.work_days,
                "work_start_time": _time_str(b.slots[0].work_start_time),
                "work_end_time": _time_str(b.slots[0].work_end_time),
                "break_minutes": b.slots[0].break_minutes,
            }
            for b in periods[0].blocks
        ],
    }


def normalize_employee_schedule(payload: dict) -> dict:
    """Rellena work_schedule_periods y campos legacy."""
    if payload.get("rotating_shift"):
        payload["work_schedule_periods"] = []
        payload["work_schedule_blocks"] = []
        payload["work_days"] = []
        payload["work_start_time"] = None
        payload["work_end_time"] = None
        wh = payload.get("weekly_hours")
        if wh is not None and wh <= 0:
            raise ValueError("Las horas semanales deben ser mayores que 0")
        return payload

    payload["weekly_hours"] = None

    periods_raw = payload.pop("work_schedule_periods", None)
    blocks_raw = payload.pop("work_schedule_blocks", None)
    legacy_days = payload.get("work_days")
    legacy_start = payload.get("work_start_time")
    legacy_end = payload.get("work_end_time")

    if periods_raw is not None:
        normalized_periods: list[dict] = []
        for p in periods_raw:
            blocks = [_normalize_day_block(b) for b in p.get("blocks", [])]
            normalized_periods.append(
                {
                    "valid_from": p["valid_from"],
                    "valid_to": p.get("valid_to"),
                    "blocks": blocks,
                }
            )
        periods = [WorkSchedulePeriod.model_validate(p) for p in normalized_periods]
        validate_periods(periods)
        serialized = [p.model_dump(mode="json") for p in periods]
        payload["work_schedule_periods"] = serialized
        payload.update(_flatten_legacy_from_periods(periods))
    elif blocks_raw is not None:
        period = period_from_legacy_blocks(blocks_raw)
        periods = [WorkSchedulePeriod.model_validate(period)]
        validate_periods(periods)
        payload["work_schedule_periods"] = [periods[0].model_dump(mode="json")]
        payload.update(_flatten_legacy_from_periods(periods))
    elif legacy_days is not None or legacy_start or legacy_end:
        legacy_blocks = blocks_from_legacy(legacy_days, legacy_start, legacy_end)
        period = period_from_legacy_blocks(legacy_blocks)
        periods = [WorkSchedulePeriod.model_validate(period)]
        payload["work_schedule_periods"] = [periods[0].model_dump(mode="json")]
        payload["work_schedule_blocks"] = legacy_blocks

    return payload


def parse_schedule_time(value: str | time | None) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    parts = str(value).strip().split(":")
    if len(parts) < 2:
        return None
    return time(int(parts[0]), int(parts[1]))


def active_period_for_date(employee: Employee, on_date: date) -> dict | None:
    periods = employee.work_schedule_periods or []
    if not periods:
        return None
    candidates: list[dict] = []
    for raw in periods:
        vf = date.fromisoformat(str(raw["valid_from"]))
        vt_raw = raw.get("valid_to")
        vt = date.fromisoformat(str(vt_raw)) if vt_raw else None
        if vf <= on_date and (vt is None or on_date <= vt):
            candidates.append(raw)
    if not candidates:
        return None
    return max(candidates, key=lambda p: date.fromisoformat(str(p["valid_from"])))


def slots_for_day(employee: Employee, on_date: date) -> list[tuple[time, time]]:
    """Franjas horarias del día (inicio, fin). Vacío si no trabaja ese día."""
    weekday = on_date.weekday()
    period = active_period_for_date(employee, on_date)
    if period:
        slots: list[tuple[time, time]] = []
        for block in period.get("blocks") or []:
            if weekday not in (block.get("work_days") or []):
                continue
            for slot in block.get("slots") or []:
                start = parse_schedule_time(slot.get("work_start_time"))
                end = parse_schedule_time(slot.get("work_end_time"))
                if start and end and start < end:
                    slots.append((start, end))
        return slots

    days = employee.work_days or []
    if weekday in days and employee.work_start_time and employee.work_end_time:
        if employee.work_start_time < employee.work_end_time:
            return [(employee.work_start_time, employee.work_end_time)]
    return []


def is_work_day(employee: Employee, on_date: date) -> bool:
    return bool(slots_for_day(employee, on_date))


def is_within_working_hours(employee: Employee, at: datetime) -> bool:
    """True si `at` cae dentro de alguna franja laboral del día."""
    current = at.time()
    for start, end in slots_for_day(employee, at.date()):
        if start <= current <= end:
            return True
    return False


def earliest_work_start(employee: Employee, on_date: date) -> time | None:
    slots = slots_for_day(employee, on_date)
    if not slots:
        return None
    return min(s[0] for s in slots)
