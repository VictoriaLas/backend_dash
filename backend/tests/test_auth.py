from datetime import timedelta

import jwt
import pytest

from app.db import utcnow
from tests.conftest import ADMIN, CLIENT


def test_login_sets_httponly_cookie_and_returns_only_user(anon):
    r = anon.post("/login", json=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body == {"id": body["id"], "email": ADMIN["email"], "name": "Administrador", "role": "Administrador"}
    assert "token" not in r.text.lower()  # el JWT nunca va en el body

    cookie = r.headers["set-cookie"]
    assert cookie.startswith("access_token=")
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
    assert "Max-Age=3600" in cookie and "Path=/" in cookie


def test_client_role(anon):
    assert anon.post("/login", json=CLIENT).json()["role"] == "Cliente"


@pytest.mark.parametrize("creds", [{**ADMIN, "password": "mala"}, {"email": "nadie@example.com", "password": "x"}])
def test_bad_credentials(anon, creds):
    r = anon.post("/login", json=creds)
    assert r.status_code == 401 and "set-cookie" not in r.headers


def test_invalid_email_format(anon):
    assert anon.post("/login", json={"email": "no-es-email", "password": "x"}).status_code == 422


def test_me_uses_cookie(admin):
    assert admin.get("/me").json()["role"] == "Administrador"


def test_logout_clears_cookie(admin):
    r = admin.post("/logout")
    assert r.status_code == 204
    assert 'access_token=""' in r.headers["set-cookie"] and "Max-Age=0" in r.headers["set-cookie"]
    assert admin.get("/vms").status_code == 401


@pytest.mark.parametrize("path", ["/vms", "/vms/1", "/summary", "/me", "/users"])
def test_protected_without_cookie(anon, path):
    assert anon.get(path).status_code == 401


def test_bearer_header_is_not_accepted(admin):
    token = admin.cookies["access_token"]
    admin.cookies.clear()
    assert admin.get("/vms", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_tampered_and_expired_tokens(anon, settings):
    forged = jwt.encode({"sub": "1", "role": "Administrador", "exp": utcnow() + timedelta(minutes=5)}, "otro-secreto-de-al-menos-32-bytes!!", algorithm="HS256")
    anon.cookies.set("access_token", forged)
    assert anon.get("/vms").json()["detail"] == "Token inválido"

    expired = jwt.encode({"sub": "1", "role": "Administrador", "exp": utcnow() - timedelta(minutes=1)}, settings.jwt_secret, algorithm="HS256")
    anon.cookies.set("access_token", expired)
    assert anon.get("/vms").json()["detail"] == "La sesión ha expirado"


def test_role_comes_from_database_not_token(client, settings):
    """Un Cliente no puede escalar a Administrador aunque tenga un token con role=Administrador."""
    me = client.get("/me").json()
    token = jwt.encode({"sub": str(me["id"]), "role": "Administrador", "exp": utcnow() + timedelta(minutes=5)}, settings.jwt_secret, algorithm="HS256")
    client.cookies.set("access_token", token)
    assert client.post("/vms", json={"name": "x", "cores": 1, "ram": 1, "disk": 10, "os": "Debian"}).status_code == 403


def test_cors_allows_credentials(anon):
    r = anon.options("/vms", headers={"Origin": "http://localhost:4200", "Access-Control-Request-Method": "GET"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:4200"
    assert r.headers["access-control-allow-credentials"] == "true"
    # Las respuestas 401 del middleware también llevan CORS, para que el frontend pueda leerlas
    r = anon.get("/vms", headers={"Origin": "http://localhost:4200"})
    assert r.status_code == 401 and r.headers["access-control-allow-origin"] == "http://localhost:4200"


def test_admin_manages_users(admin):
    r = admin.post("/users", json={"email": "Nuevo@Example.com", "name": "Nuevo", "password": "secreta123"})
    assert r.status_code == 201 and r.json()["role"] == "Cliente"
    assert admin.post("/users", json={"email": "nuevo@example.com", "name": "x", "password": "secreta123"}).status_code == 409
    assert len(admin.get("/users").json()) == 3


def test_client_cannot_manage_users(client):
    assert client.get("/users").status_code == 403
