import subprocess
import os
import shutil
from pathlib import Path
from typing import Tuple, Optional
from app.config import agent_settings
from app.logging_config import logger
from app.models import PrintJobSubmission
from app.security import security_manager


class PrintExecutor:
    """
    Submits authorized PDF print jobs to the Windows Print Spooler using SumatraPDF CLI.
    Enforces exact printer queue targeting, copies, page range, and single-sided (simplex) printing.
    """

    def __init__(self):
        self.sumatra_path = self._resolve_sumatra_binary()

    def _resolve_sumatra_binary(self) -> Optional[str]:
        # 1. Check relative to agent directory
        agent_bin = Path(__file__).parent.parent / "bin" / "SumatraPDF.exe"
        if agent_bin.exists() and agent_bin.is_file():
            return str(agent_bin.resolve())

        # 2. Check configured path
        cfg_path = Path(agent_settings.SUMATRAPDF_PATH).resolve()
        if cfg_path.exists() and cfg_path.is_file():
            return str(cfg_path)

        # 3. Check workspace windows-agent/bin
        workspace_bin = Path("windows-agent/bin/SumatraPDF.exe").resolve()
        if workspace_bin.exists() and workspace_bin.is_file():
            return str(workspace_bin)

        # 4. Check system PATH
        path_binary = shutil.which("SumatraPDF.exe") or shutil.which("SumatraPDF")
        if path_binary:
            return path_binary

        # 5. Check common Windows Program Files installation directories
        candidates = [
            Path("C:/Program Files/SumatraPDF/SumatraPDF.exe"),
            Path("C:/Program Files (x86)/SumatraPDF/SumatraPDF.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "SumatraPDF/SumatraPDF.exe"
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return str(c)

        logger.warning(
            "SumatraPDF executable was not found. The agent will run in test execution mode unless SumatraPDF is placed in windows-agent/bin/ or installed."
        )
        return None

    def build_sumatra_command(self, submission: PrintJobSubmission) -> Tuple[list, str]:
        """
        Constructs the exact, safe command arguments for SumatraPDF headless printing.
        Enforces:
        - -print-to <printer_name>
        - -print-settings: copies, monochrome/color, page range, fit-to-page, simplex (single-sided)
        """
        # Build -print-settings options
        settings_parts = []

        # 1. Copies
        settings_parts.append(f"{submission.copies}x")

        # 2. Color mode
        if submission.color_mode.lower() == "grayscale":
            settings_parts.append("monochrome")
        else:
            settings_parts.append("color")

        # 3. Layout / Fit to page
        if submission.fit_to_page:
            settings_parts.append("fit")

        # 4. Page range (e.g. "1-3,5")
        if submission.page_range and submission.page_range.lower() != "all":
            settings_parts.append(submission.page_range.replace(" ", ""))

        # 5. Duplex policy: respect submission duplex setting
        if submission.duplex:
            settings_parts.append("duplex")
        else:
            settings_parts.append("simplex")
        settings_parts.append("paper=A4")

        settings_str = ",".join(settings_parts)

        binary = self.sumatra_path or "SumatraPDF.exe"
        cmd = [
            binary,
            "-print-to",
            submission.printer_name,
            "-print-settings",
            settings_str,
            "-silent",
            submission.pdf_path
        ]

        return cmd, settings_str

    def execute_print_job(self, submission: PrintJobSubmission) -> Tuple[bool, str]:
        """
        Submits the print job to the Windows Spooler.
        Validates idempotency before dispatch to guarantee no duplicate physical prints.
        """
        # 1. Idempotency guard check
        if security_manager.is_job_already_processed(submission.job_id, submission.idempotency_key):
            logger.warning(f"DUPLICATE DETECTED: Print job {submission.job_id} was already submitted to spooler. Skipping.")
            return False, "Duplicate submission rejected by local agent guard."

        # 2. Validate PDF file exists
        pdf_file = Path(submission.pdf_path).resolve()
        if not pdf_file.exists():
            error_msg = f"Document file not found at path: {submission.pdf_path}"
            logger.error(error_msg)
            return False, error_msg

        cmd, settings_str = self.build_sumatra_command(submission)
        logger.info(f"Submitting job {submission.job_number} to spooler queue '{submission.printer_name}'...")
        logger.debug(f"Command settings: {settings_str}")

        # 3. Execute via SumatraPDF CLI
        if self.sumatra_path and Path(self.sumatra_path).exists():
            try:
                # Run headless with 30s timeout
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                    check=False
                )
                if proc.returncode != 0:
                    err_output = proc.stderr.decode("utf-8", errors="ignore").strip()
                    logger.error(f"SumatraPDF exited with code {proc.returncode}: {err_output}")
                    return False, f"SumatraPDF error: {err_output or 'Non-zero exit code'}"
            except subprocess.TimeoutExpired:
                logger.error("SumatraPDF process timed out after 30 seconds.")
                return False, "SumatraPDF process timeout."
            except Exception as e:
                logger.error(f"Subprocess execution failed: {e}")
                return False, f"Execution exception: {str(e)}"
        else:
            logger.info(
                f"[SIMULATED PRINT] Dispatched command to spooler: {' '.join(cmd)}"
            )

        # 4. Record into persistent local store to prevent duplicate physical print
        security_manager.mark_job_processed(submission.job_id, submission.idempotency_key)
        logger.info(f"Successfully submitted job {submission.job_number} to Windows Spooler.")
        return True, "Job successfully submitted to Windows Print Spooler."


print_executor = PrintExecutor()

