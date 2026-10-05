import pytest

NEW_VM = {"name": "nueva-vm", "cores": 4, "ram": 8, "disk": 100, "os": "Ubuntu 24.04", "status": "running"}


def test_both_roles_list_vms(admin, client):
    for c in (admin, client):
        vms = c.get("/vms").json()
        assert len(vms) == 10
        assert set(vms[0]) == {"id", "name", "cores", "ram", "disk", "os", "status", "created_at", "updated_at"}


def test_filters(admin):
    assert all(vm["status"] == "running" for vm in admin.get("/vms", params={"status": "running"}).json())
    assert {vm["name"] for vm in admin.get("/vms", params={"search": "WEB"}).json()} == {"web-01", "web-02"}


def test_admin_crud(admin):
    r = admin.post("/vms", json=NEW_VM)
    assert r.status_code == 201
    vm = r.json()
    assert {k: vm[k] for k in NEW_VM} == NEW_VM

    r = admin.put(f"/vms/{vm['id']}", json={"ram": 16, "status": "stopped"})
    assert r.status_code == 200
    assert r.json()["ram"] == 16 and r.json()["status"] == "stopped" and r.json()["cores"] == 4

    assert admin.get(f"/vms/{vm['id']}").json()["ram"] == 16
    assert admin.delete(f"/vms/{vm['id']}").status_code == 204
    assert admin.get(f"/vms/{vm['id']}").status_code == 404


@pytest.mark.parametrize(
    "method,path,body",
    [("post", "/vms", NEW_VM), ("put", "/vms/1", {"ram": 2}), ("delete", "/vms/1", None)],
)
def test_client_cannot_write(client, method, path, body):
    kwargs = {"json": body} if body else {}
    r = getattr(client, method)(path, **kwargs)
    assert r.status_code == 403 and r.json()["detail"] == "Solo un Administrador puede hacer esto"
    assert len(client.get("/vms").json()) == 10


def test_duplicate_name(admin):
    assert admin.post("/vms", json={**NEW_VM, "name": "WEB-01"}).status_code == 409
    assert admin.put("/vms/2", json={"name": "web-01"}).status_code == 409


@pytest.mark.parametrize(
    "field,value",
    [("cores", 0), ("ram", -1), ("disk", 0), ("status", "on"), ("name", "  "), ("name", "a"), ("name", "-web"), ("name", "con espacios"), ("name", "x" * 64)],
)
def test_validation(admin, field, value):
    assert admin.post("/vms", json={**NEW_VM, field: value}).status_code == 422


def test_put_validates_name(admin):
    assert admin.put("/vms/1", json={"name": "nombre inválido"}).status_code == 422
    assert admin.put("/vms/1", json={"name": " web-renombrada "}).json()["name"] == "web-renombrada"


def test_missing_vm(admin):
    assert admin.put("/vms/999", json={"ram": 2}).status_code == 404
    assert admin.delete("/vms/999").status_code == 404


def test_summary_and_metrics(client):
    s = client.get("/summary").json()
    assert s["total_vms"] == 10 and sum(s["by_status"].values()) == 10
    running = [vm for vm in client.get("/vms").json() if vm["status"] == "running"]
    assert s["running_cores"] == sum(vm["cores"] for vm in running)
    assert s["running_disk"] == sum(vm["disk"] for vm in running)
    m = client.get("/vms/1/metrics", params={"range": "24h"}).json()
    assert m["simulated"] is True and len(m["points"]) == 97
