from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.public.carrier_portal import router as carrier_router
from app.api.public.tracking import router as tracking_router
from app.api.v1.router import router as v1_router
from app.config import get_settings


class _DebugPathFilter(logging.Filter):
    """Suppress uvicorn access logs for /__debug__* paths."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "/__debug__" not in msg


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

    # ── Debug Inspector (DEBUG mode only) ────────────────────────────
    if settings.DEBUG:
        from app.debug_inspector import (
            RequestInspectorMiddleware,
            debug_ui_html,
            get_entries,
        )
        from starlette.responses import JSONResponse

        app.add_middleware(RequestInspectorMiddleware)

        # Silence uvicorn access logs for /__debug__* endpoints
        for _name in ("uvicorn.access", "uvicorn"):
            _logger = logging.getLogger(_name)
            _logger.addFilter(_DebugPathFilter())

        @app.get("/__debug__", include_in_schema=False)
        async def debug_ui():
            return debug_ui_html()

        @app.get("/__debug__/json", include_in_schema=False)
        async def debug_json():
            return JSONResponse(content=get_entries())

    return app


app = create_app()
