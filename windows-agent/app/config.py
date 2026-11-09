from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BACKEND_API_URL: str = "http://127.0.0.1:8000/api/v1"
    AGENT_ID: str = "AGENT-WIN11-01"
    AGENT_SECRET: str = "printx-agent-local-secret-key"

    # Target Windows Printer Queue Name
    # Default matches the installed HP Smart Tank on this Windows 11 machine
    TARGET_PRINTER_NAME: str = "HP Smart Tank 580-590 series"
    FALLBACK_PRINTER_NAME: str = "Microsoft Print to PDF"

    # Headless PDF CLI Printer
    SUMATRAPDF_PATH: str = "./bin/SumatraPDF.exe"

    # Polling & Heartbeat intervals
    HEARTBEAT_INTERVAL_SECONDS: int = 10
    POLL_INTERVAL_SECONDS: int = 3
    SPOOLER_TIMEOUT_SECONDS: int = 120

    # Local state persistence for duplicate prevention
    STATE_DIR: str = "./data"

    @property
    def resolved_state_path(self) -> Path:
        p = Path(self.STATE_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


agent_settings = AgentSettings()

