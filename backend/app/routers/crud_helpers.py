from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, SQLModel

T = TypeVar("T", bound=SQLModel)


def get_or_404(session: Session, model: type[T], item_id: UUID) -> T:
    item = session.get(model, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"{model.__name__} no encontrado")
    return item
