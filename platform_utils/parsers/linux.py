"""
Parsers for output of Linux command-line tools:
ip addr, ip route, ip neigh, ss -anop.
"""
import re


_NEIGH_CACHE_RE = re.compile(
    r"""^(?P<ip>\d+\.\d+\.\d+\.\d+)\s+.*?\blladdr\s+
        (?P<mac>[0-9a-f]{2}(?::[0-9a-f]{2}){5})\b.*?\b
        (?P<state>REACHABLE|STALE|DELAY|PROBE|PERMANENT|NOARP)\b""",
    re.I | re.VERBOSE,
)
_NEIGH_SINGLE_RE = re.compile(
    r"""^(?P<ip>\d+\.\d+\.\d+\.\d+)\s+.*?\blladdr\s+
        (?P<mac>[0-9a-f]{2}(?::[0-9a-f]{2}){5})\b""",
    re.I | re.VERBOSE,
)
_ROUTE_RE = re.compile(r"^default\s+via\s+(?P<gw>\d+\.\d+\.\d+\.\d+)\b")


def _prefix24(ip: str) -> str:
    parts = ip.split(".")
    return ".".join(parts[:3]) if len(parts) == 4 and all(part.isdigit() for part in parts) else ""


def parse_arp_cache(output: str):
    """Parse `ip neigh` output into `(ip, mac)` tuples with uppercase MACs.

    >>> parse_arp_cache("192.168.1.1 dev enp3s0 lladdr aa:bb:cc:dd:ee:ff REACHABLE")
    [('192.168.1.1', 'AA:BB:CC:DD:EE:FF')]
    """
    results = []
    for line in output.splitlines():
        match = _NEIGH_CACHE_RE.match(line.strip())
        if match:
            results.append((match.group("ip"), match.group("mac").upper()))
    return results


def parse_arp_single(output: str, ip: str):
    """Parse `ip neigh show <ip>` and return the matching MAC or `None`.

    >>> parse_arp_single("192.168.1.1 dev enp3s0 lladdr aa:bb:cc:dd:ee:ff REACHABLE", "192.168.1.1")
    'AA:BB:CC:DD:EE:FF'
    """
    for line in output.splitlines():
        match = _NEIGH_SINGLE_RE.match(line.strip())
        if match and match.group("ip") == ip:
            return match.group("mac").upper()
    return None


def parse_default_gateway(output: str, adapter_ip: str = "") -> str:
    """Parse `ip -4 route show default` and return the best-matching gateway.

    >>> parse_default_gateway("default via 192.168.1.1 dev enp3s0 proto dhcp metric 100")
    '192.168.1.1'
    """
    gateways = []
    for line in output.splitlines():
        match = _ROUTE_RE.match(line.strip())
        if match:
            gateways.append(match.group("gw"))
    if not gateways:
        return ""
    prefix = _prefix24(adapter_ip)
    if prefix:
        for gateway in gateways:
            if gateway.startswith(prefix + "."):
                return gateway
    return gateways[0]
