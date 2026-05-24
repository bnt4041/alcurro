"""Validación y normalización de horarios de empleado."""

from __future__ import annotations

from datetime import time

from pydantic import BaseModel, Field


class WorkScheduleBlock(BaseModel):
    work_days: list[int] = Field(min_length=1)
    work_start_time: time
    work_end_time: time
    break_minutes: int = Field(default=0, ge=0, le=480)


def _time_str(value: time) -> str:
    return value.strftime("%H:%M:%S")


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
            "work_start_time": _time_str(start),
            "work_end_time": _time_str(end),
            "break_minutes": break_minutes,
        }
    ]


def validate_schedule_blocks(blocks: list[WorkScheduleBlock]) -> None:
    if not blocks:
        raise ValueError("Añade al menos un bloque de horario")
    seen: set[int] = set()
    for block in blocks:
        for day in block.work_days:
            if day < 0 or day > 6:
                raise ValueError("Día inválido en el horario (0=lunes … 6=domingo)")
            if day in seen:
                raise ValueError("Un mismo día no puede repetirse en varios bloques")
            seen.add(day)
        if block.work_start_time >= block.work_end_time:
            raise ValueError("La hora de inicio debe ser anterior a la de fin")


def normalize_employee_schedule(payload: dict) -> dict:
    """Rellena work_schedule_blocks y campos legacy coherentes."""
    blocks_raw = payload.pop("work_schedule_blocks", None)
    legacy_days = payload.get("work_days")
    legacy_start = payload.get("work_start_time")
    legacy_end = payload.get("work_end_time")

    if blocks_raw is not None:
        blocks = [WorkScheduleBlock.model_validate(b) for b in blocks_raw]
        validate_schedule_blocks(blocks)
        serialized = [b.model_dump(mode="json") for b in blocks]
        payload["work_schedule_blocks"] = serialized
        first = blocks[0]
        payload["work_days"] = first.work_days
        payload["work_start_time"] = first.work_start_time
        payload["work_end_time"] = first.work_end_time
    elif legacy_days is not None or legacy_start or legacy_end:
        payload["work_schedule_blocks"] = blocks_from_legacy(
            legacy_days, legacy_start, legacy_end
        )
    return payload
