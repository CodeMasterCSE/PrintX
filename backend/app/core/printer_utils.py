import re
import socket
from typing import Optional


def extract_ip_from_port(port_name: str) -> Optional[str]:
    """Extracts IPv4 address from Windows port strings (e.g. 'IP_192.168.29.9' or 'http://192.168.29.9:3911/')."""
    if not port_name:
        return None
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', port_name)
    return match.group(1) if match else None


def is_network_printer_reachable(port_name: str, timeout: float = 0.5) -> bool:
    """
    Checks if a network printer is reachable via RAW port 9100, IPP port 631, or HTTP port 80/443.
    Overrides false-positive PRINTER_STATUS_OFFLINE flags caused by Windows WSD / SNMP probing failures.
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

