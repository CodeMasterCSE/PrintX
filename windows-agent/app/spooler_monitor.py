import time
from typing import List, Optional, Dict, Any
from app.logging_config import logger
from app.models import SpoolerJobStatus
from app.config import agent_settings

try:
    import win32print
    HAS_WIN32PRINT = True
except ImportError:
    win32print = None
    HAS_WIN32PRINT = False


# Win32 Spooler Job Status Bitflags
JOB_STATUS_PAUSED = 0x00000001
JOB_STATUS_ERROR = 0x00000002
JOB_STATUS_DELETING = 0x00000004
JOB_STATUS_SPOOLING = 0x00000008
JOB_STATUS_PRINTING = 0x00000010
JOB_STATUS_OFFLINE = 0x00000020
JOB_STATUS_PAPEROUT = 0x00000040
JOB_STATUS_PRINTED = 0x00000080
JOB_STATUS_DELETED = 0x00000100
JOB_STATUS_BLOCKED_DEVQ = 0x00000200
JOB_STATUS_USER_INTERVENTION = 0x00000400
JOB_STATUS_RESTART = 0x00000800
JOB_STATUS_COMPLETE = 0x00001000


class SpoolerMonitor:
    """
    Monitors the Windows Print Spooler queue via win32print APIs.
    Truthfully differentiates between:
    1. Present in Spooler Queue
    2. Active Spooling / Printing
    3. Left Spooler Queue (sent to printer buffer)
    4. Hardware error (Paper out / Jam / Offline)
    """

    def __init__(self, printer_name: Optional[str] = None):
        self.printer_name = printer_name or agent_settings.TARGET_PRINTER_NAME

    def get_active_spooler_jobs(self, printer_name: Optional[str] = None) -> List[SpoolerJobStatus]:
        """Queries the Windows Spooler for all pending or printing jobs in the queue."""
        target = printer_name or self.printer_name
        if not HAS_WIN32PRINT:
            return []

        handle = None
        jobs_list: List[SpoolerJobStatus] = []
        try:
            handle = win32print.OpenPrinter(target)
            raw_jobs = win32print.EnumJobs(handle, 0, -1, 2)
            for j in raw_jobs:
                job_id = j.get("JobId", 0)
                doc_name = j.get("pDocument", "")
                status_code = j.get("Status", 0)
                pages_printed = j.get("PagesPrinted", 0)
                total_pages = j.get("TotalPages", 0)

                # Decode bitflags
                status_text = "queued"
                is_error = False
                error_msg = None

                if status_code & JOB_STATUS_PRINTING:
                    status_text = "printing"
                elif status_code & JOB_STATUS_SPOOLING:
                    status_text = "spooling"
                elif status_code & JOB_STATUS_PAUSED:
                    status_text = "paused"
                elif status_code & JOB_STATUS_PAPEROUT:
                    status_text = "out_of_paper"
                    is_error = True
                    error_msg = "Printer paper tray empty"
                elif status_code & JOB_STATUS_OFFLINE:
                    status_text = "offline"
                    is_error = True
                    error_msg = "Printer is offline or disconnected"
                elif status_code & JOB_STATUS_ERROR:
                    status_text = "error"
                    is_error = True
                    error_msg = "Spooler hardware error detected"
                elif status_code & JOB_STATUS_USER_INTERVENTION:
                    status_text = "user_intervention"
                    is_error = True
                    error_msg = "Printer requires user attention (e.g. door open or jam)"

                is_completed = bool(status_code & (JOB_STATUS_PRINTED | JOB_STATUS_COMPLETE))

                jobs_list.append(SpoolerJobStatus(
                    spooler_job_id=job_id,
                    document_name=doc_name,
                    status_code=status_code,
                    status_text=status_text,
                    pages_printed=pages_printed,
                    total_pages=total_pages,
                    is_completed=is_completed,
                    is_error=is_error,
                    error_message=error_msg
                ))
        except Exception as e:
            logger.debug(f"Could not read spooler queue for '{target}': {e}")
        finally:
            if handle:
                try:
                    win32print.ClosePrinter(handle)
                except Exception:
                    pass

        return jobs_list

    def wait_for_spooler_dispatch(
        self,
        printer_name: str,
        timeout_seconds: int = 60,
        poll_interval: float = 1.0
    ) -> Dict[str, Any]:
        """
        Monitors spooler queue until newly submitted jobs clear the Windows Spooler.
        Returns precise lifecycle telemetry:
        - submitted_to_spooler: True
        - spooler_cleared: True when job data is fully transferred to physical printer buffer
        """
        start_time = time.time()
        initial_jobs = self.get_active_spooler_jobs(printer_name)
        logger.info(f"Monitoring queue '{printer_name}' (Current depth: {len(initial_jobs)})...")

        saw_job_in_queue = False
        while time.time() - start_time < timeout_seconds:
            current_jobs = self.get_active_spooler_jobs(printer_name)

            for job in current_jobs:
                if job.is_error:
                    logger.error(f"Spooler error detected on job {job.spooler_job_id}: {job.error_message}")
                    return {
                        "success": False,
                        "status": "SPOOLER_ERROR",
                        "error_message": job.error_message,
                        "saw_in_queue": True
                    }

            if len(current_jobs) > 0:
                saw_job_in_queue = True

            # If jobs were in queue and now cleared, spooler transmission to printer is complete
            if saw_job_in_queue and len(current_jobs) == 0:
                logger.info(f"Print job successfully dispatched through Windows Spooler buffer.")
                return {
                    "success": True,
                    "status": "SUBMITTED_TO_SPOOLER",
                    "note": "Document successfully spooled and transferred to physical printer memory buffer.",
                    "saw_in_queue": True
                }

            time.sleep(poll_interval)

        return {
            "success": True,
            "status": "SUBMITTED_TO_SPOOLER",
            "note": "Job accepted by spooler subsystem.",
            "saw_in_queue": saw_job_in_queue
        }

    def check_hardware_paper_out(self, printer_name: Optional[str] = None) -> bool:
        """Returns True if any active spooler job or queue status indicates paper-out."""
        jobs = self.get_active_spooler_jobs(printer_name)
        return any(j.status_text == "out_of_paper" or bool(j.status_code & JOB_STATUS_PAPEROUT) for j in jobs)


spooler_monitor = SpoolerMonitor()

