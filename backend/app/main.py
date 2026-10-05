import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import DEV_JWT_SECRET, Settings, get_settings
from app.db import init_db, make_engine, make_session_factory
from app.middleware import JWTCookieMiddleware
from app.realtime import ConnectionManager
from app.realtime import router as realtime_router
from app.routers import auth, users, vms
from app.seed import seed


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.jwt_secret == DEV_JWT_SECRET:
            logging.getLogger("uvicorn.error").warning("VMD_JWT_SECRET no está configurado: usando el secreto de desarrollo")
        engine = make_engine(settings.database_url)
        init_db(engine)
        app.state.sessions = make_session_factory(engine)
        seed(app.state.sessions, settings)
        yield
        engine.dispose()

    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.realtime = ConnectionManager()

    # Orden: el último middleware añadido es el más externo. CORS va por fuera para que
    # también las respuestas 401 del middleware JWT lleven las cabeceras CORS.
    app.add_middleware(JWTCookieMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,  # necesario para que el navegador envíe la cookie
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(vms.router)
    app.include_router(realtime_router)
    return app


app = create_app()
