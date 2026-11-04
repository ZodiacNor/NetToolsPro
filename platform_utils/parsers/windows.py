"""
Parsers for output of Windows command-line tools:
ipconfig, netstat, route print, arp -a.
"""
import re


_ARP_RE = re.compile(
    r"\s+(\d+\.\d+\.\d+\.\d+)\s+"
    r"([0-9a-f]{2}[:-](?:[0-9a-f]{2}[:-]){4}[0-9a-f]{2})\s+(\w+)",
    re.I,
)


def parse_arp_cache(output: str):
    """Parse `arp -a` output → list of (ip, mac) tuples (MAC normalised to colons)."""
    results = []
    for line in output.splitlines():
        m = _ARP_RE.match(line)
        if m:
            ip, mac, type_ = m.groups()
            if type_.lower() != "invalid":
                results.append((ip, mac.upper().replace("-", ":")))
    return results


def parse_arp_single(output: str, ip: str):
    """Extract MAC for a single IP from `arp -a <ip>` output. Returns MAC str or None."""
    for address, mac in parse_arp_cache(output):
        if address == ip:
            return mac
    return None


def parse_default_gateway(output: str, adapter_ip: str = "") -> str:
    """
    Parse `route print -4` output and return the default gateway.
    If adapter_ip is provided, prefer the route whose interface matches it.
    """
    routes = []
    for line in output.splitlines():
        parts = line.split()
        if (len(parts) >= 5 and parts[:2] == ["0.0.0.0", "0.0.0.0"]
                and parts[2] not in ("0.0.0.0", "On-link") and parts[4].isdigit()):
            routes.append((parts[2], parts[3], int(parts[4])))
    matching = [route for route in routes if route[1] == adapter_ip] if adapter_ip else []
    candidates = matching or routes
    return min(candidates, key=lambda route: route[2])[0] if candidates else ""
