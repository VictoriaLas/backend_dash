import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

ADMIN = {"email": "admin@example.com", "password": "admin-pass"}
CLIENT = {"email": "cliente@example.com", "password": "cliente-pass"}


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        admin_email=ADMIN["email"],
        admin_password=ADMIN["password"],
        client_email=CLIENT["email"],
        client_password=CLIENT["password"],
        _env_file=None,
    )


@pytest.fixture
def anon(settings):
    # https: el navegador (y httpx) solo reenvían cookies Secure por HTTPS
    with TestClient(create_app(settings), base_url="https://testserver") as c:
        yield c


def _login(c: TestClient, creds: dict) -> TestClient:
    r = c.post("/login", json=creds)
    assert r.status_code == 200, r.text
    return c


@pytest.fixture
def admin(anon):
    return _login(anon, ADMIN)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), base_url="https://testserver") as c:
        yield _login(c, CLIENT)
