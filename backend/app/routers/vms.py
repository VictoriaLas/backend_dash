import time
from collections import Counter
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import VMRecord
from app.deps import AdminUser, CurrentUser, DbDep
from app.models import VM, DashboardSummary, VMCreate, VMMetrics, VMStatus, VMUpdate
from app.realtime import make_event
from app.simulation import simulate_series

router = APIRouter(tags=["vms"])


def _get_or_404(db: Session, vm_id: int) -> VMRecord:
    vm = db.get(VMRecord, vm_id)
    if vm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"VM {vm_id} no encontrada")
    return vm


def _ensure_unique_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    query = select(VMRecord.id).where(func.lower(VMRecord.name) == name.lower())
    if exclude_id is not None:
        query = query.where(VMRecord.id != exclude_id)
    if db.scalar(query):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Ya existe una VM llamada '{name}'")


def _as_json(vm: VMRecord) -> dict:
    return VM.model_validate(vm).model_dump(mode="json")


def _notify(request: Request, background: BackgroundTasks, event: dict) -> None:
    # Se envía después de responder, para no retrasar la petición del administrador
    background.add_task(request.app.state.realtime.broadcast, event)


# --- Lectura: Administrador y Cliente ----------------------------------------------


@router.get("/vms", response_model=list[VM])
def list_vms(_: CurrentUser, db: DbDep, status: VMStatus | None = None, search: str | None = None) -> list[VMRecord]:
    query = select(VMRecord).order_by(VMRecord.name)
    if status:
        query = query.where(VMRecord.status == status.value)
    if search:
        like = f"%{search.lower()}%"
        query = query.where(func.lower(VMRecord.name).like(like) | func.lower(VMRecord.os).like(like))
    return list(db.scalars(query))


@router.get("/vms/{vm_id}", response_model=VM)
def get_vm(vm_id: int, _: CurrentUser, db: DbDep) -> VMRecord:
    return _get_or_404(db, vm_id)


@router.get("/vms/{vm_id}/metrics", response_model=VMMetrics)
def get_vm_metrics(vm_id: int, _: CurrentUser, db: DbDep, range: Literal["1h", "6h", "24h", "7d"] = "1h") -> VMMetrics:
    vm = _get_or_404(db, vm_id)
    step, points = simulate_series(vm.id, VMStatus(vm.status), range, time.time())
    return VMMetrics(vm_id=vm.id, range=range, step_seconds=step, points=points)


@router.get("/summary", response_model=DashboardSummary)
def summary(_: CurrentUser, db: DbDep) -> DashboardSummary:
    vms = list(db.scalars(select(VMRecord)))
    running = [vm for vm in vms if vm.status == VMStatus.running.value]
    return DashboardSummary(
        total_vms=len(vms),
        by_status={s: sum(1 for vm in vms if vm.status == s.value) for s in VMStatus},
        total_cores=sum(vm.cores for vm in vms),
        total_ram=sum(vm.ram for vm in vms),
        total_disk=sum(vm.disk for vm in vms),
        running_cores=sum(vm.cores for vm in running),
        running_ram=sum(vm.ram for vm in running),
        running_disk=sum(vm.disk for vm in running),
        by_os=dict(Counter(vm.os for vm in vms).most_common()),
    )


# --- Escritura: solo Administrador -------------------------------------------------


@router.post("/vms", response_model=VM, status_code=status.HTTP_201_CREATED)
def create_vm(data: VMCreate, admin: AdminUser, db: DbDep, request: Request, background: BackgroundTasks) -> VMRecord:
    _ensure_unique_name(db, data.name)
    vm = VMRecord(**data.model_dump(exclude={"status"}), status=data.status.value)
    db.add(vm)
    db.commit()
    _notify(request, background, make_event("vm.created", vm=_as_json(vm), actor=admin.email))
    return vm


@router.put("/vms/{vm_id}", response_model=VM)
def update_vm(vm_id: int, data: VMUpdate, admin: AdminUser, db: DbDep, request: Request, background: BackgroundTasks) -> VMRecord:
    vm = _get_or_404(db, vm_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in changes:
        _ensure_unique_name(db, changes["name"], exclude_id=vm_id)
    if "status" in changes:
        changes["status"] = changes["status"].value
    for field, value in changes.items():
        setattr(vm, field, value)
    db.commit()
    _notify(request, background, make_event("vm.updated", vm=_as_json(vm), actor=admin.email))
    return vm


@router.delete("/vms/{vm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vm(vm_id: int, admin: AdminUser, db: DbDep, request: Request, background: BackgroundTasks) -> Response:
    db.delete(_get_or_404(db, vm_id))
    db.commit()
    _notify(request, background, make_event("vm.deleted", vm_id=vm_id, actor=admin.email))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
