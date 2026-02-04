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
    automation_enabled: bool = Field(True, alias="AUTOMATION_ENABLED")
    automation_default_timeout_seconds: int = Field(10, alias="AUTOMATION_DEFAULT_TIMEOUT_SECONDS")
    automation_max_attempts: int = Field(8, alias="AUTOMATION_MAX_ATTEMPTS")
    automation_replay_window_seconds: int = Field(300, alias="AUTOMATION_REPLAY_WINDOW_SECONDS")
    automation_rate_limit_per_minute: int = Field(60, alias="AUTOMATION_RATE_LIMIT_PER_MINUTE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()
