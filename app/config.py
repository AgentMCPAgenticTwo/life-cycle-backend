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


settings = Settings()
