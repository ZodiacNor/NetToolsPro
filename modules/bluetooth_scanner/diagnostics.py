"""Fedora/Linux diagnostics for Bluetooth Scanner."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from .linux_bluez_backend import LinuxBlueZBackend
from .scanner_core import BluetoothScannerError


@dataclass(slots=True)
class DiagnosticReport:
    bluez_service_available: str = "unknown"
    bluetooth_service_active: str = "unknown"
    adapters: list[str] = field(default_factory=list)
    powered: str = "unknown"
    discovering: str = "unknown"
    roles: list[str] = field(default_factory=list)
    discovery_filters: list[str] = field(default_factory=list)
    rfkill: str = "unknown"
    messages: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        lines = [
            f"BlueZ service available: {self.bluez_service_available}",
            f"bluetooth.service active: {self.bluetooth_service_active}",
            f"Adapters: {', '.join(self.adapters) if self.adapters else 'none'}",
            f"Adapter powered: {self.powered}",
            f"Adapter discovering: {self.discovering}",
            f"Adapter roles: {', '.join(self.roles) if self.roles else 'unknown'}",
            f"Discovery filters: {', '.join(self.discovery_filters) if self.discovery_filters else 'unknown'}",
            f"rfkill bluetooth: {self.rfkill}",
        ]
        if self.messages:
            lines.append("")
            lines.extend(f"Message: {msg}" for msg in self.messages)
        if self.suggestions:
            lines.append("")
            lines.append("Suggested checks:")
            lines.extend(f"  {item}" for item in self.suggestions)
        return lines


def run_diagnostics(backend: LinuxBlueZBackend | None = None) -> DiagnosticReport:
    backend = backend or LinuxBlueZBackend()
    report = DiagnosticReport()
    report.bluetooth_service_active = _systemctl_is_active()
    report.rfkill = _rfkill_summary()
    try:
        adapters = backend.list_adapters()
        report.bluez_service_available = "yes"
        report.adapters = [adapter.adapter_id for adapter in adapters]
        if adapters:
            adapter = adapters[0]
            report.powered = "yes" if adapter.powered else "no"
            report.discovering = "yes" if adapter.discovering else "no"
            report.roles = adapter.roles
            report.discovery_filters = adapter.discovery_filters
        else:
            report.messages.append("BlueZ is reachable, but no Adapter1 objects were found.")
    except BluetoothScannerError as e:
        report.bluez_service_available = "no"
        report.messages.append(e.message)
        if e.suggestion:
            report.suggestions.append(e.suggestion)
    except Exception as e:
        report.bluez_service_available = "no"
        report.messages.append(str(e))

    report.suggestions.extend(
        [
            "sudo dnf install -y bluez",
            "sudo systemctl enable --now bluetooth",
            "rfkill list bluetooth",
            "bluetoothctl show",
            "busctl tree org.bluez",
            "busctl introspect org.bluez /org/bluez/hci0 org.bluez.Adapter1",
            'journalctl -u bluetooth --since "10 min ago"',
        ]
    )
    return report


def _systemctl_is_active() -> str:
    if not shutil.which("systemctl"):
        return "unknown"
    try:
        result = subprocess.run(["systemctl", "is-active", "bluetooth"], capture_output=True, text=True, timeout=3)
        value = (result.stdout or result.stderr).strip()
        if value == "active":
            return "yes"
        if value:
            return f"no ({value})"
    except Exception:
        pass
    return "unknown"


def _rfkill_summary() -> str:
    if not shutil.which("rfkill"):
        return "unknown"
    try:
        result = subprocess.run(["rfkill", "list", "bluetooth"], capture_output=True, text=True, timeout=3)
        text = (result.stdout or result.stderr).strip()
        if not text:
            return "unknown"
        if result.returncode != 0:
            return f"unknown ({text.splitlines()[0]})"
        if "Soft blocked: yes" in text or "Hard blocked: yes" in text:
            return "blocked"
        if "Soft blocked: no" in text or "Hard blocked: no" in text:
            return "not blocked"
        return "available"
    except Exception:
        return "unknown"
