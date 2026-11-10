import sys
import re
import socket
from typing import Optional, Tuple


def extract_ip_from_port(port_name: str) -> Optional[str]:
    """Extracts IPv4 address from Windows port strings (e.g. 'IP_192.168.29.9' or 'http://192.168.29.9:3911/')."""
    if not port_name:
        return None
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', port_name)
    return match.group(1) if match else None


def is_network_printer_reachable(port_name: str, timeout: float = 0.5) -> bool:
    """
    Checks if a network printer is reachable via RAW port 9100, IPP port 631, or HTTP port 80/443.
    Returns False immediately if the printer is powered off or disconnected from Wi-Fi.
    """
    ip = extract_ip_from_port(port_name)
    if not ip:
        return False

    for port in (9100, 631, 80, 443):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                if s.connect_ex((ip, port)) == 0:
                    return True
        except Exception:
            pass
    return False


def is_usb_printer_connected(port_name: str = "USB001", printer_name: str = "") -> bool:
    """
    Checks if a physical USB printer is plugged in and powered on.
    Queries Windows Configuration Manager (cfgmgr32.dll) live devnode tree.
    Returns False if USB cable is unplugged or printer is powered off.
    """
    if sys.platform != "win32":
        return True

    try:
        import ctypes
        from ctypes import wintypes
        import winreg

        cfg = ctypes.windll.cfgmgr32
        base_path = r"SYSTEM\CurrentControlSet\Enum\USBPRINT"

        # Check USBPRINT registry
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path) as base_key:
            num_models = winreg.QueryInfoKey(base_key)[0]
            for i in range(num_models):
                model_name = winreg.EnumKey(base_key, i)
                model_path = f"{base_path}\\{model_name}"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, model_path) as model_key:
                    num_instances = winreg.QueryInfoKey(model_key)[0]
                    for j in range(num_instances):
                        instance_id = winreg.EnumKey(model_key, j)
                        full_dev_id = f"USBPRINT\\{model_name}\\{instance_id}"

                        match_port = port_name.upper() in instance_id.upper() or port_name.upper() in full_dev_id.upper()
                        match_name = False
                        if printer_name:
                            p_toks = [
                                tok for tok in re.findall(r'\w+', printer_name.lower())
                                if len(tok) > 2 and tok not in ("series", "printer", "the")
                            ]
                            match_name = any(tok in model_name.lower() for tok in p_toks)

                        if match_port or match_name:
                            devinst = wintypes.DWORD()
                            # CM_LOCATE_DEVNODE_NORMAL (0) locates only present/active hardware devnodes!
                            res = cfg.CM_Locate_DevNodeW(ctypes.byref(devinst), full_dev_id, 0)
                            if res == 0:  # CR_SUCCESS: device is physically present and connected
                                status = wintypes.DWORD()
                                problem = wintypes.DWORD()
                                if cfg.CM_Get_DevNode_Status(ctypes.byref(status), ctypes.byref(problem), devinst, 0) == 0:
                                    return True
    except Exception:
        pass

    return False


def get_live_printer_status(printer_name: str, port_name: str, raw_status: int = 0) -> Tuple[bool, str, str]:
    """
    Determines true physical printer health:
    Returns (is_online: bool, status_text: str, status_details: str).
    Differentiates between:
    - Truly online (responding on LAN or physically plugged into USB)
    - Truly offline (powered off, Wi-Fi unreachable, or USB unplugged)
    - Hardware warnings (paper jam, out of paper, door open)
    """
    p_name_lower = printer_name.lower()
    p_port_upper = (port_name or "").upper()

    # 1. Virtual printers (PDF, OneNote, Fax, etc.)
    VIRTUAL_NAMES = ("microsoft print to pdf", "onenote", "fax", "xps")
    if any(v in p_name_lower for v in VIRTUAL_NAMES):
        return True, "online", "Virtual Software Printer"

    # 2. USB Printers
    is_usb = "USB" in p_port_upper or "USB" in printer_name.upper()
    if is_usb:
        connected = is_usb_printer_connected(port_name, printer_name)
        if not connected:
            return False, "offline", "USB cable disconnected or printer powered off"

        # Check spooler bitflags if device is connected
        if raw_status & 0x00000008:
            return False, "paper_jam", "Paper jam detected in USB printer"
        if raw_status & (0x00000010 | 0x00000020):
            return True, "out_of_paper", "Paper tray empty"
        if raw_status & 0x00400000:
            return True, "door_open", "Printer door or cover open"
        return True, "online", "Ready via USB"

    # 3. Wi-Fi / Network Printers
    is_network = "IP_" in p_port_upper or "WSD" in p_port_upper or "." in (port_name or "")
    if is_network:
        reachable = is_network_printer_reachable(port_name)
        if not reachable:
            return False, "offline", "Printer powered off or unreachable on Wi-Fi"

        # Check spooler bitflags if reachable
        if raw_status & 0x00000008:
            return False, "paper_jam", "Paper jam detected in network printer"
        if raw_status & (0x00000010 | 0x00000020):
            return True, "out_of_paper", "Paper tray empty"
        if raw_status & 0x00400000:
            return True, "door_open", "Printer door or cover open"
        return True, "online", "Ready via Wi-Fi"

    # 4. Other / Local ports
    if raw_status & 0x00000080 or raw_status & 0x00000002:
        return False, "offline", "Printer offline or disconnected"
    return True, "online", "Ready"
