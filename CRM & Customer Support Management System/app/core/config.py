from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
   
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/crm_db"
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    upload_directory: str = "uploads"
    max_upload_size_bytes: int = 10 * 1024 * 1024
    sla_at_risk_minutes: int = 60
    background_job_interval_seconds: int = 300
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_directory)


settings = Settings()
