import csv
import io
import json
import os
import time
import unittest

from modules.bluetooth_scanner.classifier import classify_device
from modules.bluetooth_scanner.exporter import export_csv, export_json
from modules.bluetooth_scanner.linux_bluez_backend import (
    _build_discovery_filter,
    device_from_bluez_properties,
)
from modules.bluetooth_scanner.models import BluetoothDevice, ScanConfig
from modules.bluetooth_scanner.scanner_core import BluetoothScannerError, DeviceStore


class FakeVariant:
    def __init__(self, signature, value):
        self.signature = signature
        self.value = value


class BluetoothScannerUnitTests(unittest.TestCase):
    def test_maps_bluez_properties_to_bt_device(self):
        device = device_from_bluez_properties(
            session_id="s1",
            adapter_id="hci0",
            object_path="/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF",
            properties={
                "Address": "AA:BB:CC:DD:EE:FF",
                "AddressType": "random",
                "Name": "",
                "Alias": "",
                "RSSI": -71,
                "TxPower": 4,
                "ManufacturerData": {76: [1, 2, 255]},
                "ServiceData": {"0000180d-0000-1000-8000-00805f9b34fb": bytes([3, 4])},
                "Paired": False,
            },
            event_source="properties_changed",
        )
        classify_device(device)

        self.assertEqual(device.address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(device.address_type, "random")
        self.assertEqual(device.manufacturer_data["76"], "0102ff")
        self.assertEqual(device.service_data["0000180d-0000-1000-8000-00805f9b34fb"], "0304")
        self.assertEqual(device.classification, "random_private_address")
        self.assertIn("Random/private address", device.badges)

    def test_anonymous_ble_classification_uses_precise_language(self):
        device = BluetoothDevice.new("s1", "hci0", "/org/bluez/hci0/dev_11_22_33_44_55_66")
        device.address = "11:22:33:44:55:66"
        device.address_type = "public"
        device.rssi = -82

        classify_device(device)

        self.assertEqual(device.classification, "anonymous_ble")
        self.assertIn("Anonymous BLE", device.badges)
        self.assertNotIn("hidden", " ".join(device.notes).lower())

    def test_dedupe_updates_existing_device_and_rssi_history(self):
        store = DeviceStore("s1", max_rssi_history=3)
        first = device_from_bluez_properties("s1", "hci0", "/org/bluez/hci0/dev_A", {"Address": "AA", "AddressType": "public", "RSSI": -80}, "interfaces_added")
        second = device_from_bluez_properties("s1", "hci0", "/org/bluez/hci0/dev_A", {"Address": "AA", "AddressType": "public", "RSSI": -79}, "properties_changed")
        third = device_from_bluez_properties("s1", "hci0", "/org/bluez/hci0/dev_A", {"Address": "AA", "AddressType": "public", "RSSI": -78}, "properties_changed")
        fourth = device_from_bluez_properties("s1", "hci0", "/org/bluez/hci0/dev_A", {"Address": "AA", "AddressType": "public", "RSSI": -77}, "properties_changed")

        device = store.upsert(first, "interfaces_added")
        self.assertEqual(device.seen_count, 1)
        store.upsert(second, "properties_changed")
        store.upsert(third, "properties_changed")
        updated = store.upsert(fourth, "properties_changed")

        self.assertEqual(len(store.values()), 1)
        self.assertEqual(updated.seen_count, 4)
        self.assertEqual(updated.rssi_history, [-79, -78, -77])

    def test_export_json_and_csv(self):
        config = ScanConfig(adapter_id="hci0", transport="le", duration_seconds=10)
        device = BluetoothDevice.new("s1", "hci0", "/org/bluez/hci0/dev_A")
        device.display_name = "Unknown broadcaster"
        device.address = "AA:BB:CC:DD:EE:FF"
        device.address_type = "random"
        device.transport = "le"
        device.rssi = -70
        classify_device(device)

        data = json.loads(export_json(app_version="1.9.0", scan_config=config, started_at=None, stopped_at=None, devices=[device], bluez_version="5.x"))
        self.assertEqual(data["module_version"], "0.1.0")
        self.assertEqual(data["scan_config"]["transport"], "le")
        self.assertEqual(len(data["devices"]), 1)

        rows = list(csv.DictReader(io.StringIO(export_csv([device]))))
        self.assertEqual(rows[0]["address"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(rows[0]["classification"], "random_private_address")

    def test_error_object_is_exportable(self):
        error = BluetoothScannerError("adapter_missing", "No adapter", "Check bluetooth.service")
        self.assertEqual(error.to_dict()["code"], "adapter_missing")
        self.assertIn("bluetooth", error.to_dict()["suggestion"])


class BluetoothScannerMockDBusTests(unittest.TestCase):
    def test_discovery_filter_uses_supported_bluez_keys(self):
        config = ScanConfig(transport="le", duplicate_data=True, rssi_threshold=-80)
        filters = _build_discovery_filter(FakeVariant, config, ["Transport", "DuplicateData", "RSSI"])

        self.assertEqual(filters["Transport"].value, "le")
        self.assertEqual(filters["DuplicateData"].value, True)
        self.assertEqual(filters["RSSI"].value, -80)
        self.assertEqual(filters["RSSI"].signature, "n")

    def test_properties_changed_style_update_refreshes_device(self):
        store = DeviceStore("s1")
        initial = device_from_bluez_properties(
            "s1",
            "hci0",
            "/org/bluez/hci0/dev_AA_BB",
            {"Address": "AA:BB", "AddressType": "public", "Alias": "Cached"},
            "initial_cache",
        )
        changed = device_from_bluez_properties(
            "s1",
            "hci0",
            "/org/bluez/hci0/dev_AA_BB",
            {"Address": "AA:BB", "AddressType": "public", "RSSI": -61, "ManufacturerData": {6: [1]}},
            "properties_changed",
        )

        store.upsert(initial, "initial_cache")
        updated = store.upsert(changed, "properties_changed")

        self.assertEqual(updated.rssi, -61)
        self.assertEqual(updated.manufacturer_data["6"], "01")
        self.assertFalse(updated.is_cached_only)

    def test_interfaces_removed_marks_device_removed(self):
        store = DeviceStore("s1")
        device = device_from_bluez_properties(
            "s1",
            "hci0",
            "/org/bluez/hci0/dev_AA_BB",
            {"Address": "AA:BB", "AddressType": "public"},
            "interfaces_added",
        )
        store.upsert(device, "interfaces_added")

        removed = store.mark_removed("/org/bluez/hci0/dev_AA_BB")

        self.assertIsNotNone(removed)
        self.assertTrue(removed.removed)
        self.assertEqual(removed.last_event_source, "interfaces_removed")


@unittest.skipUnless(os.environ.get("NETTOOLS_BT_INTEGRATION") == "1", "Bluetooth hardware integration disabled")
class BluetoothScannerFedoraIntegrationTests(unittest.TestCase):
    def test_bluez_adapter_list_and_short_scan(self):
        from modules.bluetooth_scanner.linux_bluez_backend import LinuxBlueZBackend

        backend = LinuxBlueZBackend(app_version="test")
        adapters = backend.list_adapters()
        self.assertTrue(adapters)
        adapter_id = adapters[0].adapter_id

        events = []
        session_id = backend.start_scan(ScanConfig(adapter_id=adapter_id, transport="le", duration_seconds=2), events.append)
        time.sleep(3)
        backend.stop_scan(session_id)
        self.assertTrue(any(event.event_type == "scan_session_started" for event in events))
        self.assertTrue(any(event.event_type == "scan_session_stopped" for event in events))


if __name__ == "__main__":
    unittest.main()
