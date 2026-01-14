from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Alfred CRM"
    environment: str = Field("development", description="Environment name")
    secret_key: str = Field("dev-secret", description="JWT secret key")
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = Field(
        "postgresql+psycopg2://alfred:alfred@db:5432/alfred",
        description="Database URL",
    )
    log_level: str = Field("INFO")
    ai_provider_backend: str = Field(
        "mock",
        description="AI provider backend to use (mock or income)",
        alias="AI_PROVIDER_BACKEND",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()
