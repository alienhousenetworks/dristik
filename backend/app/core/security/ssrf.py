"""
Dristik AI SSRF & Network Security Guard
Enforces strict zero-trust IP filtering to prevent SSRF and crawler exploits.
"""
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, Optional, List

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),    # Link-Local (AWS/GCP/Azure Metadata)
    ipaddress.ip_network("100.64.0.0/10"),     # Carrier-grade NAT
    ipaddress.ip_network("224.0.0.0/4"),       # Multicast
    ipaddress.ip_network("0.0.0.0/8"),         # Broadcast/Zero
    ipaddress.ip_network("::1/128"),           # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-Local
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "169.254.169.254",
    "instance-data",
    "metadata.azure.com",
    "fd00::",
}

def is_safe_url(target_url: str, egress_allowlist: Optional[list[str]] = None) -> Tuple[bool, str]:
    """
    Validates that a URL is safe to fetch and does not target internal infrastructure.
    Optionally enforces tenant-specific egress domain allowlist.
    Returns (is_safe, error_message).
    """
    try:
        parsed = urlparse(target_url)
        if parsed.scheme.lower() not in ["http", "https"]:
            return False, f"Invalid scheme '{parsed.scheme}'. Only http and https are allowed."
        
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: missing hostname."
        
        hostname_clean = hostname.lower().strip()
        if hostname_clean in BLOCKED_HOSTNAMES:
            return False, f"Blocked target hostname '{hostname_clean}'."

        # Tenant Egress Allowlist check (if specified)
        if egress_allowlist and "*" not in egress_allowlist:
            if not any(hostname_clean == d or hostname_clean.endswith("." + d) for d in egress_allowlist):
                return False, f"Target domain '{hostname_clean}' is not in tenant egress allowlist."

        # Check raw IP literals
        try:
            ip_obj = ipaddress.ip_address(hostname_clean)
            if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local:
                return False, f"Direct IP '{hostname_clean}' is in restricted range."
            for net in BLOCKED_IP_NETWORKS:
                if ip_obj in net:
                    return False, f"Direct IP '{hostname_clean}' is in restricted network {net}."
        except ValueError:
            pass  # It is a hostname, proceed to DNS resolution check

        # Attempt to resolve hostname to IP addresses (DNS Pinning validation)
        try:
            addr_info = socket.getaddrinfo(hostname_clean, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                for net in BLOCKED_IP_NETWORKS:
                    if ip_obj in net:
                        return False, f"Resolved IP '{ip_str}' is within restricted private range ({net})."
        except socket.gaierror:
            # Domain cannot be resolved; will fail on connection
            pass

        return True, "URL is safe"
    except Exception as e:
        return False, f"SSRF validation error: {str(e)}"

