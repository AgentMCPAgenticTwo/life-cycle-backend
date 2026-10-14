"""Shared application exceptions.

Resource routers/services raise these instead of hand-rolling a `JSONResponse`, so every
non-2xx body in the API comes out of the single error-handling layer in `app/main.py` with
the one shared shape: `{"error": string, "details": string[]}`.
"""
from fastapi import HTTPException


class NotFoundError(HTTPException):
    """Maps to 404 -- the requested resource does not exist (or is soft-deleted)."""

    def __init__(self, detail: str = "resource not found"):
        super().__init__(status_code=404, detail=detail)


class ForbiddenError(HTTPException):
    """Maps to 403 -- distinct from `require_roles`' coarse role check: the caller's role is
    on an endpoint's allowed list, but the specific resource is outside what their role/
    assignment permits (e.g. UC1-AF-006's "no permitted actions on this contract")."""

    def __init__(self, detail: str = "forbidden", details: list[str] | None = None):
        self.details = details or []
        super().__init__(status_code=403, detail=detail)


class ConflictError(HTTPException):
    """Maps to 409 -- the request conflicts with the current state (duplicate, stale version)."""

    def __init__(self, detail: str = "conflict", details: list[str] | None = None):
        self.details = details or []
        super().__init__(status_code=409, detail=detail)


class ImmutableResourceError(HTTPException):
    """Maps to 403 -- the resource is append-only and can never be modified or deleted,
    whoever the caller is (UC11: the audit log). Distinct from `ForbiddenError`, which is
    about *who* is asking; this one is about *what* is being asked."""

    def __init__(self, detail: str = "resource is immutable", details: list[str] | None = None):
        self.details = details or []
        super().__init__(status_code=403, detail=detail)


class ValidationFailedError(HTTPException):
    """Maps to 400 -- a business-rule validation failure distinct from request-shape errors.

    `RequestValidationError` (malformed/missing fields) is handled separately in `app/main.py`;
    this is for rule violations services discover after Pydantic has already parsed the body.
    """

    def __init__(self, detail: str = "validation failed", details: list[str] | None = None):
        self.details = details or []
        super().__init__(status_code=400, detail=detail)
