---
type: Module
title: auth
description: Real login — JWT access tokens, rotating httpOnly-cookie refresh tokens, bcrypt password storage and the admin bootstrap script that replaced the X-User-Role/X-User-Id header stub.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/auth.py
tags: [backend, auth, jwt, security]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T08:07:59Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 700de34973c81dd98062f0bef469b620e6fc976b
    title: Codebase knowledge graph
status: stable
---

# Files

| File | Role |
|---|---|
| `app/routers/auth.py` | `router` (prefix `/auth`), `login`, `refresh`, `logout`, `me`, `change_password`, `_set_refresh_cookie` |
| `app/services/auth.py` | `login`, `refresh`, `logout`, `change_password`, `issue_refresh_token`, `to_auth_user`, `role_code_for`, `_assert_not_deactivated`, `_unauthorized` |
| `app/repositories/auth.py` | `find_user_by_email`, `find_user_by_id`, `find_user_in_tenant_by_email`, `find_tenant_user_by_email`, `insert_user`, `insert_refresh_token`, `find_live_refresh_token`, `revoke_token`, `revoke_all_for_user` |
| `app/schemas/auth.py` | `LoginRequest`, `LoginResponse`, `AuthUserResponse`, `RefreshResponse`, `ChangePasswordRequest` |
| `app/security.py` | password rules/hashing and token primitives (table below) |
| `app/models/user.py` | `User` — adds `password_hash`, `is_active`, `must_change_password`, `last_login_at` |
| `app/models/refresh_token.py` | `RefreshToken` — one issued token, stored as a digest |
| `app/scripts/create_admin.py` | `main`, `_parse_args` — bootstrap the first `TENANT_ADMIN` |
| `app/auth.py` | `current_user` now reads the bearer token; see [App Core](/modules/app-core.md) |

# Endpoints

| Method | Path | Auth | Response |
|---|---|---|---|
| POST | `/auth/login` | none | `LoginResponse` (`accessToken`, `user`) + refresh cookie |
| POST | `/auth/refresh` | refresh cookie | `RefreshResponse` + rotated cookie |
| POST | `/auth/logout` | refresh cookie | 204, cookie deleted |
| GET | `/auth/me` | bearer | `AuthUserResponse` |
| POST | `/auth/change-password` | bearer | 204 + replacement refresh cookie |

`app/main.py` mounts `auth.router` **twice** — once under `/api/v1` and once at the bare root —
because the frontend contract spells the auth routes without the `/api/v1` base path.

# Token design

* Access token: signed JWT (`app.security.create_access_token` / `decode_access_token`,
  `settings.jwt_algorithm` = HS256, TTL `ACCESS_TOKEN_TTL_MINUTES`, default 15). Returned in the
  response body; the SPA keeps it in memory.
* Refresh token: opaque random string (`generate_refresh_token`), stored only as its SHA-256
  digest (`hash_refresh_token`, compared with `refresh_token_matches`) in `refresh_tokens`, and
  sent to the browser only as an httpOnly cookie (`settings.refresh_cookie_name`,
  `refresh_cookie_secure`, `samesite=lax`, TTL `REFRESH_TOKEN_TTL_DAYS`, default 7).
* Rotation: `app.services.auth.refresh` revokes the presented row and issues a new one.
  `logout` revokes without re-issuing; `change_password` revokes all of the user's tokens
  (`revoke_all_for_user`) and issues one replacement.
* The caller's **role is read from the `users` row on every request**, not from token claims, so
  deactivation or a role change takes effect on the next request rather than the next login.

# Passwords

`app/security.py` owns the rules in one place: `password_violations` (min length `_MIN_LENGTH`,
character classes incl. `_SPECIALS`, message `PASSWORD_RULE_MESSAGE`), `generate_password` for
admin-issued temporary credentials, and `hash_password`/`verify_password` over bcrypt
(`bcrypt>=4.2` in `requirements.txt`; `PyJWT>=2.9` backs the token functions). Every
admin-created or reset credential sets `must_change_password` — see
[Settings](/modules/settings.md).

# Bootstrap

```bash
python -m app.scripts.create_admin --tenant "Acme Co" --name "Ada" --email ada@acme.test
```

Idempotent on tenant+email (re-running resets that admin's password). With no `--password` a
strong one is generated and printed once; only the bcrypt hash reaches the database.

# Relationships

* [App Core](/modules/app-core.md) — `current_user`/`require_roles`/`current_tenant_id` consume
  the access token issued here; their signatures did not change, so no other router was touched.
* [Settings](/modules/settings.md) — `POST /settings/users` and
  `POST /settings/users/{userId}/reset-password` create/reset the credentials this module
  authenticates.
* [Conventions](/conventions.md#authentication-verified-in-appauthpy-and-appsecuritypy) — the
  401/403 matrix as now implemented.
