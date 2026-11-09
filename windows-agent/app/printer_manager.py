from typing import List, Optional, Dict, Any
from app.logging_config import logger
from app.models import AgentPrinterInfo
from app.config import agent_settings

try:
    import win32print
    HAS_WIN32PRINT = True
except ImportError:
    win32print = None
    HAS_WIN32PRINT = False


class PrinterManager:
    """
    Interfaces directly with the native Windows 11 Print Spooler subsystem via pywin32.
    Enumerates printers, discovers HP Smart Tank 585 queues, and inspects queue depth.
    """

    def __init__(self):
        self.target_name = agent_settings.TARGET_PRINTER_NAME
        self.fallback_name = agent_settings.FALLBACK_PRINTER_NAME

    def get_installed_printers(self) -> List[AgentPrinterInfo]:
        """Enumerates all installed printers on the Windows system."""
        if not HAS_WIN32PRINT:
            logger.warning("pywin32 (win32print) is not available. Using simulated printer list.")
            return [
                AgentPrinterInfo(
                    name=self.target_name,
                    driver_name=self.target_name,
                    port_name="USB001",
                    is_default=True,
                    is_online=True,
                    status="online",
                    queue_length=0
                )
            ]

        printers_info: List[AgentPrinterInfo] = []
        try:
            default_printer = win32print.GetDefaultPrinter()
        except Exception:
            default_printer = ""

        # Enumerate both local and network connection printers
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        try:
            raw_printers = win32print.EnumPrinters(flags)
        except Exception as e:
            logger.error(f"Failed to enumerate Windows printers: {e}")
            return []

        for p in raw_printers:
            # raw_printers returns tuples (flags, description, name, comment)
            printer_name = p[2]
            handle = None
            try:
                handle = win32print.OpenPrinter(printer_name)
                details = win32print.GetPrinter(handle, 2)
                driver_name = details.get("pDriverName", "")
                port_name = details.get("pPortName", "")
                c_jobs = details.get("cJobs", 0)
                raw_status = details.get("Status", 0)

                # Decode status
                status_text = "online"
                status_details = "Ready"
                is_online = True

                if raw_status & 0x00000001:  # PRINTER_STATUS_PAUSED
                    status_text = "paused"
                    status_details = "Printer is paused"
                elif raw_status & 0x00000002:  # PRINTER_STATUS_ERROR
                    status_text = "error"
                    status_details = "General printer error"
                    is_online = False
                elif raw_status & 0x00000020:  # PRINTER_STATUS_OUT_OF_PAPER
                    status_text = "out_of_paper"
                    status_details = "Paper tray empty"
                elif raw_status & 0x00000004:  # PRINTER_STATUS_PENDING_DELETION
                    status_text = "offline"
                    is_online = False

                info = AgentPrinterInfo(
                    name=printer_name,
                    driver_name=driver_name,
                    port_name=port_name,
                    is_default=(printer_name == default_printer),
                    is_online=is_online,
                    status=status_text,
                    status_details=status_details,
                    queue_length=c_jobs
                )
                printers_info.append(info)
            except Exception as e:
                logger.debug(f"Could not query details for printer {printer_name}: {e}")
            finally:
                if handle:
                    try:
                        win32print.ClosePrinter(handle)
                    except Exception:
                        pass

        return printers_info

    def resolve_target_printer(self) -> Optional[AgentPrinterInfo]:
        """
        Discovers the physical HP Smart Tank 585 queue or falls back to Microsoft Print to PDF.
        Never sends duplicate jobs across both USB and Wi-Fi queues.
        """
        installed = self.get_installed_printers()
        installed_names = {p.name: p for p in installed}

        # 1. Exact match for target printer
        if self.target_name in installed_names:
            logger.info(f"Resolved primary physical printer queue: '{self.target_name}'")
            return installed_names[self.target_name]

        # 2. Substring search for HP Smart Tank series (handles variation e.g. HP5756E5)
        for name, p in installed_names.items():
            if "HP Smart Tank" in name or "Smart Tank 58" in name:
                logger.info(f"Discovered matching HP Smart Tank queue: '{name}'")
                return p

        # 3. Fallback to Microsoft Print to PDF for zero-waste local development
        if self.fallback_name in installed_names:
            logger.info(f"Target HP printer not detected. Using fallback virtual queue: '{self.fallback_name}'")
            return installed_names[self.fallback_name]

        # 4. Default to system default printer if available
        for p in installed:
            if p.is_default:
                logger.warning(f"Using default system printer queue: '{p.name}'")
                return p

        return None


printer_manager = PrinterManager()

