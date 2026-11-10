from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "PrintX"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "printx-insecure-dev-secret-key-change-in-production-min-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite:///./printx.db"

    # Storage & Object Cloud Backend
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    STORAGE_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    DOCUMENT_RETENTION_HOURS: int = 24
    S3_ENDPOINT_URL: Union[str, None] = None
    S3_BUCKET_NAME: str = "printx-documents"
    S3_REGION_NAME: str = "us-east-1"
    S3_ACCESS_KEY: Union[str, None] = None
    S3_SECRET_KEY: Union[str, None] = None
    SERVER_PUBLIC_URL: str = "http://127.0.0.1:8000"

    # Printer & Agent Defaults (dynamically populated via Admin discovery)
    DEFAULT_PRINTER_NAME: str = ""
    FALLBACK_PRINTER_NAME: str = ""
    AGENT_SECRET_KEY: str = "printx-agent-local-secret-key"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        return v

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def resolved_storage_path(self) -> Path:
        p = Path(self.STORAGE_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()

