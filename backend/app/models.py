import re
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Role(str, Enum):
    admin = "Administrador"
    client = "Cliente"


class VMStatus(str, Enum):
    running = "running"
    stopped = "stopped"
    paused = "paused"
    error = "error"


# --- Autenticación ------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class User(BaseModel):
    """Lo que devuelve /login y /me: datos del usuario y su rol. Nunca el token."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: Role


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=72)  # bcrypt solo usa los primeros 72 bytes
    role: Role = Role.client


# --- VMs ----------------------------------------------------------------------------

# Nombre tipo hostname: empieza por letra o número; luego letras, números, punto, guion o guion bajo
VM_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,62}$")


def _clean_name(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip()
    if not VM_NAME_RE.fullmatch(v):
        raise ValueError("debe tener entre 2 y 63 caracteres, empezar por letra o número y usar solo letras, números, '.', '-' o '_'")
    return v


def _clean_os(v: str | None) -> str | None:
    if v is None:
        return v
    if not v.strip():
        raise ValueError("no puede estar vacío")
    return v.strip()


class VMCreate(BaseModel):
    name: str = Field(max_length=63)
    cores: int = Field(ge=1, le=256, description="Núcleos de CPU")
    ram: int = Field(ge=1, le=4096, description="Memoria RAM en GB")
    disk: int = Field(ge=1, le=65536, description="Disco en GB")
    os: str = Field(min_length=1, max_length=128)
    status: VMStatus = VMStatus.stopped

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        return _clean_name(v)

    @field_validator("os")
    @classmethod
    def validate_os(cls, v: str | None) -> str | None:
        return _clean_os(v)


class VMUpdate(BaseModel):
    """PUT /vms/{id}: se actualizan los campos enviados; los omitidos se mantienen."""

    name: str | None = Field(default=None, max_length=63)
    cores: int | None = Field(default=None, ge=1, le=256)
    ram: int | None = Field(default=None, ge=1, le=4096)
    disk: int | None = Field(default=None, ge=1, le=65536)
    os: str | None = Field(default=None, min_length=1, max_length=128)
    status: VMStatus | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        return _clean_name(v)

    @field_validator("os")
    @classmethod
    def validate_os(cls, v: str | None) -> str | None:
        return _clean_os(v)


class VM(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cores: int
    ram: int
    disk: int
    os: str
    status: VMStatus
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def as_utc(cls, v: datetime) -> datetime:
        # SQLite devuelve fechas sin zona horaria; se guardan siempre en UTC
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v


# --- Dashboard ----------------------------------------------------------------------


class DashboardSummary(BaseModel):
    total_vms: int
    by_status: dict[VMStatus, int]
    total_cores: int
    total_ram: int
    total_disk: int
    # Recursos asignados a las VMs activas (status = running), para la gráfica del dashboard
    running_cores: int
    running_ram: int
    running_disk: int
    by_os: dict[str, int]


class MetricPoint(BaseModel):
    timestamp: datetime
    cpu_percent: float
    ram_percent: float
    disk_percent: float


class VMMetrics(BaseModel):
    vm_id: int
    range: str
    step_seconds: int
    simulated: bool = True
    points: list[MetricPoint]
