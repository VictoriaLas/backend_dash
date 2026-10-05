import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app
from tests.conftest import ADMIN, CLIENT

# wss: la cookie es Secure, así que (como en el navegador) solo viaja por conexiones cifradas
WS_URL = "wss://testserver/ws"


@pytest.fixture
def two_users(settings):
    """Un Administrador y un Cliente conectados a la misma API (cada uno con su cookie)."""
    app = create_app(settings)
    with TestClient(app, base_url="https://testserver") as admin, TestClient(app, base_url="https://testserver") as client:
        admin.post("/login", json=ADMIN)
        client.post("/login", json=CLIENT)
        yield admin, client


def test_ws_requires_cookie(anon):
    with pytest.raises(WebSocketDisconnect) as exc:
        with anon.websocket_connect(WS_URL) as ws:
            ws.receive_json()
    assert exc.value.code == 1008


def test_ws_rejects_foreign_origin(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(WS_URL, headers={"origin": "https://sitio-malicioso.com"}) as ws:
            ws.receive_json()
    assert exc.value.code == 1008


def test_ws_accepts_frontend_origin(client):
    with client.websocket_connect(WS_URL, headers={"origin": "http://localhost:4200"}) as ws:
        ws.send_text("ping")
        assert ws.receive_json() == {"type": "pong"}


def test_admin_change_reaches_connected_client(two_users):
    admin, client = two_users
    with client.websocket_connect(WS_URL) as ws:
        r = admin.put("/vms/6", json={"status": "running"})
        assert r.status_code == 200
        event = ws.receive_json()
        assert event["type"] == "vm.updated" and event["id"] == 6
        assert event["vm"]["status"] == "running" and event["actor"] == ADMIN["email"]

        created = admin.post("/vms", json={"name": "rt-01", "cores": 1, "ram": 1, "disk": 10, "os": "Debian 12"}).json()
        event = ws.receive_json()
        assert event["type"] == "vm.created" and event["vm"]["name"] == "rt-01"

        admin.delete(f"/vms/{created['id']}")
        event = ws.receive_json()
        assert event == {**event, "type": "vm.deleted", "id": created["id"], "vm": None}


def test_failed_write_sends_no_event(two_users):
    admin, client = two_users
    with client.websocket_connect(WS_URL) as ws:
        assert client.put("/vms/1", json={"status": "stopped"}).status_code == 403
        assert admin.put("/vms/999", json={"status": "stopped"}).status_code == 404
        admin.put("/vms/2", json={"cores": 3})
        assert ws.receive_json()["id"] == 2  # el primer evento recibido es el de la escritura válida
