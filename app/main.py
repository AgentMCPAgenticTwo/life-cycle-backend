"""FastAPI entry point.

Wires the three things that are invisible until integration fails: CORS (before anything
else), the header-auth stub, and one shared error body.
"""
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(title="API", version="1.0")

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
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "details": []})


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError):
    details = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(
        status_code=400, content={"error": "validation failed", "details": details}
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Feature routers are included here as modules are implemented: from app.routers import jobs app.include_router(jobs.router, prefix="/api/v1").
