"""Backend interface and session-local device store for Bluetooth scanning."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any

from .classifier import classify_device
from .models import BluetoothAdapter, BluetoothDevice, BluetoothEvent, ScanConfig, utc_now


EventCallback = Callable[[BluetoothEvent], None]


class BluetoothScannerError(RuntimeError):
    """User-facing Bluetooth scanner error."""

    def __init__(self, code: str, message: str, suggestion: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "suggestion": self.suggestion}


class BluetoothScannerBackend(ABC):
    """Backend contract shared by Linux BlueZ and future Windows support."""

    @abstractmethod
    def list_adapters(self) -> list[BluetoothAdapter]:
        raise NotImplementedError

    @abstractmethod
    def get_adapter_status(self, adapter_id: str | None = None) -> BluetoothAdapter:
        raise NotImplementedError

    @abstractmethod
    def start_scan(self, scan_config: ScanConfig, callback: EventCallback | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def stop_scan(self, session_id: str | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def subscribe_events(self, callback: EventCallback) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_known_devices(self, adapter_id: str | None = None) -> list[BluetoothDevice]:
        raise NotImplementedError

    @abstractmethod
    def export_session(self, format: str = "json") -> str:
        raise NotImplementedError


class DeviceStore:
    """Per-session dedupe and bounded RSSI history store."""

    def __init__(self, session_id: str, max_rssi_history: int = 100):
        self.session_id = session_id
        self.max_rssi_history = max_rssi_history
        self._devices: dict[str, BluetoothDevice] = {}
        self._address_index: dict[str, str] = {}

    def values(self) -> list[BluetoothDevice]:
        return list(self._devices.values())

    def mark_removed(self, object_path: str, when: datetime | None = None) -> BluetoothDevice | None:
        key = self._find_key_by_path(object_path)
        if not key:
            return None
        device = self._devices[key]
        device.removed = True
        device.last_seen = when or utc_now()
        device.last_event_source = "interfaces_removed"
        return classify_device(device)

    def upsert(self, incoming: BluetoothDevice, event_source: str, when: datetime | None = None) -> BluetoothDevice:
        now = when or utc_now()
        key = incoming.key()
        if not incoming.object_path:
            key = self._address_key(incoming)
        elif key not in self._devices and incoming.address:
            key = self._address_index.get(self._address_key(incoming), key)

        existing = self._devices.get(key)
        if existing is None:
            incoming.first_seen = now
            incoming.last_seen = now
            incoming.seen_count = 1
            incoming.last_event_source = event_source
            incoming.is_cached_only = event_source == "initial_cache"
            self._remember(key, incoming)
            if incoming.rssi is not None:
                incoming.rssi_history = [incoming.rssi]
            return classify_device(incoming)

        self._merge(existing, incoming, event_source, now)
        self._remember(key, existing)
        return classify_device(existing)

    def _merge(self, target: BluetoothDevice, source: BluetoothDevice, event_source: str, now: datetime) -> None:
        target.last_seen = now
        target.seen_count += 1
        target.last_event_source = event_source
        target.is_cached_only = target.is_cached_only and event_source == "initial_cache"
        target.removed = False

        for attr in (
            "object_path",
            "address",
            "address_type",
            "transport",
            "name",
            "alias",
            "icon",
            "class_of_device",
            "appearance",
            "paired",
            "connected",
            "trusted",
            "blocked",
            "legacy_pairing",
            "services_resolved",
            "rssi",
            "tx_power",
        ):
            value = getattr(source, attr)
            if value not in (None, "", [], {}):
                setattr(target, attr, value)

        for attr in (
            "uuids",
            "manufacturer_data",
            "manufacturer_ids",
            "service_data",
            "advertising_flags",
            "advertising_data",
            "raw_bluez_properties",
        ):
            value = getattr(source, attr)
            if value not in (None, [], {}):
                setattr(target, attr, value)

        if source.rssi is not None:
            target.rssi_history.append(source.rssi)
            if len(target.rssi_history) > self.max_rssi_history:
                del target.rssi_history[:-self.max_rssi_history]

    def _remember(self, key: str, device: BluetoothDevice) -> None:
        self._devices[key] = device
        if device.address:
            self._address_index[self._address_key(device)] = key

    def _address_key(self, device: BluetoothDevice) -> str:
        return f"{device.adapter_id}|addr|{device.address}|{device.address_type}"

    def _find_key_by_path(self, object_path: str) -> str | None:
        for key, device in self._devices.items():
            if device.object_path == object_path:
                return key
        return None


def devices_from_iterable(items: Iterable[BluetoothDevice]) -> list[dict[str, Any]]:
    return [device.to_dict() for device in items]

