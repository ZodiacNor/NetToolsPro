"""
Network-command wrappers.  All platform-specific subprocess calls for
network diagnostics live here.

Phase 2 (this file): Windows branch fully implemented.
Phase 7:             Linux branch implementation (currently raises NotImplementedError
                     or returns empty results).
"""
import shutil
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
    traceroute_bin = shutil.which("traceroute")
    if not traceroute_bin:
        raise FileNotFoundError(
            "Traceroute is not installed on Linux. Install the 'traceroute' package and try again."
        )
    cmd = [traceroute_bin]
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


def interface_details():
    """Return normalized Linux interface details, or None on other platforms."""
    if not IS_LINUX:
        return None
    try:
        out = subprocess.check_output(
            ["ip", "addr"], text=True, timeout=5, stderr=subprocess.DEVNULL,
        )
        return _lin.parse_ip_addr(out)
    except Exception:
        return []


# ── Active connections / netstat ──────────────────────────────────────────────

def netstat_command() -> list:
    """Build the command to list active connections (parsed by caller)."""
    if IS_WINDOWS:
        return ["netstat", "-ano"]
    return ["ss", "-anop"]


def connection_details():
    """Return normalized Linux connection details, or None on other platforms."""
    if not IS_LINUX:
        return None
    try:
        out = subprocess.check_output(
            ["ss", "-anop"], text=True, timeout=8, stderr=subprocess.DEVNULL,
        )
        return _lin.parse_ss_anop(out)
    except Exception:
        return []


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


# ── arp-scan (Linux) ─────────────────────────────────────────────────────────

def arp_scan_available() -> bool:
    """Return True if the arp-scan binary is installed and available in PATH."""
    return shutil.which("arp-scan") is not None


def arp_scan_binary() -> str | None:
    """Return the full path to the arp-scan binary, or None."""
    return shutil.which("arp-scan")


def arp_scan_scan(interface: str | None = None,
                  cidr: str | None = None,
                  timeout_s: int = 60):
    """Run arp-scan and yield raw lines.

    Yields one string per response line from `arp-scan --plain --format=...`.
    The caller is responsible for parsing lines via parse_arp_scan_line().

    This function requires root or CAP_NET_RAW. Errors are handled by raising
    PermissionError / FileNotFoundError / subprocess.CalledProcessError upward;
    the caller (backend) transforms them into user-facing messages.

    Args:
        interface: e.g. "enp3s0". None -> arp-scan auto-selects.
        cidr: e.g. "192.168.1.0/24". None -> uses --localnet.
        timeout_s: hard timeout before the process is killed.

    Raises:
        FileNotFoundError: arp-scan is not installed.
        PermissionError: missing capabilities/root.
        subprocess.TimeoutExpired: if timeout is reached and the process does not exit cleanly.
    """
    binary = arp_scan_binary()
    if not binary:
        raise FileNotFoundError(
            "arp-scan is not installed. "
            "On Ubuntu/Debian: sudo apt install arp-scan. "
            "On Fedora: sudo dnf install arp-scan."
        )

    cmd = [
        binary,
        "--plain",
        "--ignoredups",
        "--format=${ip}\\t${mac}\\t${vendor}",
    ]
    if interface:
        cmd.append(f"--interface={interface}")
    if cidr:
        cmd.append(cidr)
    else:
        cmd.append("--localnet")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            yield line.rstrip("\n")
        proc.wait(timeout=timeout_s)

        if proc.returncode != 0:
            stderr_text = ""
            if proc.stderr:
                stderr_text = proc.stderr.read() or ""
            stderr_lower = stderr_text.lower()
            if (
                "root" in stderr_lower
                or "permission" in stderr_lower
                or "operation not permitted" in stderr_lower
                or "cap_net_raw" in stderr_lower
            ):
                raise PermissionError(
                    "arp-scan is missing CAP_NET_RAW or root privileges."
                )
            raise subprocess.CalledProcessError(
                proc.returncode, cmd, output="", stderr=stderr_text
            )
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)
        raise
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()


def parse_arp_scan_line(line: str) -> dict | None:
    """Parse one line from arp-scan --plain --format output into a dict.

    Expected format:
        192.168.1.1\tAA:BB:CC:DD:EE:FF\tVendor Name

    Returns:
        dict with keys: ip, mac, vendor
        or None if the line is not a valid data line.
    """
    line = line.strip()
    if not line:
        return None

    parts = line.split("\t", 2)
    if len(parts) < 2:
        parts = line.split(None, 2)
    if len(parts) < 2:
        return None

    ip = parts[0].strip()
    mac = parts[1].strip()
    if ip.count(".") != 3:
        return None
    if mac.count(":") != 5:
        return None

    vendor = parts[2].strip() if len(parts) >= 3 and parts[2].strip() else "Unknown vendor"

    return {
        "ip": ip,
        "mac": mac.upper(),
        "vendor": vendor,
    }
