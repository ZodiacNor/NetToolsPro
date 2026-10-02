"""Bluetooth device classification rules.

The classifier intentionally avoids claims like "hidden device". It only labels
what BlueZ exposes through discovery, cached state, or advertisement metadata.
"""

from __future__ import annotations

from .models import BluetoothDevice


def classify_device(device: BluetoothDevice) -> BluetoothDevice:
    """Set classification, confidence, badges, and notes on a device."""
    badges: list[str] = []
    notes: list[str] = []

    if device.address_type == "random":
        badges.append("Random/private address")
        notes.append("BlueZ reports AddressType=random; this can be a resolvable or non-resolvable BLE private address.")

    if device.manufacturer_data:
        badges.append("Manufacturer data")

    if device.service_data or device.uuids:
        badges.append("Service advertisement")

    if device.paired:
        badges.append("Paired/known")

    if device.is_cached_only:
        badges.append("Cached only")

    has_name = bool((device.name or device.alias or "").strip())
    has_ad_data = bool(
        device.rssi is not None
        or device.tx_power is not None
        or device.manufacturer_data
        or device.service_data
        or device.advertising_flags
        or device.advertising_data
    )

    if device.paired:
        classification = "paired_known_device"
        confidence = "likely"
    elif device.is_cached_only:
        classification = "cached_only"
        confidence = "likely"
    elif device.address_type == "random":
        classification = "random_private_address"
        confidence = "likely"
    elif not has_name and has_ad_data:
        classification = "anonymous_ble"
        confidence = "likely"
        badges.append("Anonymous BLE")
        notes.append("No Name or Alias was exposed, but BLE advertisement metadata or RSSI was observed.")
    elif device.transport == "bredr":
        classification = "classic_bredr_device"
        confidence = "likely"
    elif device.transport == "dual":
        classification = "dual_mode_device"
        confidence = "possible"
    elif has_name:
        classification = "visible_named_device"
        confidence = "likely"
    elif has_ad_data:
        classification = "non_connectable_or_non_discoverable_advertiser"
        confidence = "possible"
        badges.append("Unknown broadcaster")
        notes.append("Device advertised metadata but did not expose enough identity fields for a stronger label.")
    else:
        classification = "unknown_bluetooth_device"
        confidence = "unknown"

    if not has_name and not device.paired and not device.is_cached_only:
        notes.append("This only means no friendly name was exposed during discovery.")

    device.display_name = device.name or device.alias or "Unknown broadcaster"
    device.classification = classification
    device.confidence = confidence
    device.badges = _dedupe(badges)
    device.notes = _dedupe(notes)
    device.is_paired_known = bool(device.paired or device.trusted)
    return device


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
