"""Shared data models for the Bluetooth Scanner module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


MODULE_VERSION = "0.1.0"


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def isoformat(value: datetime | None) -> str:
    """Serialize timestamps in a stable, export-friendly format."""
    return value.isoformat(timespec="seconds") if value else ""


@dataclass(slots=True)
class ScanConfig:
    """User-selected scan options."""

    adapter_id: str | None = None
    transport: str = "auto"
    duration_seconds: int | None = 30
    rssi_threshold: int | None = None
    duplicate_data: bool = True
    include_cached: bool = True
    include_paired: bool = True
    continuous: bool = False
    ui_update_interval_ms: int = 250
    session_label: str | None = None

    def normalized_transport(self) -> str:
        transport = (self.transport or "auto").lower().strip()
        return transport if transport in {"auto", "le", "bredr"} else "auto"

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "transport": self.normalized_transport(),
            "duration_seconds": self.duration_seconds,
            "rssi_threshold": self.rssi_threshold,
            "duplicate_data": self.duplicate_data,
            "include_cached": self.include_cached,
            "include_paired": self.include_paired,
            "continuous": self.continuous,
            "ui_update_interval_ms": self.ui_update_interval_ms,
            "session_label": self.session_label,
        }


@dataclass(slots=True)
class BluetoothAdapter:
    """Normalized BlueZ adapter status."""

    adapter_id: str
    object_path: str
    address: str = ""
    name: str = ""
    alias: str = ""
    powered: bool = False
    discovering: bool = False
    pairable: bool = False
    discoverable: bool = False
    roles: list[str] = field(default_factory=list)
    uuids: list[str] = field(default_factory=list)
    modalias: str = ""
    discovery_filters: list[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        label = self.alias or self.name or self.adapter_id
        return f"{self.adapter_id} - {label}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "object_path": self.object_path,
            "address": self.address,
            "name": self.name,
            "alias": self.alias,
            "powered": self.powered,
            "discovering": self.discovering,
            "pairable": self.pairable,
            "discoverable": self.discoverable,
            "roles": list(self.roles),
            "uuids": list(self.uuids),
            "modalias": self.modalias,
            "discovery_filters": list(self.discovery_filters),
        }


@dataclass(slots=True)
class BluetoothDevice:
    """Normalized Bluetooth device discovered via BlueZ Device1."""

    id: str
    session_id: str
    adapter_id: str
    object_path: str = ""
    address: str = ""
    address_type: str = "unknown"
    transport: str = "unknown"
    name: str = ""
    alias: str = ""
    display_name: str = ""
    icon: str = ""
    class_of_device: int | None = None
    appearance: int | None = None
    uuids: list[str] = field(default_factory=list)
    paired: bool = False
    connected: bool = False
    trusted: bool = False
    blocked: bool = False
    legacy_pairing: bool = False
    services_resolved: bool = False
    rssi: int | None = None
    tx_power: int | None = None
    manufacturer_data: dict[str, str] = field(default_factory=dict)
    manufacturer_ids: list[str] = field(default_factory=list)
    service_data: dict[str, str] = field(default_factory=dict)
    advertising_flags: list[int] = field(default_factory=list)
    advertising_data: dict[str, str] = field(default_factory=dict)
    first_seen: datetime = field(default_factory=utc_now)
    last_seen: datetime = field(default_factory=utc_now)
    seen_count: int = 0
    last_event_source: str = "initial_cache"
    is_cached_only: bool = False
    is_paired_known: bool = False
    classification: str = "unknown_bluetooth_device"
    confidence: str = "unknown"
    notes: list[str] = field(default_factory=list)
    badges: list[str] = field(default_factory=list)
    rssi_history: list[int] = field(default_factory=list)
    removed: bool = False
    raw_bluez_properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, session_id: str, adapter_id: str, object_path: str = "") -> "BluetoothDevice":
        return cls(id=str(uuid4()), session_id=session_id, adapter_id=adapter_id, object_path=object_path)

    def key(self) -> str:
        if self.object_path:
            return f"{self.adapter_id}|path|{self.object_path}"
        return f"{self.adapter_id}|addr|{self.address}|{self.address_type}"

    def to_dict(self, include_raw: bool = True) -> dict[str, Any]:
        data = {
            "id": self.id,
            "session_id": self.session_id,
            "adapter_id": self.adapter_id,
            "object_path": self.object_path,
            "address": self.address,
            "address_type": self.address_type,
            "transport": self.transport,
            "name": self.name,
            "alias": self.alias,
            "display_name": self.display_name,
            "icon": self.icon,
            "class_of_device": self.class_of_device,
            "appearance": self.appearance,
            "uuids": list(self.uuids),
            "paired": self.paired,
            "connected": self.connected,
            "trusted": self.trusted,
            "blocked": self.blocked,
            "legacy_pairing": self.legacy_pairing,
            "services_resolved": self.services_resolved,
            "rssi": self.rssi,
            "tx_power": self.tx_power,
            "manufacturer_data": dict(self.manufacturer_data),
            "manufacturer_ids": list(self.manufacturer_ids),
            "service_data": dict(self.service_data),
            "advertising_flags": list(self.advertising_flags),
            "advertising_data": dict(self.advertising_data),
            "first_seen": isoformat(self.first_seen),
            "last_seen": isoformat(self.last_seen),
            "seen_count": self.seen_count,
            "last_event_source": self.last_event_source,
            "is_cached_only": self.is_cached_only,
            "is_paired_known": self.is_paired_known,
            "classification": self.classification,
            "confidence": self.confidence,
            "notes": list(self.notes),
            "badges": list(self.badges),
            "rssi_history": list(self.rssi_history),
            "removed": self.removed,
        }
        if include_raw:
            data["raw_bluez_properties"] = dict(self.raw_bluez_properties)
        return data


@dataclass(slots=True)
class BluetoothEvent:
    """Backend-to-UI event object."""

    event_type: str
    session_id: str = ""
    device: BluetoothDevice | None = None
    adapter: BluetoothAdapter | None = None
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
