"""Tiempo real: los cambios de VMs se envían por WebSocket a todos los clientes conectados."""
import logging

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import UserRecord, utcnow
from app.security import decode_access_token

log = logging.getLogger("uvicorn.error")
router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, float] = {}  # socket -> expiración del JWT (epoch)

    def add(self, ws: WebSocket, token_exp: float) -> None:
        self._connections[ws] = token_exp

    def remove(self, ws: WebSocket) -> None:
        self._connections.pop(ws, None)

    @property
    def count(self) -> int:
        return len(self._connections)

    async def broadcast(self, event: dict) -> None:
        now = utcnow().timestamp()
        for ws, exp in list(self._connections.items()):
            if exp <= now:
                # La sesión caducó: el cliente debe volver a hacer login
                self.remove(ws)
                await _safe_close(ws, 4401, "La sesión ha expirado")
                continue
            try:
                await ws.send_json(event)
            except Exception:  # conexión rota
                self.remove(ws)


async def _safe_close(ws: WebSocket, code: int, reason: str) -> None:
    try:
        await ws.close(code=code, reason=reason)
    except Exception:
        pass


def _origin_allowed(ws: WebSocket, settings: Settings) -> bool:
    """Los WebSockets no pasan por CORS: comprobamos el Origin a mano para evitar
    Cross-Site WebSocket Hijacking (otra web abriendo el socket con la cookie del usuario)."""
    origin = ws.headers.get("origin")
    if origin is None:
        return True  # clientes que no son navegador (scripts, tests)
    same_origin = origin.split("://", 1)[-1] == ws.headers.get("host")
    return same_origin or origin in settings.cors_origins


@router.websocket("/ws")
async def vm_events(ws: WebSocket) -> None:
    settings: Settings = ws.app.state.settings
    sessions: sessionmaker = ws.app.state.sessions
    manager: ConnectionManager = ws.app.state.realtime

    # El middleware JWT solo actúa sobre HTTP, así que el socket valida la cookie aquí
    if not _origin_allowed(ws, settings):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Origen no permitido")
        return
    token = ws.cookies.get(settings.cookie_name)
    try:
        payload = decode_access_token(token or "", settings)
    except jwt.PyJWTError:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="No autenticado")
        return
    with sessions() as db:
        user = db.get(UserRecord, int(payload["sub"]))
    if user is None or not user.is_active:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Usuario no válido")
        return

    await ws.accept()
    manager.add(ws, float(payload["exp"]))
    try:
        while True:
            # El cliente no necesita enviar nada; esto mantiene la conexión y detecta el cierre
            if await ws.receive_text() == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.remove(ws)


def make_event(event_type: str, *, vm: dict | None = None, vm_id: int | None = None, actor: str) -> dict:
    return {"type": event_type, "vm": vm, "id": vm_id if vm is None else vm["id"], "actor": actor, "at": utcnow().isoformat()}


__all__ = ["ConnectionManager", "make_event", "router"]
