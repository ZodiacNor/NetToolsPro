"""
Linux capability detection and privilege escalation helpers.
Stub — populated in Phase 10 (Linux capability flow).

On Windows these functions are no-ops returning safe defaults.
"""
from .detect import IS_LINUX, IS_WINDOWS, is_admin


def has_net_raw() -> bool:
    """True if the process can open raw sockets (cap_net_raw or root)."""
    if IS_WINDOWS:
        return is_admin()
    # TODO (Phase 10): parse /proc/self/status CapEff bits for CAP_NET_RAW
    return is_admin()


def has_net_admin() -> bool:
    """True if the process has CAP_NET_ADMIN (or is root/admin)."""
    if IS_WINDOWS:
        return is_admin()
    # TODO (Phase 10): parse /proc/self/status CapEff bits for CAP_NET_ADMIN
    return is_admin()


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
