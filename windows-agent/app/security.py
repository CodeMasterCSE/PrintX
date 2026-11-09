import json
from pathlib import Path
from typing import Set
from app.config import agent_settings
from app.logging_config import logger


class AgentSecurityManager:
    """
    Manages local idempotency store and verifies print authorization.
    Prevents duplicate physical printing and ensures unauthorized jobs are dropped.
    """

    def __init__(self):
        self.state_file = agent_settings.resolved_state_path / "processed_jobs.json"
        self._processed_ids: Set[str] = self._load_processed_jobs()

    def _load_processed_jobs(self) -> Set[str]:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                return set(data.get("processed_job_ids", []))
            except Exception as e:
                logger.warning(f"Could not read agent processed jobs file: {e}")
        return set()

    def _save_processed_jobs(self) -> None:
        try:
            payload = {"processed_job_ids": list(self._processed_ids)}
            self.state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist processed jobs state: {e}")

    def is_job_already_processed(self, job_id: str, idempotency_key: str) -> bool:
        """Returns True if the job ID or idempotency key was previously submitted."""
        return (job_id in self._processed_ids) or (idempotency_key in self._processed_ids)

    def mark_job_processed(self, job_id: str, idempotency_key: str) -> None:
        """Records the job as successfully dispatched to prevent replay attacks."""
        self._processed_ids.add(job_id)
        self._processed_ids.add(idempotency_key)
        self._save_processed_jobs()
        logger.info(f"Registered job {job_id} into persistent duplicate guard.")

    def clear(self) -> None:
        """Clears the in-memory and on-disk processed jobs state (used for testing)."""
        self._processed_ids.clear()
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except Exception:
                pass

    def validate_agent_credentials(self, headers: dict) -> bool:
        """Validates incoming webhook or communication credentials."""
        secret = headers.get("X-Agent-Secret")
        return secret == agent_settings.AGENT_SECRET


security_manager = AgentSecurityManager()
