"""Password hashing, password-strength rules and JWT/refresh-token primitives.

This module owns no business rules and touches no database -- `app.services.auth` and
`app.services.settings_users` call into it. Plain passwords are never stored or logged:
only the bcrypt hash of a password, and only the SHA-256 hash of a refresh token, ever
reach the database.
"""
import hashlib
import hmac
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

PASSWORD_RULE_MESSAGE = (
    "Password must be at least 8 characters and include an uppercase letter, "
    "a lowercase letter, a number and a special character."
)

_SPECIALS = set("!@#$%^&*()-_=+[]{};:,.<>?/|~`\"'\\")
_MIN_LENGTH = 8


def password_violations(password: str | None) -> list[str]:
    """Returns the (single) rule message when `password` fails the strength rule."""
    if password is None:
        return [PASSWORD_RULE_MESSAGE]
    if (
        len(password) < _MIN_LENGTH
        or not any(c.isupper() for c in password)
        or not any(c.islower() for c in password)
        or not any(c.isdigit() for c in password)
        or not any(c in _SPECIALS for c in password)
    ):
        return [PASSWORD_RULE_MESSAGE]
    return []


def generate_password(length: int = 16) -> str:
    """A strong random password that satisfies `password_violations` by construction."""
    specials = "!@#$%^&*-_=+?"
    alphabet = string.ascii_letters + string.digits + specials
    while True:
        chars = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice(specials),
        ]
        chars += [secrets.choice(alphabet) for _ in range(max(length, _MIN_LENGTH) - 4)]
        secrets.SystemRandom().shuffle(chars)
        candidate = "".join(chars)
        if not password_violations(candidate):
            return candidate


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID, role: str, tenant_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "tenantId": str(tenant_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Returns the claims, or None when the token is malformed, tampered with or expired."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


def create_file_token(user_id: uuid.UUID, tenant_id: uuid.UUID, resource: str) -> str:
    """A short-lived token for ONE downloadable resource, carried in the `fileUrl` query
    string because the browser cannot attach an Authorization header to a window.open or an
    `<a download>` click. `resource` pins the token to a single file so it cannot be replayed
    against another one."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenantId": str(tenant_id),
        "resource": resource,
        "purpose": "file",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.file_token_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_file_token(token: str, resource: str) -> dict | None:
    """Returns the claims when `token` is a valid, unexpired file token for `resource`."""
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if claims.get("purpose") != "file" or claims.get("resource") != resource:
        return None
    return claims


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Refresh tokens are opaque high-entropy strings, so a fast digest is enough -- what
    matters is that a database dump does not hand out usable sessions."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_matches(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_refresh_token(token), token_hash)


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)
