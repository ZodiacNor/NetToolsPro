"""
Shell/OS integration wrappers — URLs, folders, hidden command execution.
"""
import subprocess
from .detect import IS_WINDOWS, IS_LINUX, IS_MACOS, SUBPROCESS_FLAGS


def open_url(url: str) -> None:
    """Open a URL in the user's default browser."""
    if IS_WINDOWS:
        subprocess.Popen(["cmd", "/c", "start", "", url],
                         creationflags=SUBPROCESS_FLAGS)
    elif IS_LINUX:
        subprocess.Popen(["xdg-open", url])
    elif IS_MACOS:
        subprocess.Popen(["open", url])


def open_folder(path) -> None:
    """Open a folder in the system file manager."""
    path = str(path)
    if IS_WINDOWS:
        subprocess.Popen(["explorer", path], creationflags=SUBPROCESS_FLAGS)
    elif IS_LINUX:
        subprocess.Popen(["xdg-open", path])
    elif IS_MACOS:
        subprocess.Popen(["open", path])
