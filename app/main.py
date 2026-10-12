"""FastAPI entry point.

Wires the things that are invisible until integration fails: CORS (before anything else),
the header-auth stub, migrations-at-startup, and one shared error body.
"""
import os
from contextlib import asynccontextmanager
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
    clauses,
    contracts,
    contracts_third_party_paper,
    counterparties,
    esignature_settings,
    lifecycle_clauses,
    lifecycle_negotiation,
    lookups,
    signers,
    signing_sessions,
    templates,
)

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
    yield


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
    allow_headers=["Content-Type", "X-User-Role", "X-User-Id"],
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
app.include_router(clauses.router, prefix="/api/v1")
app.include_router(contracts.router, prefix="/api/v1")
app.include_router(contracts_third_party_paper.router, prefix="/api/v1")
app.include_router(counterparties.router, prefix="/api/v1")
app.include_router(esignature_settings.router, prefix="/api/v1")
app.include_router(lifecycle_clauses.router, prefix="/api/v1")
app.include_router(lifecycle_negotiation.router, prefix="/api/v1")
app.include_router(lifecycle_negotiation.external_router, prefix="/api/v1")
app.include_router(lookups.router, prefix="/api/v1")
app.include_router(signers.router, prefix="/api/v1")
app.include_router(signing_sessions.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
