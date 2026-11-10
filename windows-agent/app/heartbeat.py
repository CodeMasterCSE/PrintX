import time
import requests
from app.config import agent_settings
from app.logging_config import logger
from app.printer_manager import printer_manager
from app.spooler_monitor import spooler_monitor


class AgentHeartbeat:
    """
    Transmits periodic heartbeat telemetry to the central backend.
    Reports real queue length, printer error state, and driver availability.
    """

    def __init__(self):
        self.backend_url = agent_settings.BACKEND_API_URL
        self.agent_id = agent_settings.AGENT_ID
        self.agent_secret = agent_settings.AGENT_SECRET

    def send_heartbeat(self) -> bool:
        target_info = printer_manager.resolve_target_printer()
        if not target_info:
            logger.warning("No printer resolved for heartbeat report.")
            return False

        current_status = target_info.status
        if spooler_monitor.check_hardware_paper_out(target_info.name):
            current_status = "out_of_paper"

        payload = {
            "agent_id": self.agent_id,
            "version": "1.0.0",
            "printer_name": target_info.name,
            "printer_status": current_status,
            "queue_length": target_info.queue_length,
            "is_online": target_info.is_online
        }

        headers = {
            "X-Agent-ID": self.agent_id,
            "X-Agent-Secret": self.agent_secret,
            "Content-Type": "application/json"
        }

        url = f"{self.backend_url}/printers/heartbeat"
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=5)
            if res.status_code in (200, 204):
                logger.debug("Heartbeat transmitted successfully.")
                return True
            else:
                logger.debug(f"Heartbeat received non-200: {res.status_code}")
                return False
        except Exception as e:
            logger.debug(f"Backend heartbeat connection failed (backend might be starting): {e}")
            return False


heartbeat_sender = AgentHeartbeat()

