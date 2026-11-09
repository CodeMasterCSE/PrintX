import requests
from pathlib import Path
from typing import Optional, Dict, Any
from app.config import agent_settings
from app.logging_config import logger
from app.models import PrintJobSubmission
from app.printer_manager import printer_manager
from app.print_executor import print_executor
from app.spooler_monitor import spooler_monitor


class JobReceiver:
    """
    Pulls authorized and payment-verified print jobs from the central backend.
    Independently re-validates payment authorization before sending to physical hardware.
    """

    def __init__(self):
        self.backend_url = agent_settings.BACKEND_API_URL
        self.agent_id = agent_settings.AGENT_ID
        self.agent_secret = agent_settings.AGENT_SECRET

    @property
    def auth_headers(self) -> dict:
        return {
            "X-Agent-ID": self.agent_id,
            "X-Agent-Secret": self.agent_secret,
            "Content-Type": "application/json"
        }

    def update_job_status(
        self,
        job_id: str,
        status: str,
        spooler_job_id: Optional[int] = None,
        error_message: Optional[str] = None,
        message: Optional[str] = None
    ) -> bool:
        """Reports state machine transition back to the server."""
        url = f"{self.backend_url}/jobs/{job_id}/status"
        payload = {
            "status": status,
            "spooler_job_id": spooler_job_id,
            "error_message": error_message,
            "message": message
        }
        try:
            res = requests.patch(url, json=payload, headers=self.auth_headers, timeout=5)
            return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to transmit status update for job {job_id}: {e}")
            return False

    def _download_document(self, job_id: str, url: str) -> Optional[str]:
        """Downloads document from pre-signed cloud URL or backend to local cache for cloud deployment."""
        try:
            cache_dir = Path(agent_settings.STATE_DIR) / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            local_file = cache_dir / f"{job_id}.pdf"
            logger.info(f"Downloading remote document for job {job_id} from cloud storage...")
            res = requests.get(url, headers=self.auth_headers, stream=True, timeout=30)
            if res.status_code == 200:
                with open(local_file, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        f.write(chunk)
                return str(local_file.resolve())
            else:
                logger.error(f"Cloud document download failed with HTTP status {res.status_code}")
                return None
        except Exception as e:
            logger.error(f"Exception during cloud document download: {e}")
            return None

    def process_submission(self, raw_job: Dict[str, Any]) -> bool:
        """
        Executes an authorized print job:
        1. Checks payment status on the backend payload (never print unpaid!)
        2. Resolves target printer queue
        3. Downloads remote file if cloud URL provided
        4. Submits via SumatraPDF CLI
        5. Monitors Spooler queue
        6. Reports completion
        """
        job_id = raw_job["id"]
        job_number = raw_job["job_number"]
        status = raw_job.get("status")

        # Independent Authorization Check: Reject if not payment verified
        if status not in ("PAYMENT_VERIFIED", "QUEUED"):
            logger.error(f"SECURITY ALERT: Dropping job {job_number} because status '{status}' is NOT paid/authorized!")
            return False

        printer_info = printer_manager.resolve_target_printer()
        if not printer_info:
            logger.error("No Windows printer available to process job.")
            self.update_job_status(job_id, "FAILED", error_message="Printer offline or not detected.")
            return False

        # Mark Dispatched
        self.update_job_status(job_id, "DISPATCHED", message=f"Pulled by agent {self.agent_id}")

        # Resolve document path (supports local path or remote cloud URL)
        raw_doc_path = raw_job.get("document_path", "")
        if raw_doc_path.startswith("http://") or raw_doc_path.startswith("https://"):
            local_pdf = self._download_document(job_id, raw_doc_path)
            if not local_pdf:
                self.update_job_status(job_id, "FAILED", error_message="Failed to download cloud document.")
                return False
            pdf_path = local_pdf
        else:
            pdf_path = raw_doc_path

        cfg = raw_job.get("configuration", {})
        submission = PrintJobSubmission(
            job_id=job_id,
            job_number=job_number,
            pdf_path=pdf_path,
            printer_name=printer_info.name,
            copies=cfg.get("copies", 1),
            color_mode=cfg.get("color_mode", "grayscale"),
            page_range=cfg.get("page_range", "all"),
            fit_to_page=cfg.get("fit_to_page", True),
            duplex=False,  # Enforce single-sided for HP Smart Tank 585
            idempotency_key=raw_job.get("idempotency_key", job_id)
        )

        # Execute Print
        success, message = print_executor.execute_print_job(submission)
        if not success:
            self.update_job_status(job_id, "FAILED", error_message=message)
            return False

        # Transition to SUBMITTED_TO_SPOOLER
        self.update_job_status(job_id, "SUBMITTED_TO_SPOOLER", message="Document accepted by Windows Spooler")

        # Monitor Spooler queue
        telemetry = spooler_monitor.wait_for_spooler_dispatch(printer_info.name, timeout_seconds=60)
        if telemetry.get("status") == "SPOOLER_ERROR":
            self.update_job_status(job_id, "FAILED", error_message=telemetry.get("error_message"))
            return False

        # Mark Completed (spooled and transferred to physical buffer)
        self.update_job_status(job_id, "COMPLETED", message="Document spooled successfully to physical printer buffer.")
        logger.info(f"Job {job_number} processing finished.")
        return True

    def poll_next_job(self) -> Optional[Dict[str, Any]]:
        """Polls backend for next ready print job."""
        url = f"{self.backend_url}/jobs/agent/pull"
        try:
            res = requests.post(url, headers=self.auth_headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("job"):
                    return data["job"]
        except Exception as e:
            logger.debug(f"Job polling probe error: {e}")
        return None


job_receiver = JobReceiver()

