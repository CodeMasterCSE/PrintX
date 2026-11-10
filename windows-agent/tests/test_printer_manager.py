from unittest.mock import patch, MagicMock
from app.printer_manager import PrinterManager
from app.models import AgentPrinterInfo


def test_resolve_exact_hp_smart_tank():
    pm = PrinterManager()
    fake_printers = [
        AgentPrinterInfo(
            name="OneNote",
            driver_name="OneNote",
            port_name="nul:",
            is_default=False,
            is_online=True,
            is_virtual=True,
            status="online"
        ),
        AgentPrinterInfo(
            name="HP Smart Tank 580-590 series",
            driver_name="HP Smart Tank 580-590 series",
            port_name="USB001",
            is_default=True,
            is_online=True,
            is_virtual=False,
            status="online"
        )
    ]

    with patch.object(pm, "get_installed_printers", return_value=fake_printers):
        target = pm.resolve_target_printer()
        assert target is not None
        assert target.name == "HP Smart Tank 580-590 series"
        assert target.is_online is True


def test_resolve_fallback_pdf_printer_when_hp_not_found():
    pm = PrinterManager()
    fake_printers = [
        AgentPrinterInfo(
            name="Microsoft Print to PDF",
            driver_name="Microsoft Print to PDF",
            port_name="PORTPROMPT:",
            is_default=True,
            is_online=True,
            is_virtual=True,
            status="online"
        )
    ]

    with patch.object(pm, "get_installed_printers", return_value=fake_printers):
        target = pm.resolve_target_printer()
        assert target is not None
        assert target.name == "Microsoft Print to PDF"

