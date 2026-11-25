"""Exercise real D-Bus signal routing on an isolated, temporary session bus."""

import asyncio
import contextlib
import io
import shutil
import subprocess
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from modules.bluetooth_scanner import linux_bluez_backend as bluez
from modules.bluetooth_scanner.models import ScanConfig
from modules.bluetooth_scanner.scanner_core import DeviceStore


@unittest.skipUnless(shutil.which("dbus-daemon"), "Requires a private D-Bus daemon")
class BlueZSignalDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from dbus_next import Message, Variant
        from dbus_next.aio import MessageBus

        self.Message, self.Variant = Message, Variant
        self.daemon = subprocess.Popen(
            ["dbus-daemon", "--session", "--nofork", "--print-address"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        address = await asyncio.wait_for(asyncio.to_thread(self.daemon.stdout.readline), 3)
        self.server = await MessageBus(bus_address=address.strip()).connect()
        await self.server.request_name(bluez.BLUEZ_SERVICE)
        self.client = await MessageBus(bus_address=address.strip()).connect()
        self.events, self.tasks = [], []
        self.stop_calls = 0
        self.fail_start = False

    async def asyncTearDown(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.client.disconnect()
        self.server.disconnect()
        await asyncio.gather(self.client.wait_for_disconnect(), self.server.wait_for_disconnect())
        # dbus-next 0.2.3 shuts down, but does not close, its socket descriptor.
        # Explicitly release both fixture descriptors after disconnect completes.
        self.client._stream.close()
        self.server._stream.close()
        self.client._sock.close()
        self.server._sock.close()
        self.daemon.terminate()
        await asyncio.to_thread(self.daemon.wait, 3)
        self.daemon.stdout.close()

    async def emit_devices(self):
        await asyncio.sleep(0.03)
        for adapter in ("hci0", "hci1"):
            path = f"/org/bluez/{adapter}/dev_02_00_00_00_00_01"
            properties = {"Address": self.Variant("s", "02:00:00:00:00:01"),
                          "RSSI": self.Variant("n", -70)}
            await self.server.send(self.Message.new_signal(
                "/", bluez.OBJECT_MANAGER_IFACE, "InterfacesAdded", "oa{sa{sv}}",
                [path, {bluez.DEVICE_IFACE: properties}],
            ))
            await self.server.send(self.Message.new_signal(
                path, bluez.PROPERTIES_IFACE, "PropertiesChanged", "sa{sv}as",
                [bluez.DEVICE_IFACE, {"RSSI": self.Variant("n", -42)}, []],
            ))

    async def connect(self, _dbus):
        async def objects():
            return {"/org/bluez/hci0": {bluez.ADAPTER_IFACE: {"Powered": True}}}
        return self.client, SimpleNamespace(call_get_managed_objects=objects)

    async def adapter(self, *_args):
        async def filters():
            return []
        async def set_filter(_filters):
            pass
        async def start():
            if self.fail_start:
                raise RuntimeError("Synthetic StartDiscovery failure")
            self.tasks.append(asyncio.create_task(self.emit_devices()))
        async def stop():
            self.stop_calls += 1
        return SimpleNamespace(call_get_discovery_filters=filters,
                               call_set_discovery_filter=set_filter,
                               call_start_discovery=start, call_stop_discovery=stop)

    async def scan(self):
        backend = bluez.LinuxBlueZBackend()
        backend.subscribe_events(self.events.append)
        store = DeviceStore("synthetic")
        with patch.object(bluez, "_connect_bluez", self.connect), \
                patch.object(bluez, "_adapter_interface", self.adapter), \
                patch.object(bluez, "get_bluez_version", return_value="synthetic"), \
                contextlib.redirect_stdout(io.StringIO()):
            await asyncio.wait_for(backend._scan_async(
                "synthetic", ScanConfig(adapter_id="hci0", include_cached=False, duration_seconds=.2),
                threading.Event(), store,
            ), 3)
        return store

    async def test_receives_live_devices_and_updates_only_from_selected_adapter(self):
        store = await self.scan()
        self.assertEqual(len(store.values()), 1)
        self.assertEqual(store.values()[0].adapter_id, "hci0")
        self.assertEqual(store.values()[0].rssi, -42)
        self.assertEqual([event.event_type for event in self.events].count("device_added"), 1)
        self.assertEqual([event.event_type for event in self.events].count("device_updated"), 1)
        self.assertEqual(self.stop_calls, 1)
        self.assertFalse(self.client.connected)

    async def test_failed_start_disconnects_without_stopping_another_discovery(self):
        self.fail_start = True
        with self.assertRaisesRegex(RuntimeError, "Synthetic StartDiscovery failure"):
            await self.scan()
        self.assertEqual(self.stop_calls, 0)
        self.assertFalse(self.client.connected)


class BlueZBinaryExportTests(unittest.TestCase):
    def test_binary_advertisement_properties_survive_json_export(self):
        import json
        from modules.bluetooth_scanner.exporter import export_json
        device = bluez.device_from_bluez_properties(
            "synthetic", "hci0", "/org/bluez/hci0/dev_test",
            {"AdvertisingFlags": bytes([6]), "ManufacturerData": {76: bytes([1, 255])},
             "ServiceData": {"test": bytearray([0, 128])}}, "interfaces_added",
        )
        result = json.loads(export_json(app_version="test", scan_config=ScanConfig(),
                                      started_at=None, stopped_at=None, devices=[device]))
        exported = result["devices"][0]
        self.assertEqual(exported["raw_bluez_properties"]["AdvertisingFlags"], [6])
        self.assertEqual(exported["raw_bluez_properties"]["ManufacturerData"]["76"], [1, 255])
        self.assertEqual(exported["manufacturer_data"]["76"], "01ff")
        self.assertEqual(exported["service_data"]["test"], "0080")


if __name__ == "__main__":
    unittest.main()
