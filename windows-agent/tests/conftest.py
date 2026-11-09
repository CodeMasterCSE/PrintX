import pytest
from pathlib import Path
from app.config import agent_settings
from app.security import security_manager

@pytest.fixture(autouse=True)
def setup_test_state_dir(tmp_path):
    agent_settings.STATE_DIR = str(tmp_path / "data")
    security_manager.state_file = Path(agent_settings.STATE_DIR) / "processed_jobs.json"
    security_manager.clear()
    yield
    security_manager.clear()
