from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db import UserRecord, VMRecord
from app.models import Role
from app.security import hash_password

DEMO_VMS = [
    ("web-01", 2, 4, 80, "Ubuntu 24.04", "running"),
    ("web-02", 2, 4, 80, "Ubuntu 24.04", "running"),
    ("api-01", 4, 8, 120, "Debian 12", "running"),
    ("db-01", 8, 32, 500, "Rocky Linux 9", "running"),
    ("cache-01", 2, 16, 40, "Debian 12", "running"),
    ("worker-01", 4, 8, 80, "Ubuntu 22.04", "stopped"),
    ("monitor-01", 2, 4, 120, "Ubuntu 24.04", "running"),
    ("backup-01", 2, 8, 1000, "Rocky Linux 9", "stopped"),
    ("ci-runner-01", 8, 16, 200, "Ubuntu 22.04", "paused"),
    ("win-app-01", 4, 16, 160, "Windows Server 2022", "error"),
]


def seed(sessions: sessionmaker[Session], settings: Settings) -> None:
    """Crea los usuarios iniciales si no hay ninguno y, opcionalmente, VMs de ejemplo."""
    with sessions() as db:
        if not db.scalar(select(func.count()).select_from(UserRecord)):
            db.add(UserRecord(email=settings.admin_email, name="Administrador", hashed_password=hash_password(settings.admin_password), role=Role.admin.value))
            if settings.seed_demo_data:
                db.add(UserRecord(email=settings.client_email, name="Cliente demo", hashed_password=hash_password(settings.client_password), role=Role.client.value))
        if settings.seed_demo_data and not db.scalar(select(func.count()).select_from(VMRecord)):
            db.add_all(VMRecord(name=n, cores=c, ram=r, disk=d, os=o, status=s) for n, c, r, d, o, s in DEMO_VMS)
        db.commit()
