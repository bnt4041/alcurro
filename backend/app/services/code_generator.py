"""Generación automática de códigos/referencias secuenciales."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.models.models import Employee
from app.models.organization import Department, WorkCenter

_CODE_SUFFIX = re.compile(r"^([A-Z]+)-(\d+)$", re.IGNORECASE)


def _max_suffix(codes: list[str], prefix: str) -> int:
    prefix_upper = prefix.upper()
    max_num = 0
    for raw in codes:
        if not raw:
            continue
        m = _CODE_SUFFIX.match(raw.strip())
        if m and m.group(1).upper() == prefix_upper:
            max_num = max(max_num, int(m.group(2)))
    return max_num


def _format_code(prefix: str, num: int) -> str:
    return f"{prefix.upper()}-{num:03d}"


def next_work_center_code(session: Session, company_id: UUID) -> str:
    rows = session.exec(
        select(WorkCenter.code).where(WorkCenter.company_id == company_id)
    ).all()
    n = _max_suffix(list(rows), "CEN") + 1
    return _format_code("CEN", n)


def next_department_code(session: Session, work_center_id: UUID) -> str:
    rows = session.exec(
        select(Department.code).where(Department.work_center_id == work_center_id)
    ).all()
    n = _max_suffix(list(rows), "DEP") + 1
    return _format_code("DEP", n)


def next_employee_code(session: Session, company_id: UUID) -> str:
    rows = session.exec(
        select(Employee.employee_code).where(Employee.company_id == company_id)
    ).all()
    n = _max_suffix(list(rows), "EMP") + 1
    return _format_code("EMP", n)
