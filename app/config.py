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


settings = Settings()
