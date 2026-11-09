from pathlib import Path
from unittest.mock import patch, MagicMock
from app.print_executor import PrintExecutor
from app.models import PrintJobSubmission
from app.security import security_manager


def test_build_sumatra_command_simplex_and_a4(tmp_path):
    test_pdf = tmp_path / "doc.pdf"
    test_pdf.write_text("dummy")

    pe = PrintExecutor()
    submission = PrintJobSubmission(
        job_id="test-job-01",
        job_number="PX-2026-0001",
        pdf_path=str(test_pdf),
        printer_name="HP Smart Tank 580-590 series",
        copies=2,
        color_mode="color",
        page_range="1-3,5",
        fit_to_page=True,
        duplex=False,  # Single-sided
        idempotency_key="idemp-01"
    )

    cmd, settings_str = pe.build_sumatra_command(submission)

    assert "-print-to" in cmd
    assert "HP Smart Tank 580-590 series" in cmd
    assert "-print-settings" in cmd
    # Enforces copies, color, fit, custom range, simplex, and A4 paper
    assert "2x" in settings_str
    assert "color" in settings_str
    assert "fit" in settings_str
    assert "1-3,5" in settings_str
    assert "simplex" in settings_str
    assert "paper=A4" in settings_str


def test_duplicate_print_prevention(tmp_path):
    test_pdf = tmp_path / "doc.pdf"
    test_pdf.write_text("dummy")

    pe = PrintExecutor()
    submission = PrintJobSubmission(
        job_id="unique-job-123",
        job_number="PX-0002",
        pdf_path=str(test_pdf),
        printer_name="Microsoft Print to PDF",
        copies=1,
        color_mode="grayscale",
        page_range="all",
        fit_to_page=True,
        duplex=False,
        idempotency_key="unique-idemp-123"
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr=b"")
        # First dispatch succeeds
        success1, _ = pe.execute_print_job(submission)
        assert success1 is True
        assert mock_run.call_count == 1

        # Immediate second duplicate attempt must be rejected by the guard
        success2, msg2 = pe.execute_print_job(submission)
        assert success2 is False
        assert "Duplicate submission rejected" in msg2
        # SumatraPDF should NOT be called again
        assert mock_run.call_count == 1

