"""
Script-lab helpers — extensions, filetype filters, and command builders.
"""
import sys
import pathlib
import shutil
from .detect import IS_WINDOWS, IS_LINUX


def script_extensions() -> set:
    """Return the set of runnable script extensions for the current platform."""
    if IS_WINDOWS:
        return {".ps1", ".py", ".bat", ".cmd"}
    if IS_LINUX:
        return {".sh", ".py"}
    return {".py"}


def script_filetypes() -> list:
    """Return tkinter filedialog filetype filters for the current platform."""
    if IS_WINDOWS:
        return [
            ("Script files", "*.ps1 *.py *.bat *.cmd"),
            ("PowerShell", "*.ps1"),
            ("Python",     "*.py"),
            ("Batch",      "*.bat *.cmd"),
            ("All files",  "*.*"),
        ]
    if IS_LINUX:
        return [
            ("Script files", "*.sh *.py"),
            ("Shell",        "*.sh"),
            ("Python",       "*.py"),
            ("All files",    "*.*"),
        ]
    return [("Python", "*.py"), ("All files", "*.*")]


def default_script_extension() -> str:
    """Extension used when creating a new blank script."""
    return ".ps1" if IS_WINDOWS else ".sh"


def build_run_command(path) -> list:
    """Build the subprocess command list for running a script by extension."""
    suffix = pathlib.Path(path).suffix.lower()
    if suffix == ".py":
        if not getattr(sys, "frozen", False):
            return [sys.executable, str(path)]
        # In a frozen build sys.executable points to NetTools Pro itself.
        for name in (("py", "python", "python3") if IS_WINDOWS else ("python3", "python")):
            executable = shutil.which(name)
            if executable:
                return [executable, *(["-3"] if name == "py" else []), str(path)]
        raise FileNotFoundError("Python is not installed or is not on PATH. Install Python to run .py scripts.")
    if IS_WINDOWS:
        if suffix == ".ps1":
            return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(path)]
        if suffix in (".bat", ".cmd"):
            return ["cmd", "/c", str(path)]
        return []
    # Linux (and macOS as best-effort)
    if suffix == ".sh":
        return ["bash", str(path)]
    return []
