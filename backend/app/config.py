from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-secret-change-me-in-production-0123456789"


class Settings(BaseSettings):
    """Configuración leída de variables de entorno (prefijo VMD_) o de un archivo .env."""

    model_config = SettingsConfigDict(env_prefix="VMD_", env_file=".env", extra="ignore")

    app_name: str = "VM Dashboard API"
    database_url: str = "sqlite:///./vm_dashboard.db"
    seed_demo_data: bool = True  # crea usuarios y VMs de ejemplo si la base de datos está vacía
    # Orígenes del frontend. Con cookies, CORS necesita orígenes explícitos (nunca "*")
    cors_origins: list[str] = ["http://localhost:4200", "http://localhost:5173", "http://localhost:3000"]

    # JWT. Cambia jwt_secret en producción (p. ej. `openssl rand -hex 32`).
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Cookie donde viaja el JWT
    cookie_name: str = "access_token"
    cookie_secure: bool = True  # los navegadores aceptan cookies Secure en http://localhost
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None

    # Usuarios iniciales (solo si no hay ninguno)
    admin_email: str = "admin@vmdashboard.com"
    admin_password: str = "admin123"
    client_email: str = "cliente@vmdashboard.com"
    client_password: str = "cliente123"


@lru_cache
def get_settings() -> Settings:
    return Settings()
