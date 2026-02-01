from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str | None = None

    @property
    def database_url(self):
        return self.DATABASE_URL or "sqlite:///./local.db"

    # Security
    JWT_SECRET: str = Field(
        "your-secret-key-change-in-production",
        validation_alias=AliasChoices("JWT_SECRET", "SECRET_KEY"),
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    APP_ENV: str = "development"
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None

    # App
    PROJECT_NAME: str = "Receta Facil"
    API_V1_STR: str = "/api/v1"
    UPLOAD_DIR: str = "uploads/signatures"
    FRONTEND_URL: str = "http://localhost:3000"  # Base URL del frontend para enlaces (activación, etc.)

    # Email (SMTP). Si no están configurados, no se envía email.
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None


settings = Settings()
