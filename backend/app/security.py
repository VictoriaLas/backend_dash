from datetime import timedelta

import bcrypt
import jwt
from fastapi import Response

from app.config import Settings
from app.db import UserRecord, utcnow

# Hash fijo para comparar cuando el email no existe, así el login tarda lo mismo
# y no revela qué emails están registrados.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    return bcrypt.checkpw(password.encode(), (hashed or _DUMMY_HASH).encode()) and hashed is not None


def create_access_token(user: UserRecord, settings: Settings) -> str:
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict:
    """Lanza jwt.PyJWTError si el token es inválido, está manipulado o ha expirado."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], options={"require": ["exp", "sub"]})


def set_auth_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,  # JavaScript no puede leerla (protege frente a XSS)
        secure=settings.cookie_secure,  # solo viaja por HTTPS (y http://localhost)
        samesite=settings.cookie_samesite,  # no se envía en peticiones de otros sitios (CSRF)
        domain=settings.cookie_domain,
        path="/",
    )


def clear_auth_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )
