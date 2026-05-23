from sqlalchemy import or_
from sqlmodel import SQLModel


def ilike_filter(*columns, term: str | None):
    if not term or not term.strip():
        return None
    pattern = f"%{term.strip()}%"
    return or_(*[col.ilike(pattern) for col in columns])  # type: ignore[attr-defined]
