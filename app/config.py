"""Configuration read from the environment; never hard-code credentials."""
import os


class Settings:
    port: int = int(os.environ.get("PORT", "5199"))
    database_url: str = os.environ.get("DATABASE_URL", "")
    cors_origins: list[str] = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]
    # Real login replaces the former header-auth stub: access tokens are signed JWTs and the
    # refresh token lives in an httpOnly cookie. The secret and both TTLs come from the
    # environment -- never hard-code credentials.
    jwt_secret: str = os.environ.get("JWT_SECRET", "dev-only-insecure-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = int(os.environ.get("ACCESS_TOKEN_TTL_MINUTES", "15"))
    refresh_token_ttl_days: int = int(os.environ.get("REFRESH_TOKEN_TTL_DAYS", "7"))
    refresh_cookie_name: str = os.environ.get("REFRESH_COOKIE_NAME", "refreshToken")
    refresh_cookie_secure: bool = os.environ.get("REFRESH_COOKIE_SECURE", "false").lower() == "true"
    # Where `app.services.tracker_export` writes the generated Excel/PDF export files (UC10).
    # They are served back through GET /api/v1/tracker/exports/{fileId}; a plain directory,
    # because no object-storage client is declared in this repo's manifest.
    export_storage_dir: str = os.environ.get("EXPORT_STORAGE_DIR", "var/exports")
    # Where contract document bytes live: the uploaded third party paper and the generated
    # Version 1 document. Served back through GET /api/v1/contracts/{contractId}/document/file.
    document_storage_dir: str = os.environ.get("DOCUMENT_STORAGE_DIR", "var/documents")
    # Absolute, browser-reachable base URL of THIS API. Every `fileUrl` handed to the frontend
    # is built from it: a relative path resolves against the SPA's own origin, which serves the
    # app shell -- a blank screen -- instead of the file.
    api_base_url: str = os.environ.get(
        "API_BASE_URL", f"http://localhost:{os.environ.get('PORT', '5199')}"
    ).rstrip("/")
    # A `fileUrl` is opened directly by the browser (window.open / <a download>), which cannot
    # carry the Authorization header, so the URL carries a short-lived signed file token
    # instead. The byte endpoints still accept a bearer token when one is sent.
    file_token_ttl_minutes: int = int(os.environ.get("FILE_TOKEN_TTL_MINUTES", "15"))
    # Outbound mail for app.services.notifications. With no SMTP_HOST the service logs the
    # message instead of sending it, so the app runs without a mail relay. Credentials come
    # from the environment -- never hard-code them.
    smtp_host: str = os.environ.get("SMTP_HOST", "")
    smtp_port: int = int(os.environ.get("SMTP_PORT", "587"))
    smtp_username: str = os.environ.get("SMTP_USERNAME", "")
    smtp_password: str = os.environ.get("SMTP_PASSWORD", "")
    smtp_from: str = os.environ.get("SMTP_FROM", "no-reply@localhost")
    smtp_use_tls: bool = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    smtp_timeout_seconds: int = int(os.environ.get("SMTP_TIMEOUT_SECONDS", "10"))
    # How often app.services.scheduled_notifications sweeps for overdue reviews, due
    # signature reminders and renewal alerts. The sweeps are idempotent per day/per cadence,
    # so a shorter interval only makes an alert land sooner. 0 disables the in-process sweep
    # (e.g. when an external scheduler calls `run_all` instead).
    notification_sweep_interval_seconds: int = int(
        os.environ.get("NOTIFICATION_SWEEP_INTERVAL_SECONDS", "3600")
    )


settings = Settings()
