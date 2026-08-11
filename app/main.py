from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.v1.router import router as v1_router
from app.api.public.tracking import router as tracking_router
from app.api.public.carrier_portal import router as carrier_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize DB pools, Redis, etc.
    yield
    # Shutdown: close pools, cleanup


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Phase 1: restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(v1_router, prefix="/api/v1")
    app.include_router(tracking_router)
    app.include_router(carrier_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
