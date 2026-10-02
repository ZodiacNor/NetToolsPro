"""Future Windows Bluetooth backend stub.

TODO: Windows 10/11 support should use:
- BLE: Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementWatcher
- Classic: Win32 Bluetooth APIs
"""

from __future__ import annotations

from .models import BluetoothAdapter, BluetoothDevice, ScanConfig
from .scanner_core import BluetoothScannerBackend, BluetoothScannerError, EventCallback


class WindowsBluetoothBackend(BluetoothScannerBackend):
    """Placeholder backend so the UI contract is not Linux-specific."""

    def _unsupported(self) -> BluetoothScannerError:
        return BluetoothScannerError(
            "windows_not_implemented",
            "Windows Bluetooth scanning is not implemented in this release.",
            "Use Fedora/Linux BlueZ support for now. Windows support can be added behind the same backend interface.",
        )

    def list_adapters(self) -> list[BluetoothAdapter]:
        raise self._unsupported()

    def get_adapter_status(self, adapter_id: str | None = None) -> BluetoothAdapter:
        raise self._unsupported()

    def start_scan(self, scan_config: ScanConfig, callback: EventCallback | None = None) -> str:
        raise self._unsupported()

    def stop_scan(self, session_id: str | None = None) -> None:
        raise self._unsupported()

    def subscribe_events(self, callback: EventCallback) -> None:
        raise self._unsupported()

    def get_known_devices(self, adapter_id: str | None = None) -> list[BluetoothDevice]:
        raise self._unsupported()

    def export_session(self, format: str = "json") -> str:
        raise self._unsupported()
