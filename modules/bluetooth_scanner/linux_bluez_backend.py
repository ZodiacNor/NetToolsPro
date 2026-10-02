"""Linux BlueZ D-Bus backend for Bluetooth Scanner.

Primary target: Fedora Workstation 43 with BlueZ on the system D-Bus.
The backend does not shell out to bluetoothctl for production scanning.
"""

from __future__ import annotations

import asyncio
import json
import platform
import re
import subprocess
import threading
from types import SimpleNamespace
from datetime import datetime
from uuid import uuid4
from typing import Any

from .exporter import export_csv, export_json
from .models import BluetoothAdapter, BluetoothDevice, BluetoothEvent, ScanConfig, utc_now
from .scanner_core import BluetoothScannerBackend, BluetoothScannerError, DeviceStore, EventCallback

BLUEZ_SERVICE = "org.bluez"
OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
ADAPTER_IFACE = "org.bluez.Adapter1"
DEVICE_IFACE = "org.bluez.Device1"


def _mask_address(address: str) -> str:
    if not address or ":" not in address:
        return address or "unknown"
    parts = address.split(":")
    if len(parts) < 6:
        return address
    return ":".join(parts[:3] + ["xx", "xx", parts[-1]])


class LinuxBlueZBackend(BluetoothScannerBackend):
    """BlueZ system D-Bus backend."""

    def __init__(self, app_version: str = "1.9.0"):
        self.app_version = app_version
        self._callbacks: list[EventCallback] = []
        self._active_session_id: str | None = None
        self._active_stop: threading.Event | None = None
        self._active_thread: threading.Thread | None = None
        self._active_store: DeviceStore | None = None
        self._last_config = ScanConfig()
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._bluez_version = ""
        self._lock = threading.RLock()

    def subscribe_events(self, callback: EventCallback) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def list_adapters(self) -> list[BluetoothAdapter]:
        return asyncio.run(self._list_adapters_async())

    def get_adapter_status(self, adapter_id: str | None = None) -> BluetoothAdapter:
        adapters = self.list_adapters()
        if not adapters:
            raise BluetoothScannerError(
                "adapter_missing",
                "No Bluetooth adapter was found through BlueZ.",
                "Check that bluetooth.service is active and that the adapter is not disabled in firmware or rfkill.",
            )
        selected = _select_adapter(adapters, adapter_id)
        if selected is None:
            raise BluetoothScannerError(
                "adapter_missing",
                f"Bluetooth adapter '{adapter_id}' was not found.",
                "Select another adapter or check bluetoothctl show / busctl tree org.bluez.",
            )
        return selected

    def get_known_devices(self, adapter_id: str | None = None) -> list[BluetoothDevice]:
        return asyncio.run(self._get_known_devices_async(adapter_id))

    def start_scan(self, scan_config: ScanConfig, callback: EventCallback | None = None) -> str:
        with self._lock:
            if self._active_session_id:
                raise BluetoothScannerError("scan_active", "Bluetooth scan is already active.", "Stop the active scan first.")
            session_id = str(uuid4())
            stop_event = threading.Event()
            store = DeviceStore(session_id)
            self._active_session_id = session_id
            self._active_stop = stop_event
            self._active_store = store
            self._last_config = scan_config
            self._started_at = utc_now()
            self._stopped_at = None
            if callback:
                self.subscribe_events(callback)

            thread = threading.Thread(
                target=self._scan_thread,
                args=(session_id, scan_config, stop_event, store),
                daemon=True,
            )
            self._active_thread = thread
            thread.start()
            return session_id

    def stop_scan(self, session_id: str | None = None) -> None:
        with self._lock:
            if not self._active_session_id:
                return
            if session_id and session_id != self._active_session_id:
                raise BluetoothScannerError("wrong_session", "Stop requested for a different Bluetooth scan session.")
            if self._active_stop:
                self._active_stop.set()

    def export_session(self, format: str = "json") -> str:
        devices = self._active_store.values() if self._active_store else []
        if format.lower() == "csv":
            return export_csv(devices)
        return export_json(
            app_version=self.app_version,
            scan_config=self._last_config,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            devices=devices,
            bluez_version=self._bluez_version,
        )

    def _scan_thread(self, session_id: str, config: ScanConfig, stop_event: threading.Event, store: DeviceStore) -> None:
        try:
            asyncio.run(self._scan_async(session_id, config, stop_event, store))
        except BluetoothScannerError as e:
            self._emit(BluetoothEvent("diagnostic_error", session_id=session_id, message=e.message, payload=e.to_dict()))
        except Exception as e:
            self._emit(
                BluetoothEvent(
                    "diagnostic_error",
                    session_id=session_id,
                    message=str(e),
                    payload={"code": "unexpected_error", "message": str(e)},
                )
            )
        finally:
            with self._lock:
                self._stopped_at = utc_now()
                self._active_session_id = None
                self._active_stop = None
                self._active_thread = None
            self._emit(BluetoothEvent("scan_session_stopped", session_id=session_id, payload={"stopped_at": self._stopped_at.isoformat()}))

    async def _scan_async(self, session_id: str, config: ScanConfig, stop_event: threading.Event, store: DeviceStore) -> None:
        dbus = await _dbus_import()
        self._bluez_version = get_bluez_version()
        bus, manager = await _connect_bluez(dbus)
        objects = await manager.call_get_managed_objects()
        adapters = await self._adapters_from_objects(dbus, bus, objects)
        adapter = _select_adapter(adapters, config.adapter_id)
        if adapter is None:
            self._emit(BluetoothEvent("adapter_missing", session_id=session_id, message="No matching Bluetooth adapter found."))
            raise BluetoothScannerError("adapter_missing", "No matching Bluetooth adapter found.")
        if not adapter.powered:
            raise BluetoothScannerError(
                "adapter_powered_off",
                f"Bluetooth adapter {adapter.adapter_id} is powered off.",
                "Turn Bluetooth on in Fedora Settings or bluetoothctl, then retry. Do not run the whole app as root.",
            )

        adapter_iface = await _adapter_interface(dbus, bus, adapter.object_path)
        supported_filters = await _safe_call(adapter_iface.call_get_discovery_filters, default=[])
        adapter.discovery_filters = list(supported_filters or [])
        self._emit(BluetoothEvent("adapter_found", session_id=session_id, adapter=adapter))

        filter_dict = _build_discovery_filter(dbus.Variant, config, adapter.discovery_filters)
        if filter_dict:
            try:
                await adapter_iface.call_set_discovery_filter(filter_dict)
            except Exception as e:
                self._emit(
                    BluetoothEvent(
                        "diagnostic_error",
                        session_id=session_id,
                        message=f"SetDiscoveryFilter failed: {e}",
                        payload={"code": "filter_failed", "detail": str(e)},
                    )
                )

        if config.include_cached:
            for path, ifaces in objects.items():
                if DEVICE_IFACE not in ifaces or not _path_under_adapter(path, adapter.object_path):
                    continue
                device = device_from_bluez_properties(
                    session_id=session_id,
                    adapter_id=adapter.adapter_id,
                    object_path=path,
                    properties=ifaces[DEVICE_IFACE],
                    event_source="initial_cache",
                )
                if device.paired and not config.include_paired:
                    continue
                updated = store.upsert(device, "initial_cache")
                self._emit(BluetoothEvent("device_added", session_id=session_id, device=updated))

        def on_message(message: Any) -> None:
            if getattr(message, "message_type", None) != dbus.MessageType.SIGNAL:
                return
            path = getattr(message, "path", "") or ""
            if message.interface == OBJECT_MANAGER_IFACE and message.member == "InterfacesAdded":
                obj_path, ifaces = message.body
                if not _path_under_adapter(obj_path, adapter.object_path):
                    return
                if DEVICE_IFACE in ifaces:
                    device = device_from_bluez_properties(session_id, adapter.adapter_id, obj_path, ifaces[DEVICE_IFACE], "interfaces_added")
                    updated = store.upsert(device, "interfaces_added")
                    self._emit(BluetoothEvent("device_added", session_id=session_id, device=updated))
            elif message.interface == OBJECT_MANAGER_IFACE and message.member == "InterfacesRemoved":
                obj_path, _ifaces = message.body
                if not _path_under_adapter(obj_path, adapter.object_path):
                    return
                removed = store.mark_removed(obj_path)
                if removed:
                    self._emit(BluetoothEvent("device_removed", session_id=session_id, device=removed))
            elif message.interface == PROPERTIES_IFACE and message.member == "PropertiesChanged":
                if not _path_under_adapter(path, adapter.object_path):
                    return
                iface_name, changed, _invalidated = message.body
                if iface_name == DEVICE_IFACE:
                    device = device_from_bluez_properties(session_id, adapter.adapter_id, path, changed, "properties_changed")
                    updated = store.upsert(device, "properties_changed")
                    self._emit(BluetoothEvent("device_updated", session_id=session_id, device=updated))

        bus.add_message_handler(on_message)
        await adapter_iface.call_start_discovery()
        self._emit(BluetoothEvent("scan_session_started", session_id=session_id, adapter=adapter, payload={"config": config.to_dict()}))

        try:
            deadline = None if config.continuous or not config.duration_seconds else asyncio.get_running_loop().time() + config.duration_seconds
            while not stop_event.is_set():
                if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                    break
                await asyncio.sleep(0.1)
        finally:
            try:
                await adapter_iface.call_stop_discovery()
            except Exception as e:
                self._emit(
                    BluetoothEvent(
                        "diagnostic_error",
                        session_id=session_id,
                        message=f"StopDiscovery failed: {e}",
                        payload={"code": "stop_failed", "detail": str(e)},
                    )
                )
            try:
                bus.remove_message_handler(on_message)
            except Exception:
                pass
            try:
                bus.disconnect()
            except Exception:
                pass

    async def _list_adapters_async(self) -> list[BluetoothAdapter]:
        dbus = await _dbus_import()
        bus, manager = await _connect_bluez(dbus)
        try:
            objects = await manager.call_get_managed_objects()
            return await self._adapters_from_objects(dbus, bus, objects)
        finally:
            bus.disconnect()

    async def _get_known_devices_async(self, adapter_id: str | None = None) -> list[BluetoothDevice]:
        dbus = await _dbus_import()
        bus, manager = await _connect_bluez(dbus)
        try:
            objects = await manager.call_get_managed_objects()
            adapters = await self._adapters_from_objects(dbus, bus, objects)
            selected = _select_adapter(adapters, adapter_id)
            adapter_path = selected.object_path if selected else ""
            session_id = str(uuid4())
            store = DeviceStore(session_id)
            for path, ifaces in objects.items():
                if DEVICE_IFACE not in ifaces:
                    continue
                if adapter_path and not _path_under_adapter(path, adapter_path):
                    continue
                adapter_name = _adapter_id_from_path(path)
                device = device_from_bluez_properties(session_id, adapter_name, path, ifaces[DEVICE_IFACE], "initial_cache")
                updated = store.upsert(device, "initial_cache")
            return store.values()
        finally:
            bus.disconnect()

    async def _adapters_from_objects(self, dbus: Any, bus: Any, objects: dict[str, Any]) -> list[BluetoothAdapter]:
        adapters: list[BluetoothAdapter] = []
        for path, ifaces in objects.items():
            props = ifaces.get(ADAPTER_IFACE)
            if not props:
                continue
            adapter = BluetoothAdapter(
                adapter_id=path.rsplit("/", 1)[-1],
                object_path=path,
                address=str(_unwrap(props.get("Address"), "")),
                name=str(_unwrap(props.get("Name"), "")),
                alias=str(_unwrap(props.get("Alias"), "")),
                powered=bool(_unwrap(props.get("Powered"), False)),
                discovering=bool(_unwrap(props.get("Discovering"), False)),
                pairable=bool(_unwrap(props.get("Pairable"), False)),
                discoverable=bool(_unwrap(props.get("Discoverable"), False)),
                roles=list(_unwrap(props.get("Roles"), []) or []),
                uuids=list(_unwrap(props.get("UUIDs"), []) or []),
                modalias=str(_unwrap(props.get("Modalias"), "")),
            )
            try:
                adapter_iface = await _adapter_interface(dbus, bus, path)
                adapter.discovery_filters = list(await _safe_call(adapter_iface.call_get_discovery_filters, default=[]))
            except Exception:
                adapter.discovery_filters = []
            adapters.append(adapter)
        adapters.sort(key=lambda item: (item.adapter_id != "hci0", item.adapter_id))
        return adapters

    def _emit(self, event: BluetoothEvent) -> None:
        if event.device and event.event_type in {"device_added", "device_updated"}:
            _structured_log(event.event_type, event.device.address)
        else:
            _structured_log(event.event_type)
        for callback in list(self._callbacks):
            try:
                callback(event)
            except Exception:
                pass


def device_from_bluez_properties(
    session_id: str,
    adapter_id: str,
    object_path: str,
    properties: dict[str, Any],
    event_source: str,
) -> BluetoothDevice:
    props = normalize_bluez_properties(properties)
    device = BluetoothDevice.new(session_id=session_id, adapter_id=adapter_id, object_path=object_path)
    device.address = str(props.get("Address") or "")
    device.address_type = str(props.get("AddressType") or "unknown")
    device.name = str(props.get("Name") or "")
    device.alias = str(props.get("Alias") or "")
    device.icon = str(props.get("Icon") or "")
    device.class_of_device = _int_or_none(props.get("Class"))
    device.appearance = _int_or_none(props.get("Appearance"))
    device.uuids = list(props.get("UUIDs") or [])
    device.paired = bool(props.get("Paired", False))
    device.connected = bool(props.get("Connected", False))
    device.trusted = bool(props.get("Trusted", False))
    device.blocked = bool(props.get("Blocked", False))
    device.legacy_pairing = bool(props.get("LegacyPairing", False))
    device.services_resolved = bool(props.get("ServicesResolved", False))
    device.rssi = _int_or_none(props.get("RSSI"))
    device.tx_power = _int_or_none(props.get("TxPower"))
    device.manufacturer_data = _hex_dict(props.get("ManufacturerData") or {})
    device.manufacturer_ids = [f"0x{int(k):04x}" if str(k).isdigit() else str(k) for k in (props.get("ManufacturerData") or {}).keys()]
    device.service_data = _hex_dict(props.get("ServiceData") or {})
    device.advertising_flags = list(props.get("AdvertisingFlags") or [])
    device.advertising_data = _hex_dict(props.get("AdvertisingData") or {})
    device.raw_bluez_properties = props
    device.last_event_source = event_source
    device.is_cached_only = event_source == "initial_cache"
    device.is_paired_known = bool(device.paired or device.trusted)
    device.transport = _infer_transport(device)
    return device


def normalize_bluez_properties(properties: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _unwrap(value) for key, value in (properties or {}).items()}


def _unwrap(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if hasattr(value, "value"):
        return _unwrap(value.value, default)
    if isinstance(value, dict):
        return {_unwrap(k): _unwrap(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_unwrap(v) for v in value]
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return value


def _hex_dict(values: dict[Any, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in values.items():
        result[str(key)] = _bytes_to_hex(value)
    return result


def _bytes_to_hex(value: Any) -> str:
    value = _unwrap(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, bytearray):
        return bytes(value).hex()
    if isinstance(value, list):
        try:
            return bytes(int(item) & 0xFF for item in value).hex()
        except Exception:
            return json.dumps(value, default=str)
    return str(value)


def _infer_transport(device: BluetoothDevice) -> str:
    if device.address_type in {"public", "random"} and (
        device.rssi is not None
        or device.tx_power is not None
        or device.manufacturer_data
        or device.service_data
        or device.advertising_data
    ):
        return "le"
    if device.uuids and device.class_of_device is not None:
        return "dual"
    if device.class_of_device is not None:
        return "bredr"
    return "unknown"


async def _dbus_import() -> Any:
    try:
        from dbus_next import Variant
        from dbus_next.aio import MessageBus
        from dbus_next.constants import BusType, MessageType
    except ImportError as e:
        raise BluetoothScannerError(
            "dbus_next_missing",
            "Python package dbus-next is required for BlueZ D-Bus scanning.",
            "Install project dependencies from requirements.txt.",
        ) from e

    return SimpleNamespace(
        Variant=Variant,
        MessageBus=MessageBus,
        BusType=BusType,
        MessageType=MessageType,
    )


async def _connect_bluez(dbus: Any) -> tuple[Any, Any]:
    try:
        bus = await dbus.MessageBus(bus_type=dbus.BusType.SYSTEM).connect()
        introspection = await bus.introspect(BLUEZ_SERVICE, "/")
        proxy = bus.get_proxy_object(BLUEZ_SERVICE, "/", introspection)
        return bus, proxy.get_interface(OBJECT_MANAGER_IFACE)
    except Exception as e:
        raise BluetoothScannerError(
            "bluez_unavailable",
            "BlueZ is not available on the system D-Bus.",
            "Run: sudo systemctl enable --now bluetooth ; then check rfkill list bluetooth.",
        ) from e


async def _adapter_interface(dbus: Any, bus: Any, adapter_path: str) -> Any:
    introspection = await bus.introspect(BLUEZ_SERVICE, adapter_path)
    proxy = bus.get_proxy_object(BLUEZ_SERVICE, adapter_path, introspection)
    return proxy.get_interface(ADAPTER_IFACE)


async def _safe_call(callable_obj: Any, default: Any = None) -> Any:
    try:
        return await callable_obj()
    except Exception:
        return default


def _select_adapter(adapters: list[BluetoothAdapter], adapter_id: str | None) -> BluetoothAdapter | None:
    if adapter_id:
        for adapter in adapters:
            if adapter.adapter_id == adapter_id or adapter.object_path == adapter_id:
                return adapter
    for adapter in adapters:
        if adapter.adapter_id == "hci0":
            return adapter
    return adapters[0] if adapters else None


def _build_discovery_filter(variant_cls: Any, config: ScanConfig, supported_filters: list[str]) -> dict[str, Any]:
    supported = set(supported_filters or [])
    filters: dict[str, Any] = {}
    if not supported or "Transport" in supported:
        filters["Transport"] = variant_cls("s", config.normalized_transport())
    if not supported or "DuplicateData" in supported:
        filters["DuplicateData"] = variant_cls("b", bool(config.duplicate_data))
    if config.rssi_threshold is not None and (not supported or "RSSI" in supported):
        filters["RSSI"] = variant_cls("n", int(config.rssi_threshold))
    return filters


def _path_under_adapter(path: str, adapter_path: str) -> bool:
    return path == adapter_path or path.startswith(adapter_path + "/")


def _adapter_id_from_path(path: str) -> str:
    match = re.search(r"/org/bluez/(hci\d+)", path)
    return match.group(1) if match else "unknown"


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _structured_log(event_type: str, address: str = "") -> None:
    safe = {"event": event_type}
    if address:
        safe["address"] = _mask_address(address)
    print(f"BT_SCANNER {json.dumps(safe, sort_keys=True)}", flush=False)


def get_bluez_version() -> str:
    try:
        result = subprocess.run(["bluetoothd", "--version"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def platform_summary() -> str:
    return platform.platform()
