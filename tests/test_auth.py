"""Exercises the header-auth stub end-to-end through the real error-handling layer in
app/main.py: missing X-User-Role -> 401, a role outside the endpoint's allow-list -> 403,
a permitted role -> 200.
"""
from fastapi import Depends

from app.auth import CurrentUser, require_roles
from app.main import app

TENANT_ADMIN = "TENANT_ADMIN"


@app.get("/_test/protected")
def _protected(user: CurrentUser = Depends(require_roles(TENANT_ADMIN))) -> dict:
    return {"role": user.role}


def test_missing_role_header_is_401(client):
    resp = client.get("/_test/protected")
    assert resp.status_code == 401
    body = resp.json()
    assert "error" in body and "details" in body


def test_disallowed_role_is_403(client):
    resp = client.get(
        "/_test/protected",
        headers={"X-User-Role": "SIGNER", "X-User-Id": "00000000-0000-0000-0000-000000000001"},
    )
    assert resp.status_code == 403


def test_permitted_role_is_200(client):
    resp = client.get(
        "/_test/protected",
        headers={"X-User-Role": TENANT_ADMIN, "X-User-Id": "00000000-0000-0000-0000-000000000001"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"role": TENANT_ADMIN}


def test_role_outside_contract_is_403_not_accepted(client):
    """Only the 5 contract roles are ever permitted -- a made-up role must 403, not pass."""
    resp = client.get(
        "/_test/protected",
        headers={"X-User-Role": "SUPERUSER", "X-User-Id": "00000000-0000-0000-0000-000000000001"},
    )
    assert resp.status_code == 403


def test_openapi_declares_both_auth_headers_as_distinct_security_schemes(client):
    """Regression guard: X-User-Role and X-User-Id must be two distinct OpenAPI security
    schemes. Both APIKeyHeader instances defaulted to the same auto-generated component name
    ("APIKeyHeader") before `scheme_name` was set explicitly in app/auth.py, so the second
    one silently clobbered the first in the generated doc -- Swagger's "Authorize" dialog then
    offered only one header input and every "try it out" call came back 401 (see CLAUDE.md's
    callout on this exact failure mode).
    """
    schema = client.get("/openapi.json").json()
    schemes = schema["components"]["securitySchemes"]
    header_names = {scheme["name"] for scheme in schemes.values() if scheme.get("in") == "header"}
    assert {"X-User-Role", "X-User-Id"} <= header_names
