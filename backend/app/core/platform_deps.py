from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.security import decode_access_token
from app.database import get_session
from app.models.rbac import PlatformUser

bearer = HTTPBearer(auto_error=False)


def get_platform_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> PlatformUser:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "platform":
            raise ValueError("not platform")
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Token inválido") from None
    user = session.get(PlatformUser, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no válido")
    return user
