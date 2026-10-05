from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from app.db import UserRecord
from app.deps import CurrentUser, DbDep, SettingsDep
from app.models import LoginRequest, User
from app.security import clear_auth_cookie, create_access_token, set_auth_cookie, verify_password

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=User)
def login(data: LoginRequest, response: Response, db: DbDep, settings: SettingsDep) -> UserRecord:
    """Valida email y contraseña, guarda el JWT en una cookie HttpOnly y devuelve el usuario con su rol."""
    user = db.scalar(select(UserRecord).where(func.lower(UserRecord.email) == data.email.lower()))
    if not verify_password(data.password, user.hashed_password if user else None) or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos")
    set_auth_cookie(response, create_access_token(user, settings), settings)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, settings: SettingsDep) -> None:
    clear_auth_cookie(response, settings)


@router.get("/me", response_model=User)
def me(user: CurrentUser) -> UserRecord:
    """Permite al frontend saber si hay sesión (p. ej. al recargar la página) y con qué rol."""
    return user
