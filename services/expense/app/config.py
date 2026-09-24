import os
from functools import lru_cache


class Settings:
    """Environment-only configuration (Compose and Kubernetes inject the same keys)."""

    def __init__(self) -> None:
        self.database_host = os.environ.get("DATABASE_HOST", "localhost")
        self.database_port = os.environ.get("DATABASE_PORT", "5432")
        self.database_name = os.environ.get("DATABASE_NAME", "claimguard")
        self.database_user = os.environ.get("DATABASE_USER", "claimguard")
        self.database_password = os.environ.get("DATABASE_PASSWORD", "change-me")
        self.policy_base_url = os.environ.get("POLICY_BASE_URL", "http://localhost:8001").rstrip("/")
        self.policy_http_timeout_seconds = float(os.environ.get("POLICY_HTTP_TIMEOUT_SECONDS", "3"))

    @property
    def database_url(self) -> str:
        user = self.database_user
        password = self.database_password
        host = self.database_host
        port = self.database_port
        name = self.database_name
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
