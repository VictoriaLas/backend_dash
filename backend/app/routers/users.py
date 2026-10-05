from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.db import UserRecord
from app.deps import AdminUser, DbDep
from app.models import User, UserCreate
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[User])
def list_users(_: AdminUser, db: DbDep) -> list[UserRecord]:
    return list(db.scalars(select(UserRecord).order_by(UserRecord.email)))


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, _: AdminUser, db: DbDep) -> UserRecord:
    if db.scalar(select(UserRecord.id).where(func.lower(UserRecord.email) == data.email.lower())):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese email")
    user = UserRecord(email=data.email.lower(), name=data.name, hashed_password=hash_password(data.password), role=data.role.value)
    db.add(user)
    db.commit()
    return user
