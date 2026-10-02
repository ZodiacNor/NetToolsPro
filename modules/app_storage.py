"""Durable user settings, with conservative migration from portable builds."""
import json
import os
from pathlib import Path
import sys
import tempfile


class StorageError(Exception):
    """A saved file could not be read or safely replaced."""


def data_directory():
    """Never store user data in a PyInstaller extraction directory."""
    override = os.environ.get("NETTOOLS_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "NetTools Pro"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "NetTools Pro"
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    if not base.is_absolute():
        base = Path.home() / ".config"
    return base / "nettools-pro"


def legacy_paths(filename, source_file):
    """Consider only known application locations, never the working directory."""
    if os.environ.get("NETTOOLS_DATA_DIR"):
        return []  # Explicit isolation must not import real favorites.
    directories = [Path(source_file).resolve().parent]
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        directories.insert(0, executable_dir)
        if executable_dir.name == "dist":
            directories.insert(1, executable_dir.parent)
    return list(dict.fromkeys(directory / filename for directory in directories))


def valid_settings(value):
    return (isinstance(value, dict)
            and value.get("theme", "dark") in ("dark", "light", "system")
            and isinstance(value.get("minimize_to_tray", True), bool))


def valid_favorites(value):
    return isinstance(value, list) and all(
        isinstance(row, dict)
        and all(isinstance(row.get(key), str) for key in ("id", "name", "type", "value"))
        and isinstance(row.get("notes", ""), str)
        for row in value
    )


class JsonStore:
    """Atomic JSON writes; corrupt source files remain untouched for recovery."""

    def __init__(self, path, default_factory, validator, legacy=()):
        self.path = Path(path)
        self.default_factory = default_factory
        self.validator = validator
        self.legacy = list(legacy)
        self._read_failed = False

    def load(self):
        self._read_failed = False
        source = self.path
        try:
            if not source.exists():
                source = next((Path(p) for p in self.legacy if Path(p).exists()), None)
            if source is None:
                return self.default_factory()
            value = json.loads(source.read_text(encoding="utf-8"))
            if not self.validator(value):
                raise ValueError("Invalid data structure")
            if source != self.path:
                self.save(value)
            return value
        except (OSError, ValueError, TypeError, StorageError):
            self._read_failed = True
            raise StorageError(
                f"Cannot load {self.path.name}. The original file has been preserved. "
                f"Check the saved JSON file before saving again: {source}"
            ) from None

    def save(self, value):
        if self._read_failed:
            raise StorageError(f"Saving {self.path.name} is blocked to protect an unreadable file. "
                               "Repair or move the original file, then restart NetTools Pro.")
        if not self.validator(value):
            raise StorageError(f"Invalid data for {self.path.name}; nothing was saved.")
        temporary = None
        try:
            payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=f".{self.path.name}.", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except (OSError, TypeError, ValueError):
            raise StorageError(f"Cannot save {self.path.name}. Check free space and permissions in "
                               f"{self.path.parent}. Your previous saved file was not replaced.") from None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass  # Do not hide the original storage error.
