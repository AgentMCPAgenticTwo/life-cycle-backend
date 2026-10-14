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


settings = Settings()
