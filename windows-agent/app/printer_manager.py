import re
import socket
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


def is_network_printer_reachable(port_name: str, timeout: float = 0.5) -> bool:
    """
    Checks if a network printer is reachable via RAW port 9100, IPP port 631, or HTTP port 80.
    Overrides false-positive PRINTER_STATUS_OFFLINE flags caused by Windows WSD / SNMP probing failures.
    """
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', port_name)
    if not match:
        return False
    ip = match.group(1)
    for port in (9100, 631, 80):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                if s.connect_ex((ip, port)) == 0:
                    return True
        except Exception:
            pass
    return False


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
                    # Verify if network printer is actually online on Port 9100 / 631 (bypassing SNMP/WSD false-positives)
                    if is_network_printer_reachable(port_name):
                        status_text = "online"
                        status_details = "Ready (Direct TCP/IP)"
                        is_online = True
                    else:
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
        Includes intelligent auto-failover: if the requested queue is offline (e.g. USB unplugged),
        it seamlessly routes to an active online counterpart (e.g. Wi-Fi).
        """
        installed = self.get_installed_printers()
        installed_names = {p.name: p for p in installed}

        # 1. Exact match for requested printer name from job
        if requested_name and requested_name in installed_names:
            target = installed_names[requested_name]
            if target.is_online:
                logger.info(f"Resolved online requested printer queue: '{requested_name}'")
                return target
            else:
                logger.warning(
                    f"Requested printer '{requested_name}' is currently offline. Evaluating failover queues..."
                )

        # 2. Case-insensitive or substring match for requested name
        if requested_name:
            for name, p in installed_names.items():
                if requested_name.lower() in name.lower() or name.lower() in requested_name.lower():
                    if p.is_online:
                        logger.info(f"Resolved online printer queue via match: '{name}' (requested: '{requested_name}')")
                        return p

        # 3. Intelligent Auto-Failover: If requested printer is offline, find online physical alternative (e.g. Wi-Fi <-> USB)
        if requested_name:
            req_tokens = set(re.findall(r'\w+', requested_name.lower()))
            for name, p in installed_names.items():
                if not p.is_virtual and p.is_online:
                    cand_tokens = set(re.findall(r'\w+', name.lower()))
                    common = (req_tokens & cand_tokens) - {"series", "printer", "the", "pcl", "v4"}
                    if common:
                        logger.warning(
                            f"Auto-Failover: Requested printer '{requested_name}' is offline. Routing print job to online counterpart: '{name}'"
                        )
                        return p

        # 4. Explicit TARGET_PRINTER_NAME from config if set and online
        if self.target_name and self.target_name in installed_names and installed_names[self.target_name].is_online:
            logger.info(f"Resolved configured target printer queue: '{self.target_name}'")
            return installed_names[self.target_name]

        # 5. Default Windows printer if physical and online
        for p in installed:
            if p.is_default and not p.is_virtual and p.is_online:
                logger.info(f"Using default system physical printer queue: '{p.name}'")
                return p

        # 6. Any installed physical printer that is online (USB, Network/Wi-Fi)
        for p in installed:
            if not p.is_virtual and p.is_online:
                logger.info(f"Using available online physical printer queue: '{p.name}'")
                return p

        # 7. Fallback to requested or any installed physical printer even if spooler reported offline
        if requested_name and requested_name in installed_names:
            logger.warning(f"Using requested printer queue despite offline status: '{requested_name}'")
            return installed_names[requested_name]

        for p in installed:
            if not p.is_virtual:
                logger.warning(f"Using physical printer queue (may be offline): '{p.name}'")
                return p

        # 8. Any installed printer (including virtual/default)
        for p in installed:
            if p.is_default:
                logger.warning(f"Using default system printer queue: '{p.name}'")
                return p

        if installed:
            return installed[0]

        return None


printer_manager = PrinterManager()

