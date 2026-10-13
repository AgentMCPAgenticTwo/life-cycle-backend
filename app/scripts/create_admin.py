"""Create the first TENANT_ADMIN so somebody can sign in to a fresh database.

    python -m app.scripts.create_admin --tenant "Acme Co" --name "Ada" \
        --email ada@acme.test [--password 'Str0ng!pass']

With no --password a strong one is generated and printed once -- that print is the only
place the plain password ever appears; only the bcrypt hash reaches the database. The
script is idempotent on tenant+email: re-running it resets that admin's password instead of
creating a duplicate row. Never commit a password; pass it on the command line or let the
script generate one.
"""
import argparse
import sys
import uuid
from datetime import datetime, timezone

from app.db import SessionLocal
from app.models.tenant import Tenant
from app.models.tracker import TenantUser
from app.models.user import User
from app.security import PASSWORD_RULE_MESSAGE, generate_password, hash_password, password_violations

ADMIN_ROLE_CODE = "TENANT_ADMIN"
ADMIN_ROLE_LABEL = "Tenant Admin"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or reset the first TENANT_ADMIN user.")
    parser.add_argument("--tenant", required=True, help="Tenant name (created if it does not exist)")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", default=None, help="Omit to generate a strong one")
    parser.add_argument(
        "--high-risk-threshold",
        type=int,
        default=70,
        help="Only used when the tenant is created by this run",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    password = args.password or generate_password()
    violations = password_violations(password)
    if violations:
        print(PASSWORD_RULE_MESSAGE, file=sys.stderr)
        return 2

    if SessionLocal is None:
        print("DATABASE_URL is not configured", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        tenant = db.query(Tenant).filter(Tenant.name == args.tenant, Tenant.deleted_at.is_(None)).first()
        actor_id = uuid.uuid4()
        if tenant is None:
            tenant = Tenant(
                name=args.tenant,
                high_risk_threshold=args.high_risk_threshold,
                created_by=actor_id,
                updated_by=actor_id,
            )
            db.add(tenant)
            db.flush()

        email = args.email.strip()
        user = (
            db.query(User)
            .filter(User.tenant_id == tenant.id, User.email == email, User.deleted_at.is_(None))
            .first()
        )
        if user is None:
            user = User(
                tenant_id=tenant.id,
                name=args.name,
                email=email,
                role=ADMIN_ROLE_CODE,
                created_by=actor_id,
                updated_by=actor_id,
            )
            db.add(user)
            db.flush()
        user.password_hash = hash_password(password)
        user.is_active = True
        user.must_change_password = True
        user.updated_at = now
        user.updated_by = user.id

        tenant_user = (
            db.query(TenantUser)
            .filter(
                TenantUser.tenant_id == tenant.id,
                TenantUser.email == email,
                TenantUser.deleted_at.is_(None),
            )
            .first()
        )
        if tenant_user is None:
            db.add(
                TenantUser(
                    tenant_id=tenant.id,
                    name=args.name,
                    email=email,
                    role=ADMIN_ROLE_LABEL,
                    status="Active",
                    created_by=user.id,
                    updated_by=user.id,
                )
            )
        else:
            tenant_user.status = "Active"
        db.commit()
    finally:
        db.close()

    print(f"Tenant admin ready: {args.email}")
    print(f"Temporary password: {password}")
    print("The user must change this password at first login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
