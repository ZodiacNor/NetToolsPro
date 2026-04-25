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
    for line in output.splitlines():
        if ip in line:
            m = re.search(
                r"([0-9a-f]{2}[:-](?:[0-9a-f]{2}[:-]){4}[0-9a-f]{2})",
                line, re.I,
            )
            if m:
                return m.group(1).upper().replace("-", ":")
    return None


def parse_default_gateway(output: str, adapter_ip: str = "") -> str:
    """
    Parse `route print -4` output and return the default gateway.
    If adapter_ip is provided, prefer the route whose interface matches it.
    """
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "0.0.0.0":
            gw   = parts[2]
            iface = parts[4] if len(parts) > 4 else ""
            if adapter_ip and (
                iface == adapter_ip
                or (gw != "0.0.0.0" and gw.startswith(adapter_ip.rsplit(".", 1)[0]))
            ):
                return gw
    for line in output.splitlines():
        parts = line.split()
        if (len(parts) >= 4 and parts[0] == "0.0.0.0"
                and parts[2] not in ("0.0.0.0", "")):
            return parts[2]
    return ""
