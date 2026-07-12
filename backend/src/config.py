"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Runtime configuration for the mdify backend."""

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND")
    clamav_host: str = Field(default="localhost", alias="CLAMAV_HOST")
    clamav_port: int = Field(default=3310, alias="CLAMAV_PORT")
    max_upload_size_mb: int = Field(default=50, alias="MAX_UPLOAD_SIZE_MB")
    purge_interval_seconds: int = Field(default=600, alias="PURGE_INTERVAL_SECONDS")
    conversion_base_dir: str = Field(default="/tmp/conversions", alias="CONVERSION_BASE_DIR")

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    class Config:
        env_file = ".env"
        populate_by_name = True


settings = Settings()
