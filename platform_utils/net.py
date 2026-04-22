"""
Network-command wrappers.  All platform-specific subprocess calls for
network diagnostics live here.

Phase 2 (this file): Windows branch fully implemented.
Phase 7:             Linux branch implementation (currently raises NotImplementedError
                     or returns empty results).
"""
import subprocess
from .detect import IS_WINDOWS, IS_LINUX, SUBPROCESS_FLAGS
from .parsers import windows as _win
from .parsers import linux as _lin


# ── Ping ──────────────────────────────────────────────────────────────────────

def ping_command(target: str, count: int = 4, size: int = 32,
                 ttl: int = 128, timeout_ms: int = 1000) -> list:
    """Build a ping command list (platform-native flags)."""
    if IS_WINDOWS:
        return ["ping", "-n", str(count), "-l", str(size),
                "-i", str(ttl), "-w", str(timeout_ms), target]
    # Linux: -c count, -s size, -t ttl, -W seconds
    return ["ping", "-c", str(count), "-s", str(size),
            "-t", str(ttl), "-W", str(max(1, timeout_ms // 1000)), target]


def ping_once_command(target: str, timeout_ms: int = 500,
                      size: int | None = None, ttl: int | None = None,
                      df: bool = False) -> list:
    """Build a single-ping command (used by scanners and the Ping tool)."""
    if IS_WINDOWS:
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms)]
        if size is not None:
            cmd += ["-l", str(size)]
        if ttl is not None:
            cmd += ["-i", str(ttl)]
        if df:
            cmd.insert(1, "-f")
        cmd.append(str(target))
        return cmd
    # Linux: ping -c 1 -W <s> [-s size] [-t ttl] [-M do]
    cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000))]
    if size is not None:
        cmd += ["-s", str(size)]
    if ttl is not None:
        cmd += ["-t", str(ttl)]
    if df:
        cmd += ["-M", "do"]
    cmd.append(str(target))
    return cmd


def ping_once(target: str, timeout_ms: int = 500) -> bool:
    """Send a single ping; return True if the host replied."""
    try:
        r = subprocess.run(
            ping_once_command(target, timeout_ms),
            capture_output=True,
            creationflags=SUBPROCESS_FLAGS,
            timeout=max(2, timeout_ms / 1000 + 1),
        )
        return r.returncode == 0
    except Exception:
        return False


# ── Traceroute ────────────────────────────────────────────────────────────────

def traceroute_command(target: str, max_hops: int = 30,
                       timeout_ms: int = 1000, resolve: bool = False) -> list:
    """Build a traceroute command list (Windows: tracert, Linux: traceroute)."""
    if IS_WINDOWS:
        cmd = ["tracert"]
        if not resolve:
            cmd.append("-d")
        cmd += ["-h", str(max_hops), "-w", str(timeout_ms), target]
        return cmd
    # Linux
    cmd = ["traceroute"]
    if not resolve:
        cmd.append("-n")
    cmd += ["-m", str(max_hops), "-w", str(max(1, timeout_ms // 1000)), target]
    return cmd


# ── Interface / ipconfig ──────────────────────────────────────────────────────

def ipconfig_command() -> list:
    """Build the command to dump all interface info (parsed by caller)."""
    if IS_WINDOWS:
        return ["ipconfig", "/all"]
    # Linux: caller should run multiple (ip addr, ip link) — phase 7 will return
    # a wrapper. For now, raise to make regressions visible.
    return ["ip", "addr"]


# ── Active connections / netstat ──────────────────────────────────────────────

def netstat_command() -> list:
    """Build the command to list active connections (parsed by caller)."""
    if IS_WINDOWS:
        return ["netstat", "-ano"]
    return ["ss", "-anop"]


# ── ARP ───────────────────────────────────────────────────────────────────────

def arp_command(*args) -> list:
    """Build a raw arp command list with optional extra args."""
    return ["arp", *args]


def arp_table() -> list:
    """Return a list of (ip, mac) tuples from the system ARP cache."""
    try:
        if IS_WINDOWS:
            out = subprocess.check_output(
                ["arp", "-a"], text=True, stderr=subprocess.DEVNULL,
                creationflags=SUBPROCESS_FLAGS, timeout=5,
            )
            return _win.parse_arp_cache(out)
        # Linux
        out = subprocess.check_output(
            ["ip", "neigh"], text=True, stderr=subprocess.DEVNULL, timeout=5,
        )
        return _lin.parse_arp_cache(out)
    except Exception:
        return []


def arp_lookup(ip: str):
    """Return the MAC for a single IP, or None."""
    try:
        if IS_WINDOWS:
            res = subprocess.run(
                ["arp", "-a", str(ip)], capture_output=True, text=True,
                timeout=4, creationflags=SUBPROCESS_FLAGS,
            )
            return _win.parse_arp_single(res.stdout, str(ip))
        res = subprocess.run(
            ["ip", "neigh", "show", str(ip)],
            capture_output=True, text=True, timeout=4,
        )
        return _lin.parse_arp_single(res.stdout, str(ip))
    except Exception:
        return None


# ── Routing ───────────────────────────────────────────────────────────────────

def default_gateway(adapter_ip: str = "") -> str:
    """Return the default gateway IP for the given adapter (empty string on failure)."""
    try:
        if IS_WINDOWS:
            out = subprocess.check_output(
                ["route", "print", "-4"],
                creationflags=SUBPROCESS_FLAGS, timeout=5,
            ).decode(errors="ignore")
            return _win.parse_default_gateway(out, adapter_ip)
        out = subprocess.check_output(
            ["ip", "-4", "route", "show", "default"],
            text=True, timeout=5,
        )
        return _lin.parse_default_gateway(out, adapter_ip)
    except Exception:
        return ""


def default_gateway_output() -> str:
    """Raw command output used by dashboard's `route print 0.0.0.0` probe."""
    try:
        if IS_WINDOWS:
            return subprocess.check_output(
                ["route", "print", "0.0.0.0"],
                creationflags=SUBPROCESS_FLAGS, text=True, timeout=5,
            )
        return subprocess.check_output(
            ["ip", "-4", "route", "show", "default"],
            text=True, timeout=5,
        )
    except Exception:
        return ""
