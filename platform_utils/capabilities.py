"""
Linux capability detection and privilege escalation helpers.
Stub — populated in Phase 10 (Linux capability flow).

On Windows these functions are no-ops returning safe defaults.
"""
from .detect import IS_LINUX, IS_WINDOWS, is_admin

_CAP_NET_ADMIN = 12
_CAP_NET_RAW = 13


def _linux_has_cap(cap_bit: int) -> bool:
    """Read CapEff from /proc/self/status and check one Linux capability bit."""
    if not IS_LINUX:
        return False
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("CapEff:"):
                    effective = int(line.split(":", 1)[1].strip(), 16)
                    return bool(effective & (1 << cap_bit))
    except (OSError, ValueError):
        return False
    return False


def has_net_raw() -> bool:
    """True if the process can open raw sockets (cap_net_raw or root)."""
    if IS_WINDOWS:
        return is_admin()
    return is_admin() or _linux_has_cap(_CAP_NET_RAW)


def has_net_admin() -> bool:
    """True if the process has CAP_NET_ADMIN (or is root/admin)."""
    if IS_WINDOWS:
        return is_admin()
    return is_admin() or _linux_has_cap(_CAP_NET_ADMIN)


def suggest_setcap_command() -> str:
    """Return a user-friendly setcap command for the current Python binary."""
    # TODO (Phase 10): readlink -f sys.executable and format
    return "sudo setcap cap_net_raw,cap_net_admin+eip $(readlink -f $(which python3))"


def relaunch_as_root() -> bool:
    """Relaunch the current process under pkexec. Returns False on Windows."""
    if IS_WINDOWS:
        return False
    # TODO (Phase 10): use pkexec with DISPLAY/XAUTHORITY env passthrough
    return False
