# Bluetooth Scanner — Fedora 43

Bluetooth Scanner is a local BlueZ D-Bus based scanner for visible Bluetooth Classic devices, BLE advertisements, anonymous BLE broadcasters, random/private BLE addresses, and known/cached devices already present in BlueZ.

It does not claim to reveal every hidden Bluetooth device. Devices that do not advertise, are not discoverable, and are not already known to the local BlueZ cache cannot be reliably discovered through normal OS discovery.

## Fedora Setup

```bash
sudo dnf install -y bluez
sudo systemctl enable --now bluetooth
rfkill list bluetooth
bluetoothctl show
```

Do not run the whole app as root. NetTools Pro uses BlueZ through the system D-Bus. If adapter power or discovery requires privilege, the app should show a user-facing D-Bus or Polkit error.

## Supported In This Release

- Adapter listing through `org.freedesktop.DBus.ObjectManager.GetManagedObjects()`
- BlueZ `org.bluez.Adapter1` discovery through `SetDiscoveryFilter()`, `StartDiscovery()`, and `StopDiscovery()`
- Discovery transport modes: `auto`, `le`, and `bredr` where the controller supports them
- Device updates from `InterfacesAdded`, `InterfacesRemoved`, and `PropertiesChanged`
- Known/cached device view from BlueZ `org.bluez.Device1`
- RSSI updates, ManufacturerData, ServiceData, UUIDs, TxPower, and address type where BlueZ exposes them
- JSON and CSV local export

## Precise Labels

The UI uses defensive labels:

- `Anonymous BLE`
- `Random/private address`
- `Non-discoverable advertiser`
- `Unknown broadcaster`
- `Cached/known device`

These labels describe what BlueZ exposes. They do not identify a person and do not bypass BLE privacy.

## Manual Fedora Test Plan

1. Check Bluetooth:
   ```bash
   systemctl status bluetooth
   bluetoothctl show
   ```
2. Start NetTools Pro.
3. Open `Bluetooth Scanner`.
4. Select adapter `hci0`.
5. Run `BLE only` for `30s`.
6. Verify BLE devices appear, including unnamed devices if present nearby.
7. Run `Auto` for `30s`.
8. Verify BLE and any visible Classic devices appear.
9. Turn Bluetooth off and verify the app shows a clear adapter/powered-off error.
10. Start a scan and close or switch away from the module; verify discovery is stopped.
11. Export JSON and CSV.
12. Compare manually with:
    ```bash
    bluetoothctl scan on
    bluetoothctl devices
    ```

## Useful Diagnostics

The module diagnostic view suggests these checks:

```bash
rpm -q bluez
systemctl status bluetooth
systemctl is-active bluetooth
rfkill list bluetooth
bluetoothctl show
busctl tree org.bluez
busctl introspect org.bluez /org/bluez/hci0 org.bluez.Adapter1
journalctl -u bluetooth --since "10 min ago"
```

## Export Examples

JSON shape:

```json
{
  "app_version": "1.9.0",
  "module_version": "0.1.0",
  "os": "Linux-...",
  "bluez_version": "5.x",
  "scan_config": {
    "adapter_id": "hci0",
    "transport": "le",
    "duration_seconds": 30,
    "rssi_threshold": null,
    "duplicate_data": true,
    "include_cached": true,
    "include_paired": true,
    "continuous": false,
    "ui_update_interval_ms": 250,
    "session_label": "BLE only"
  },
  "started_at": "2026-05-29T18:00:00+00:00",
  "stopped_at": "2026-05-29T18:00:30+00:00",
  "devices": []
}
```

CSV columns:

```csv
display_name,address,address_type,transport,rssi,tx_power,first_seen,last_seen,seen_count,classification,manufacturer_ids,uuids,paired,connected,notes
Unknown broadcaster,AA:BB:CC:DD:EE:FF,random,le,-71,,2026-05-29T18:00:01+00:00,2026-05-29T18:00:10+00:00,4,random_private_address,0x004c,,False,False,BlueZ reports AddressType=random
```

## Future Ports

- Ubuntu, Kali, and Parrot should be able to reuse `LinuxBlueZBackend` if BlueZ and D-Bus permissions are equivalent.
- Windows 10/11 should use a separate backend:
  - BLE: `Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementWatcher`
  - Classic: Win32 Bluetooth APIs

Windows support is intentionally not implemented in this release.
