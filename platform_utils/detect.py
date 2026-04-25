"""
Platform detection + basic OS primitives.
The single source of truth for IS_WINDOWS/IS_LINUX/IS_MACOS, SUBPROCESS_FLAGS
and the is_admin() check.
"""
import sys
import os
import subprocess
import ctypes

IS_WINDOWS = sys.platform == "win32"
IS_LINUX   = sys.platform.startswith("linux")
IS_MACOS   = sys.platform == "darwin"

# Hide console window on Windows when frozen; no-op elsewhere.
SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0


def is_admin() -> bool:
    """True if the current process has administrator/root privileges."""
    if IS_WINDOWS:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    # POSIX
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


def platform_name() -> str:
    if IS_WINDOWS: return "windows"
    if IS_LINUX:   return "linux"
    if IS_MACOS:   return "macos"
    return "unknown"
