from unittest.mock import patch
from app.spooler_monitor import (
    SpoolerMonitor,
    JOB_STATUS_PRINTING,
    JOB_STATUS_PAPEROUT,
    JOB_STATUS_ERROR
)


def test_decode_spooler_jobs_with_mocked_win32print():
    sm = SpoolerMonitor()
    mock_raw_jobs = (
        {
            "JobId": 101,
            "pDocument": "assignment.pdf",
            "Status": JOB_STATUS_PRINTING,
            "PagesPrinted": 1,
            "TotalPages": 3
        },
        {
            "JobId": 102,
            "pDocument": "thesis.pdf",
            "Status": JOB_STATUS_PAPEROUT,
            "PagesPrinted": 0,
            "TotalPages": 10
        }
    )

    with patch("app.spooler_monitor.HAS_WIN32PRINT", True), \
         patch("app.spooler_monitor.win32print") as mock_w32:
        mock_w32.OpenPrinter.return_value = 1
        mock_w32.EnumJobs.return_value = mock_raw_jobs

        jobs = sm.get_active_spooler_jobs("HP Smart Tank 580-590 series")
        assert len(jobs) == 2
        
        # Job 101: Active printing
        assert jobs[0].spooler_job_id == 101
        assert jobs[0].status_text == "printing"
        assert jobs[0].is_error is False

        # Job 102: Paper tray empty
        assert jobs[1].spooler_job_id == 102
        assert jobs[1].status_text == "out_of_paper"
        assert jobs[1].is_error is True
        assert "paper tray empty" in jobs[1].error_message

