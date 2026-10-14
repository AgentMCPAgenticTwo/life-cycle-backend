"""FastAPI entry point.

Wires the things that are invisible until integration fails: CORS (before anything else),
the header-auth stub, migrations-at-startup, and one shared error body.
"""
import asyncio
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import (
    approval_matrix,
    approvals,
    auth,
    clauses,
    contract_lifecycle,
    contracts,
    contracts_third_party_paper,
    counterparties,
    esignature_settings,
    lifecycle_clauses,
    lifecycle_negotiation,
    lookups,
    settings_approval_rules,
    settings_audit_log,
    settings_integrations,
    settings_notifications,
    settings_users,
    signers,
    signing_sessions,
    templates,
    tracker_bottleneck,
    tracker_bottleneck_thresholds,
    tracker_cycle_time,
    tracker_export,
    tracker_ownership,
    tracker_turnaround,
)
from app.services import scheduled_notifications

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def _run_migrations() -> None:
    """Apply pending migrations at startup -- never auto-create the schema in a production
    path (see CLAUDE.md's "Database and migrations"). No-op when no DATABASE_URL is
    configured, so the app still boots (e.g. for the health check) without a database.
    """
    if not settings.database_url:
        return
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _run_migrations()
    # UC5/UC7/UC9 reminders and renewal alerts fire because a date passed, not because anyone
    # called an endpoint. There is no scheduler dependency in this repository, so the sweep
    # runs in-process; set NOTIFICATION_SWEEP_INTERVAL_SECONDS=0 to turn it off and drive
    # `scheduled_notifications.run_all` from outside instead.
    sweep: asyncio.Task | None = None
    if settings.database_url and settings.notification_sweep_interval_seconds > 0:
        sweep = asyncio.create_task(scheduled_notifications.sweep_loop())
    try:
        yield
    finally:
        if sweep is not None:
            sweep.cancel()
            with suppress(asyncio.CancelledError):
                await sweep


app = FastAPI(title="API", version="1.0", lifespan=lifespan)

# CORS first.
origins = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-User-Role", "X-User-Id"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    """One shared shape for every non-2xx response: {"error", "details"}."""
    details = getattr(exc, "details", [])
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "details": details})


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError):
    details = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(
        status_code=400, content={"error": "validation failed", "details": details}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, _exc: Exception):
    """Catch-all: an unexpected error is still one shared body, never a raw traceback."""
    return JSONResponse(status_code=500, content={"error": "internal server error", "details": []})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Feature routers are included here as modules are implemented.
app.include_router(approval_matrix.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
# The frontend contract spells the auth routes as bare `/auth/login`, `/auth/refresh`, ...
# while every other route it lists carries the `/api/v1` base path. Serving both spellings
# costs one extra mount and removes the chance of a 404 on the login call itself.
app.include_router(auth.router)
app.include_router(clauses.router, prefix="/api/v1")
app.include_router(contracts.router, prefix="/api/v1")
app.include_router(contract_lifecycle.router, prefix="/api/v1")
app.include_router(contract_lifecycle.folder_tags_router, prefix="/api/v1")
app.include_router(contracts_third_party_paper.router, prefix="/api/v1")
app.include_router(counterparties.router, prefix="/api/v1")
app.include_router(esignature_settings.router, prefix="/api/v1")
app.include_router(lifecycle_clauses.router, prefix="/api/v1")
app.include_router(lifecycle_negotiation.router, prefix="/api/v1")
app.include_router(lifecycle_negotiation.external_router, prefix="/api/v1")
app.include_router(lookups.router, prefix="/api/v1")
app.include_router(settings_approval_rules.router, prefix="/api/v1")
app.include_router(settings_audit_log.router, prefix="/api/v1")
app.include_router(settings_integrations.router, prefix="/api/v1")
app.include_router(settings_notifications.router, prefix="/api/v1")
app.include_router(settings_users.router, prefix="/api/v1")
app.include_router(signers.router, prefix="/api/v1")
app.include_router(signing_sessions.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(tracker_bottleneck.router, prefix="/api/v1")
app.include_router(tracker_bottleneck_thresholds.router, prefix="/api/v1")
app.include_router(tracker_cycle_time.router, prefix="/api/v1")
app.include_router(tracker_export.router, prefix="/api/v1")
app.include_router(tracker_ownership.router, prefix="/api/v1")
app.include_router(tracker_turnaround.router, prefix="/api/v1")
