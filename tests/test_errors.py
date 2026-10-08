"""Exercises the centralized error-handling layer in app/main.py: every non-2xx response,
whatever raised it, comes back as {"error": string, "details": string[]}.
"""
from fastapi.testclient import TestClient

from app.errors import ConflictError, NotFoundError, ValidationFailedError
from app.main import app


@app.get("/_test/not-found")
def _not_found():
    raise NotFoundError("contract not found")


@app.get("/_test/conflict")
def _conflict():
    raise ConflictError("stale version", details=["version 3 was expected"])


@app.get("/_test/validation-failed")
def _validation_failed():
    raise ValidationFailedError("validation failed", details=["startDate must be before endDate"])


@app.get("/_test/boom")
def _boom():
    raise RuntimeError("unexpected failure")


@app.get("/_test/typed")
def _typed(count: int):
    return {"count": count}


def _assert_shared_shape(body: dict) -> None:
    assert set(body.keys()) == {"error", "details"}
    assert isinstance(body["details"], list)


def test_not_found_is_404(client):
    resp = client.get("/_test/not-found")
    assert resp.status_code == 404
    body = resp.json()
    _assert_shared_shape(body)
    assert body["error"] == "contract not found"


def test_conflict_is_409(client):
    resp = client.get("/_test/conflict")
    assert resp.status_code == 409
    body = resp.json()
    _assert_shared_shape(body)
    assert body["details"] == ["version 3 was expected"]


def test_validation_failed_is_400(client):
    resp = client.get("/_test/validation-failed")
    assert resp.status_code == 400
    body = resp.json()
    _assert_shared_shape(body)


def test_unknown_route_is_404(client):
    resp = client.get("/_test/does-not-exist")
    assert resp.status_code == 404
    _assert_shared_shape(resp.json())


def test_request_validation_error_is_400(client):
    resp = client.get("/_test/typed", params={"count": "not-a-number"})
    assert resp.status_code == 400
    body = resp.json()
    _assert_shared_shape(body)
    assert body["details"]


def test_unhandled_exception_is_500(client):
    # The default TestClient re-raises server exceptions instead of returning the response,
    # which is right for catching a route that forgot to handle an error -- but here we are
    # specifically verifying the catch-all handler's own response shape, so that re-raise is
    # disabled for this one request.
    with TestClient(app, raise_server_exceptions=False) as raw_client:
        resp = raw_client.get("/_test/boom")
    assert resp.status_code == 500
    _assert_shared_shape(resp.json())
    assert resp.json()["error"] == "internal server error"
