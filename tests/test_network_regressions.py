"""Offline regressions for scan results, input limits and platform helpers."""
import errno
import threading
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import nettools
from platform_utils import scripting
from platform_utils.parsers import windows
from modules.bluetooth_scanner.linux_bluez_backend import device_from_bluez_properties
from modules.bluetooth_scanner.scanner_core import DeviceStore


def variable(value):
    return Mock(get=Mock(return_value=value))


def frame_stub(cls, methods=(), **values):
    frame = SimpleNamespace(**values)
    for name in methods:
        setattr(frame, name, MethodType(getattr(cls, name), frame))
    return frame


class PortScanTests(unittest.TestCase):
    def test_tcp_timeout_is_filtered_not_closed(self):
        with patch.object(nettools.socket, "socket") as factory:
            connection = factory.return_value.__enter__.return_value
            for code, expected in ((0, "open"), (errno.ECONNREFUSED, "closed"),
                                   (errno.ETIMEDOUT, "filtered"), (10060, "filtered"),
                                   (errno.EHOSTUNREACH, "filtered")):
                with self.subTest(code=code):
                    connection.connect_ex.return_value = code
                    self.assertEqual(nettools.PortScanFrame._tcp_scan(None, "192.0.2.1", 80, 100), expected)

    def test_udp_uncertainty_is_not_open_and_does_not_trigger_tcp_fingerprint(self):
        frame = frame_stub(nettools.PortScanFrame, stop_event=threading.Event(),
                           _tcp_scan=Mock(return_value="closed"),
                           _udp_scan=Mock(return_value="open|filtered"), _fingerprint=Mock())
        for proto in ("UDP", "Both"):
            with self.subTest(proto=proto):
                result = nettools.PortScanFrame._scan_one(frame, "192.0.2.1", 53, proto, 100, True)
                self.assertEqual(result[1], "open|filtered")
                frame._fingerprint.assert_not_called()

    def test_udp_open_does_not_trigger_tcp_fingerprint(self):
        frame = SimpleNamespace(stop_event=threading.Event(), _udp_scan=Mock(return_value="open"),
                                _fingerprint=Mock())
        result = nettools.PortScanFrame._scan_one(frame, "192.0.2.1", 53, "UDP", 100, True)
        self.assertEqual(result[1], "open")
        frame._fingerprint.assert_not_called()

    def test_invalid_custom_ports_are_rejected_before_allocation(self):
        frame = frame_stub(nettools.PortScanFrame, _PROFILES=nettools.PortScanFrame._PROFILES,
                           _profile_var=variable("Custom"), mode_var=variable("range"))
        for start, end in ((0, 80), (80, 0), (90, 80), (-1, 65535), (1, 65536)):
            with self.subTest(start=start, end=end):
                frame.start_port, frame.end_port = variable(start), variable(end)
                with self.assertRaises(ValueError):
                    nettools.PortScanFrame._get_ports(frame)

    def test_udp_unknown_is_counted_as_filtered_in_results(self):
        frame = frame_stub(nettools.PortScanFrame, ("_scan_ports",), _total=1, _results=[],
                           timeout_var=variable(100), proto_var=variable("UDP"),
                           threads_var=variable(1), open_only_var=variable(False),
                           fingerprint_var=variable(False), stop_event=threading.Event(),
                           _scan_stats=dict(scanned=0, open=0, closed=0, filtered=0),
                           _scan_one=Mock(return_value=(53, "open|filtered", "UDP", "", "")),
                           q=Mock(), after=Mock())
        with patch.object(nettools.SessionHistory, "log"):
            nettools.PortScanFrame._worker(frame, "192.0.2.1", [53], (100, "UDP", 1, False, False))
        self.assertEqual(frame._scan_stats["open"], 0)
        self.assertEqual(frame._scan_stats["filtered"], 1)
        self.assertEqual(frame._results, [])
        self.assertTrue(any("OPEN|FILTERED" in call.args[0] for call in frame.q.call_args_list))


class NetworkScanTests(unittest.TestCase):
    def test_large_scan_is_confirmed_before_enumerating_hosts(self):
        network = Mock(num_addresses=2**32, prefixlen=0)
        network.hosts.side_effect = AssertionError("Host list allocated before confirmation")
        frame = SimpleNamespace(running=False, net_var=variable("0.0.0.0/0"))
        with patch.object(nettools.ipaddress, "IPv4Network", return_value=network), \
                patch.object(nettools.messagebox, "askyesno", return_value=False) as confirm:
            nettools.NetworkScanFrame._start(frame)
        confirm.assert_called_once()
        network.hosts.assert_not_called()

    def test_small_prefixes_count_all_usable_addresses(self):
        for cidr, expected in (("192.0.2.0/31", 2), ("192.0.2.1/32", 1), ("192.0.2.0/30", 2)):
            with self.subTest(cidr=cidr):
                frame = SimpleNamespace(running=False, net_var=variable(cidr),
                                        timeout_var=variable(100), threads_var=variable(1), resolve_var=variable(False),
                                        ui_started=Mock(), _clear_all=Mock(), start_poll=Mock(), _worker=Mock())
                with patch.object(nettools.threading, "Thread"):
                    nettools.NetworkScanFrame._start(frame)
                self.assertEqual(frame._total, expected)


class WindowsParsingTests(unittest.TestCase):
    def test_arp_lookup_matches_entire_address(self):
        output = "  192.0.2.10  aa-bb-cc-dd-ee-10 dynamic\n  192.0.2.1  aa-bb-cc-dd-ee-01 dynamic\n"
        self.assertEqual(windows.parse_arp_single(output, "192.0.2.1"), "AA:BB:CC:DD:EE:01")
        self.assertIsNone(windows.parse_arp_single(output, "192.0.2.2"))

    def test_route_uses_interface_column_and_lowest_metric(self):
        output = "\n".join((
            "0.0.0.0 0.0.0.0 192.0.2.1 192.0.2.10 200",
            "0.0.0.0 0.0.0.0 198.51.100.1 192.0.2.20 50",
            "0.0.0.0 0.0.0.0 203.0.113.1 203.0.113.10 10",
        ))
        self.assertEqual(windows.parse_default_gateway(output, "192.0.2.20"), "198.51.100.1")
        self.assertEqual(windows.parse_default_gateway(output), "203.0.113.1")


class ScriptCommandTests(unittest.TestCase):
    def test_source_python_uses_current_interpreter(self):
        with patch.object(scripting.sys, "frozen", False, create=True):
            command = scripting.build_run_command("example.py")
        self.assertEqual(command[0], scripting.sys.executable)

    def test_frozen_python_uses_external_interpreter(self):
        with patch.object(scripting.sys, "frozen", True, create=True), \
                patch.object(scripting, "IS_WINDOWS", False), \
                patch("shutil.which", return_value="/usr/bin/python3"):
            command = scripting.build_run_command("example.py")
        self.assertEqual(command[0], "/usr/bin/python3")
        self.assertNotEqual(command[0], scripting.sys.executable)

    def test_frozen_python_missing_interpreter_reports_error(self):
        with patch.object(scripting.sys, "frozen", True, create=True), patch("shutil.which", return_value=None):
            with self.assertRaises(FileNotFoundError):
                scripting.build_run_command("example.py")

    def test_frozen_windows_prefers_python_launcher(self):
        with patch.object(scripting.sys, "frozen", True, create=True), \
                patch.object(scripting, "IS_WINDOWS", True), \
                patch("shutil.which", return_value="C:/Windows/py.exe"):
            self.assertEqual(scripting.build_run_command("example.py"),
                             ["C:/Windows/py.exe", "-3", "example.py"])


class BluetoothMergeTests(unittest.TestCase):
    def test_rssi_update_preserves_pairing_address_type_and_raw_properties(self):
        store = DeviceStore("test")
        initial = device_from_bluez_properties("test", "hci0", "/org/bluez/hci0/dev_TEST", {
            "Address": "AA:BB:CC:DD:EE:FF", "AddressType": "random", "Paired": True,
            "Trusted": True, "Connected": True, "Name": "Test device", "RSSI": -70,
        }, "initial_cache")
        store.upsert(initial, "initial_cache")
        change = device_from_bluez_properties("test", "hci0", initial.object_path, {"RSSI": -60}, "properties_changed")
        updated = store.upsert(change, "properties_changed")
        self.assertTrue(updated.paired)
        self.assertTrue(updated.connected)
        self.assertTrue(updated.trusted)
        self.assertEqual(updated.address_type, "random")
        self.assertEqual(updated.transport, "le")
        self.assertEqual(updated.raw_bluez_properties["Name"], "Test device")
        self.assertEqual(updated.rssi, -60)

    def test_explicit_false_and_empty_property_updates_are_applied(self):
        store = DeviceStore("test")
        initial = device_from_bluez_properties("test", "hci0", "/org/bluez/hci0/dev_TEST", {
            "Paired": True, "Name": "Old name", "UUIDs": ["test"], "ManufacturerData": {76: [1]},
        }, "interfaces_added")
        store.upsert(initial, "interfaces_added")
        change = device_from_bluez_properties("test", "hci0", initial.object_path, {
            "Paired": False, "Name": "", "UUIDs": [], "ManufacturerData": {},
        }, "properties_changed")
        updated = store.upsert(change, "properties_changed")
        self.assertFalse(updated.paired)
        self.assertEqual(updated.name, "")
        self.assertEqual(updated.uuids, [])
        self.assertEqual(updated.manufacturer_data, {})

    def test_empty_properties_changed_does_not_clear_known_flags(self):
        store = DeviceStore("test")
        initial = device_from_bluez_properties("test", "hci0", "/org/bluez/hci0/dev_TEST",
                                               {"Paired": True, "Trusted": True}, "initial_cache")
        store.upsert(initial, "initial_cache")
        change = device_from_bluez_properties("test", "hci0", initial.object_path, {}, "properties_changed")
        updated = store.upsert(change, "properties_changed")
        self.assertTrue(updated.paired)
        self.assertTrue(updated.trusted)


if __name__ == "__main__":
    unittest.main()
