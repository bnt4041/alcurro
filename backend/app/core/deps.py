from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.security import can_access_panel, decode_access_token
from app.database import get_session
from app.models.models import Employee

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> Employee:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") == "platform":
            raise ValueError("platform token")
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from None
    user = session.get(Employee, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no válido")
    if not can_access_panel(session, user, tenant_id):
        raise HTTPException(status_code=403, detail="Sin acceso al panel")
    return user
