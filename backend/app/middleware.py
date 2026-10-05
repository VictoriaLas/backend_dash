import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import Settings
from app.security import decode_access_token

# Rutas accesibles sin sesión
PUBLIC_PATHS = {"/login", "/logout", "/health", "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}


class JWTCookieMiddleware(BaseHTTPMiddleware):
    """Valida el JWT de la cookie HttpOnly en cada petición protegida.

    Si es válido deja el payload en `request.state.jwt`; si falta o no es válido responde 401.
    La autorización por rol se hace después, en cada endpoint (ver app/deps.py).
    """

    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        token = request.cookies.get(self.settings.cookie_name)
        if not token:
            return JSONResponse({"detail": "No autenticado"}, status_code=401)
        try:
            request.state.jwt = decode_access_token(token, self.settings)
        except jwt.ExpiredSignatureError:
            return JSONResponse({"detail": "La sesión ha expirado"}, status_code=401)
        except jwt.PyJWTError:
            return JSONResponse({"detail": "Token inválido"}, status_code=401)
        return await call_next(request)
