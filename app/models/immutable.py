"""Append-only persistence guard.

UC11-BR-005/BR-011: an audit log entry can never be modified or deleted. The HTTP layer
simply exposes no write route, but that only covers callers coming in through the API --
any service that loaded an entry into the session could still mutate it and have the flush
quietly persist the change. Registering the guard on the mapper closes that path at the
persistence layer: the attempt raises before SQLAlchemy emits the UPDATE/DELETE.

The matching database-level trigger belongs in an Alembic migration under `alembic/`,
which is outside the paths this change is allowed to touch -- see the task summary.
"""
from sqlalchemy import event

from app.errors import ImmutableResourceError

AUDIT_LOG_IMMUTABLE_MESSAGE = "Audit log entries cannot be modified or deleted."


def enforce_append_only(model: type, message: str = AUDIT_LOG_IMMUTABLE_MESSAGE) -> type:
    """Block UPDATE and DELETE on `model` at the mapper level. Returns the model so it can
    be used as a one-line call next to the class definition."""

    def _blocked(_mapper, _connection, _target) -> None:
        raise ImmutableResourceError(message, details=[message])

    event.listen(model, "before_update", _blocked, propagate=True)
    event.listen(model, "before_delete", _blocked, propagate=True)
    return model
