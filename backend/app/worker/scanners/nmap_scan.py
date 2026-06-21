"""nmap port/service scanner.

Runs nmap with service/version detection and parses the XML output into
normalized finding dicts (one per open port). Open ports are informational by
default; well-known risky/plaintext services are flagged ``low``.
"""

from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET

from app.config import settings

# Plaintext / commonly-risky services worth surfacing above "info".
RISKY_SERVICES = {
    "telnet": "Telnet exposes credentials in cleartext.",
    "ftp": "FTP transmits credentials and data in cleartext.",
    "rlogin": "rlogin is insecure and should be disabled.",
    "vnc": "Exposed VNC can allow remote control if weakly authenticated.",
    "rdp": "Exposed RDP is a frequent ransomware entry point.",
    "smb": "Exposed SMB/file sharing should not face the internet.",
    "microsoft-ds": "Exposed SMB/file sharing should not face the internet.",
    "mysql": "Databases should not be directly internet-exposed.",
    "postgresql": "Databases should not be directly internet-exposed.",
    "mongodb": "Databases should not be directly internet-exposed.",
    "redis": "Exposed Redis is frequently abused; bind to localhost.",
}


def available() -> bool:
    return shutil.which("nmap") is not None


def run(address: str) -> tuple[list[dict], str]:
    """Return (findings, raw_xml)."""
    if not available():
        raise RuntimeError("nmap is not installed in the worker image")

    args = settings.nmap_default_args.split()
    cmd = ["nmap", *args, "-oX", "-", address]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=settings.scan_timeout_seconds,
    )
    raw = proc.stdout
    findings = _parse(raw)
    return findings, raw


def _parse(xml_text: str) -> list[dict]:
    findings: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return findings

    for host in root.findall("host"):
        addr_el = host.find("address")
        host_addr = addr_el.get("addr") if addr_el is not None else None
        ports_el = host.find("ports")
        if ports_el is None:
            continue
        for port in ports_el.findall("port"):
            state = port.find("state")
            if state is None or state.get("state") != "open":
                continue
            port_num = int(port.get("portid"))
            service_el = port.find("service")
            service_name = service_el.get("name") if service_el is not None else "unknown"
            product = service_el.get("product") if service_el is not None else None
            version = service_el.get("version") if service_el is not None else None
            banner = " ".join(filter(None, [product, version]))

            severity = "info"
            description = f"Open port {port_num}/{port.get('protocol')} ({service_name})."
            remediation = None
            risky = RISKY_SERVICES.get((service_name or "").lower())
            if risky:
                severity = "low"
                remediation = "Restrict access via firewall/VPN or disable the service."
                description = f"{description} {risky}"

            findings.append(
                {
                    "title": f"{service_name} on port {port_num}",
                    "description": description + (f" Banner: {banner}." if banner else ""),
                    "severity": severity,
                    "host": host_addr,
                    "port": port_num,
                    "service": service_name,
                    "source": "nmap",
                    "remediation": remediation,
                }
            )
    return findings
