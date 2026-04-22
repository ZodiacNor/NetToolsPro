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
_IFACE_RE = re.compile(
    r"^(?P<index>\d+):\s+(?P<name>[^:]+):\s+<(?P<flags>[^>]*)>.*?\bmtu\s+"
    r"(?P<mtu>\d+).*?\bstate\s+(?P<state>\S+)",
)
_LINK_RE = re.compile(r"^\s+link/\S+\s+(?P<mac>[0-9a-f:]{17})\b", re.I)
_INET_RE = re.compile(r"^\s+inet\s+(?P<ip>\d+\.\d+\.\d+\.\d+)/(?P<prefix>\d+)\b")
_USERS_NAME_RE = re.compile(r'users:\(\("([^"]+)"')
_USERS_PID_RE = re.compile(r"pid=(\d+)")


def _prefix_to_netmask(prefix: str) -> str:
    try:
        bits = int(prefix)
    except (TypeError, ValueError):
        return ""
    if bits < 0 or bits > 32:
        return ""
    mask = (0xFFFFFFFF << (32 - bits)) & 0xFFFFFFFF if bits else 0
    return ".".join(str((mask >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def _normalise_state(state: str) -> str:
    return {
        "ESTAB": "ESTABLISHED",
        "TIME-WAIT": "TIME_WAIT",
        "CLOSE-WAIT": "CLOSE_WAIT",
        "FIN-WAIT-1": "FIN_WAIT_1",
        "FIN-WAIT-2": "FIN_WAIT_2",
        "LAST-ACK": "LAST_ACK",
        "SYN-RECV": "SYN_RECV",
        "SYN-SENT": "SYN_SENT",
        "CLOSING": "CLOSING",
        "LISTEN": "LISTEN",
        "UNCONN": "UNCONN",
    }.get(state, state.replace("-", "_").upper())


def _split_addr_port(value: str) -> tuple[str, str]:
    value = value.strip()
    if not value:
        return "", ""
    if value in {"*", "*:*"}:
        return "*", "*"
    if value.startswith("[") and "]:" in value:
        host, _, port = value[1:].rpartition("]:")
        return host or "*", port or "*"
    host, sep, port = value.rpartition(":")
    if not sep:
        return value, ""
    return host or "*", port or "*"


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


def parse_ip_addr(output: str):
    """Parse `ip addr` output into interface dicts for the fallback UI path.

    >>> parse_ip_addr("2: enp3s0: <BROADCAST,MULTICAST,UP> mtu 1500 state UP\\n    link/ether aa:bb:cc:dd:ee:ff\\n    inet 192.168.1.50/24")
    [{'name': 'enp3s0', 'status': 'UP', 'state': 'UP', 'mtu': '1500', 'mac': 'AA:BB:CC:DD:EE:FF', 'ipv4': '192.168.1.50', 'prefix': '24', 'netmask': '255.255.255.0'}]
    """
    interfaces, current = [], None
    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        match = _IFACE_RE.match(line)
        if match:
            if current:
                interfaces.append(current)
            flags = {flag.strip() for flag in match.group("flags").split(",") if flag.strip()}
            state = match.group("state").upper()
            current = {
                "name": match.group("name"),
                "status": "UP" if "UP" in flags or state == "UP" else state,
                "state": state,
                "mtu": match.group("mtu"),
                "mac": "",
                "ipv4": "",
                "prefix": "",
                "netmask": "",
            }
            continue
        if not current:
            continue
        match = _LINK_RE.match(line)
        if match:
            current["mac"] = match.group("mac").upper()
            continue
        match = _INET_RE.match(line)
        if match and not current["ipv4"]:
            current["ipv4"] = match.group("ip")
            current["prefix"] = match.group("prefix")
            current["netmask"] = _prefix_to_netmask(match.group("prefix"))
    if current:
        interfaces.append(current)
    return interfaces


def parse_ss_anop(output: str):
    """Parse `ss -anop` output into normalised connection dicts.

    >>> parse_ss_anop('tcp LISTEN 0 4096 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=931,fd=3))')
    [{'proto': 'tcp', 'state': 'LISTEN', 'local_address': '0.0.0.0', 'local_port': '22', 'remote_address': '0.0.0.0', 'remote_port': '*', 'pid': 931, 'process': 'sshd'}]
    """
    results = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("Netid "):
            continue
        parts = line.split(None, 6)
        if len(parts) < 6 or parts[0].lower() not in {"tcp", "udp"}:
            continue
        local_addr, local_port = _split_addr_port(parts[4])
        remote_addr, remote_port = _split_addr_port(parts[5])
        users = parts[6] if len(parts) > 6 else ""
        name_match = _USERS_NAME_RE.search(users)
        pid_match = _USERS_PID_RE.search(users)
        results.append({
            "proto": parts[0].lower(),
            "state": _normalise_state(parts[1]),
            "local_address": local_addr,
            "local_port": local_port,
            "remote_address": remote_addr,
            "remote_port": remote_port,
            "pid": int(pid_match.group(1)) if pid_match else None,
            "process": name_match.group(1) if name_match else "",
        })
    return results
