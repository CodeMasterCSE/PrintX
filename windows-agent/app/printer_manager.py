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

                # Decode status using Windows WinSpool constants
                status_text = "online"
                status_details = "Ready"
                is_online = True

                if raw_status & 0x00000001:  # PRINTER_STATUS_PAUSED
                    status_text = "paused"
                    status_details = "Printer is paused"
                elif raw_status & 0x00000008:  # PRINTER_STATUS_PAPER_JAM
                    status_text = "paper_jam"
                    status_details = "Paper jam detected in transport path"
                    is_online = False
                elif raw_status & (0x00000010 | 0x00000020):  # PRINTER_STATUS_PAPER_OUT / MANUAL_FEED
                    status_text = "out_of_paper"
                    status_details = "Paper tray empty - please refill paper"
                elif raw_status & 0x00000080:  # PRINTER_STATUS_OFFLINE
                    status_text = "offline"
                    status_details = "Printer offline or disconnected"
                    is_online = False
                elif raw_status & 0x00400000:  # PRINTER_STATUS_DOOR_OPEN
                    status_text = "door_open"
                    status_details = "Printer cover or ink door open"
                elif raw_status & 0x00000002:  # PRINTER_STATUS_ERROR
                    status_text = "error"
                    status_details = "General printer error"
                    is_online = False
                elif raw_status & 0x00000004:  # PRINTER_STATUS_PENDING_DELETION
                    status_text = "offline"
                    is_online = False

                is_virt = any(v in printer_name.lower() or v in driver_name.lower() for v in ["pdf", "onenote", "xps", "fax"])
                info = AgentPrinterInfo(
                    name=printer_name,
                    driver_name=driver_name,
                    port_name=port_name,
                    is_default=(printer_name == default_printer),
                    is_online=is_online,
                    is_virtual=is_virt,
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

    def resolve_target_printer(self, requested_name: Optional[str] = None) -> Optional[AgentPrinterInfo]:
        """
        Discovers and resolves the target printer queue for any connected physical printer.
        Prioritizes the exact printer requested by the print job or server configuration.
        """
        installed = self.get_installed_printers()
        installed_names = {p.name: p for p in installed}

        # 1. Exact match for requested printer name from job
        if requested_name and requested_name in installed_names:
            logger.info(f"Resolved job requested printer queue: '{requested_name}'")
            return installed_names[requested_name]

        # 2. Case-insensitive or substring match for requested name
        if requested_name:
            for name, p in installed_names.items():
                if requested_name.lower() in name.lower() or name.lower() in requested_name.lower():
                    logger.info(f"Resolved printer queue via match: '{name}' (requested: '{requested_name}')")
                    return p

        # 3. Explicit TARGET_PRINTER_NAME from config if set
        if self.target_name and self.target_name in installed_names:
            logger.info(f"Resolved configured target printer queue: '{self.target_name}'")
            return installed_names[self.target_name]

        # 4. Default Windows printer if physical
        for p in installed:
            if p.is_default and not p.is_virtual:
                logger.info(f"Using default system physical printer queue: '{p.name}'")
                return p

        # 5. Any installed physical printer (USB, Network/Wi-Fi)
        for p in installed:
            if not p.is_virtual:
                logger.info(f"Using available physical printer queue: '{p.name}'")
                return p

        # 6. Any installed printer (including virtual/default)
        for p in installed:
            if p.is_default:
                logger.warning(f"Using default system printer queue: '{p.name}'")
                return p

        if installed:
            return installed[0]

        return None


printer_manager = PrinterManager()

