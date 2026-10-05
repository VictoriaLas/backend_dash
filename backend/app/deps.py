from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import UserRecord, get_db
from app.models import Role

DbDep = Annotated[Session, Depends(get_db)]


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


def get_current_user(request: Request, db: DbDep) -> UserRecord:
    payload = getattr(request.state, "jwt", None)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    user = db.get(UserRecord, int(payload["sub"]))
    # El usuario pudo ser borrado o desactivado después de emitir el token
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no válido")
    return user


CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> UserRecord:
    if user.role != Role.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un Administrador puede hacer esto")
    return user


AdminUser = Annotated[UserRecord, Depends(require_admin)]
