from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql://ibis:ibis@localhost:5432/ibis"

    # Sign-in tokens (sliding sessions, see infrastructure/security/jwt_handler.py)
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24 * 90  # signed out after 90 days without using the app
    jwt_refresh_after_hours: int = 24  # tokens older than this are renewed on use

    # Deployment configuration
    cors_origins: str = "http://localhost:3000"
    run_migrations_on_startup: bool = False
    log_level: str = "info"

    # Uploads
    max_qr_image_kb: int = 1024

    @property
    def sqlalchemy_url(self) -> str:
        """Normalize Railway/Heroku style URLs (postgres://...) to SQLAlchemy URLs with an explicit driver.

        The driver is pinned to psycopg2 (the one installed): newer SQLAlchemy versions
        default plain postgresql:// to psycopg 3.
        """
        url = self.database_url.replace("+asyncpg", "")
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg2://" + url[len(prefix):]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env == "production":
            if not self.jwt_secret_key or self.jwt_secret_key == "change-this-in-production":
                raise ValueError("JWT_SECRET_KEY must be set to a secure value in production")
        return self


settings = Settings()
