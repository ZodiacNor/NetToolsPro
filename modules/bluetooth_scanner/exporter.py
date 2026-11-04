"""Local JSON and CSV export helpers for Bluetooth scan sessions."""

from __future__ import annotations

import csv
import io
import json
import platform
from datetime import datetime
from typing import Any

from .models import MODULE_VERSION, BluetoothDevice, ScanConfig, isoformat


def export_json(
    *,
    app_version: str,
    scan_config: ScanConfig,
    started_at: datetime | None,
    stopped_at: datetime | None,
    devices: list[BluetoothDevice],
    bluez_version: str = "",
) -> str:
    payload = {
        "app_version": app_version,
        "module_version": MODULE_VERSION,
        "os": platform.platform(),
        "bluez_version": bluez_version,
        "scan_config": scan_config.to_dict(),
        "started_at": isoformat(started_at),
        "stopped_at": isoformat(stopped_at),
        "devices": [device.to_dict(include_raw=True) for device in devices],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def export_csv(devices: list[BluetoothDevice]) -> str:
    output = io.StringIO()
    fields = [
        "display_name",
        "address",
        "address_type",
        "transport",
        "rssi",
        "tx_power",
        "first_seen",
        "last_seen",
        "seen_count",
        "classification",
        "manufacturer_ids",
        "uuids",
        "paired",
        "connected",
        "notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for device in devices:
        writer.writerow(
            {
                "display_name": device.display_name,
                "address": device.address,
                "address_type": device.address_type,
                "transport": device.transport,
                "rssi": "" if device.rssi is None else device.rssi,
                "tx_power": "" if device.tx_power is None else device.tx_power,
                "first_seen": isoformat(device.first_seen),
                "last_seen": isoformat(device.last_seen),
                "seen_count": device.seen_count,
                "classification": device.classification,
                "manufacturer_ids": ";".join(device.manufacturer_ids),
                "uuids": ";".join(device.uuids),
                "paired": device.paired,
                "connected": device.connected,
                "notes": " | ".join(device.notes),
            }
        )
    return output.getvalue()


def flat_preview(device: BluetoothDevice) -> dict[str, Any]:
    """Return a compact dict for UI tables and debug previews."""
    return {
        "display_name": device.display_name,
        "address": device.address,
        "address_type": device.address_type,
        "transport": device.transport,
        "rssi": device.rssi,
        "tx_power": device.tx_power,
        "classification": device.classification,
        "badges": device.badges,
    }
