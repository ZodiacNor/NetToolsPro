"""Deterministic storage and dashboard regression tests; no network access."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from modules.app_storage import JsonStore, StorageError, data_directory, valid_favorites, valid_settings
from modules.dashboard_stats import SystemSampler
from modules.tool_search import search_tools


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "config" / "settings.json"

    def store(self, legacy=()):
        return JsonStore(self.path, dict, valid_settings, legacy)

    def test_round_trip_atomic_private_file(self):
        store = self.store()
        store.save({"theme": "light"})
        self.assertEqual(store.load(), {"theme": "light"})
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])
        if os.name == "posix":
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_legacy_migration_preserves_original(self):
        legacy = self.root / "settings.json"
        legacy.write_text('{"theme":"light"}', encoding="utf-8")
        before = legacy.read_bytes()
        self.assertEqual(self.store([legacy]).load(), {"theme": "light"})
        self.assertEqual(legacy.read_bytes(), before)
        self.assertEqual(self.store().load(), {"theme": "light"})

    def test_current_store_wins_over_legacy(self):
        self.store().save({"theme": "dark"})
        legacy = self.root / "settings.json"
        legacy.write_text('{"theme":"light"}', encoding="utf-8")
        self.assertEqual(self.store([legacy]).load(), {"theme": "dark"})

    def test_corrupt_file_is_not_overwritten(self):
        self.path.parent.mkdir()
        self.path.write_text("{broken", encoding="utf-8")
        store = self.store()
        with self.assertRaises(StorageError):
            store.load()
        with self.assertRaises(StorageError):
            store.save({"theme": "dark"})
        self.assertEqual(self.path.read_text(), "{broken")

    def test_failed_replace_keeps_last_good_file_and_cleans_temp(self):
        store = self.store()
        store.save({"theme": "light"})
        with patch("modules.app_storage.os.replace", side_effect=PermissionError):
            with self.assertRaises(StorageError):
                store.save({"theme": "dark"})
        self.assertEqual(store.load(), {"theme": "light"})
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_invalid_structure_does_not_become_active(self):
        for value in ([], {"theme": []}, {"theme": "banana"}, {"minimize_to_tray": "false"}):
            with self.subTest(value=value):
                with self.assertRaises(StorageError):
                    self.store().save(value)

    def test_favorites_require_complete_rows(self):
        self.assertTrue(valid_favorites([]))
        self.assertTrue(valid_favorites([dict(id="a", name="Lab", type="Host", value="192.0.2.1")]))
        for value in ({}, [None], [{"name": "Missing fields"}], [{"id": 1}]):
            self.assertFalse(valid_favorites(value))

    def test_explicit_test_directory(self):
        with patch.dict(os.environ, {"NETTOOLS_DATA_DIR": str(self.root)}):
            self.assertEqual(data_directory(), self.root)

    def test_linux_config_directory(self):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.root)}, clear=True):
            with patch("modules.app_storage.sys.platform", "linux"):
                self.assertEqual(data_directory(), self.root / "nettools-pro")


class SamplerTests(unittest.TestCase):
    def setUp(self):
        self.clock = Mock(return_value=10.0)
        self.ps = Mock()
        self.ps.cpu_percent.return_value = 20.0
        self.ps.cpu_count.return_value = 8
        self.ps.virtual_memory.return_value = SimpleNamespace(percent=50.0, used=10, total=20)
        self.ps.disk_usage.return_value = SimpleNamespace(percent=25.0, used=5, total=20)
        self.ps.net_io_counters.return_value = SimpleNamespace(bytes_recv=1000, bytes_sent=500)
        self.ps.net_connections.return_value = [object(), object()]
        self.gateway = Mock(return_value="192.0.2.1")
        self.sampler = SystemSampler(self.ps, lambda: "192.0.2.10", self.gateway, self.clock)

    def test_rates_are_deltas_not_totals(self):
        self.assertIsNone(self.sampler.sample()["download"])
        self.clock.return_value = 12.0
        self.ps.net_io_counters.return_value = SimpleNamespace(bytes_recv=3000, bytes_sent=1000)
        result = self.sampler.sample()
        self.assertEqual(result["download"], 1000)
        self.assertEqual(result["upload"], 250)

    def test_reset_counters_never_produce_negative_rates(self):
        self.sampler.sample()
        self.clock.return_value = 12.0
        self.ps.net_io_counters.return_value = SimpleNamespace(bytes_recv=50, bytes_sent=10)
        self.assertIsNone(self.sampler.sample()["download"])

    def test_missing_psutil_is_supported(self):
        result = SystemSampler(None, lambda: "192.0.2.10", self.gateway, self.clock).sample()
        self.assertIsNone(result["cpu"])
        self.assertEqual(result["local_ip"], "192.0.2.10")

    def test_denied_connections_are_unknown_not_zero(self):
        self.ps.net_connections.side_effect = PermissionError
        self.assertIsNone(self.sampler.sample()["connections"])

    def test_slow_route_and_connections_checks_are_throttled(self):
        self.sampler.sample()
        self.clock.return_value = 12.0
        self.sampler.sample()
        self.assertEqual(self.gateway.call_count, 1)
        self.assertEqual(self.ps.net_connections.call_count, 1)
        self.clock.return_value = 21.0
        self.sampler.sample()
        self.assertEqual(self.gateway.call_count, 2)

    def test_disk_error_does_not_hide_other_metrics(self):
        self.ps.disk_usage.side_effect = OSError
        result = self.sampler.sample()
        self.assertIsNone(result["disk"])
        self.assertEqual(result["cpu"], 20)


class SearchTests(unittest.TestCase):
    structure = [
        ("standalone", "Dashboard", "dashboard", None),
        ("category", "Camera", "camera", None),
        ("tool", "Stream Viewer", "camview", "camera"),
        ("tool", "Camera Finder", "camfinder", "camera"),
        ("category", "Discovery", "discovery", None),
        ("tool", "Wake-on-LAN", "wol", "discovery"),
    ]

    def test_case_insensitive_alias(self):
        self.assertEqual(search_tools("RTSP", self.structure)[0][0], "camview")

    def test_multi_word_matching(self):
        self.assertEqual([row[0] for row in search_tools("camera playback", self.structure)], ["camview"])

    def test_category_matches_all_its_tools(self):
        self.assertEqual(len(search_tools("camera", self.structure)), 2)

    def test_blank_query_preserves_catalog_order_without_headers(self):
        self.assertEqual([row[0] for row in search_tools("  ", self.structure)],
                         ["dashboard", "camview", "camfinder", "wol"])

    def test_no_matches(self):
        self.assertEqual(search_tools("not-a-real-tool", self.structure), [])


if __name__ == "__main__":
    unittest.main()
