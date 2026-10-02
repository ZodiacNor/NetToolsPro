"""Exercise the real GUI data managers without constructing a GUI."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nettools
from modules.app_storage import JsonStore, valid_favorites, valid_settings


class ManagerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.favorites = nettools.FavoritesManager
        self.settings = nettools.SettingsManager
        patches = [
            patch.object(self.favorites, "_store", JsonStore(self.root / "favorites.json", list, valid_favorites)),
            patch.object(self.favorites, "_favorites", []),
            patch.object(self.favorites, "_load_error", None),
            patch.object(self.settings, "_store", JsonStore(self.root / "settings.json", dict, valid_settings)),
            patch.object(self.settings, "_settings", dict(self.settings._defaults)),
            patch.object(self.settings, "_load_error", None),
            patch.object(nettools.messagebox, "showerror"),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def test_favorites_survive_reload_and_delete(self):
        entry = self.favorites.add("Test host", "Host", "192.0.2.1")
        self.favorites._favorites = []
        self.favorites.load()
        self.assertEqual(self.favorites.get_all(), [entry])
        self.favorites.remove(entry["id"])
        self.favorites.load()
        self.assertEqual(self.favorites.get_all(), [])

    def test_failed_save_rolls_back_new_favorite(self):
        with patch("modules.app_storage.os.replace", side_effect=PermissionError):
            self.assertIsNone(self.favorites.add("Test", "Host", "192.0.2.1"))
        self.assertEqual(self.favorites.get_all(), [])
        nettools.messagebox.showerror.assert_called_once()

    def test_failed_delete_keeps_favorite_in_memory_and_on_disk(self):
        entry = self.favorites.add("Test", "Host", "192.0.2.1")
        with patch("modules.app_storage.os.replace", side_effect=PermissionError):
            self.favorites.remove(entry["id"])
        self.assertEqual(self.favorites.get_all(), [entry])
        self.favorites.load()
        self.assertEqual(self.favorites.get_all(), [entry])

    def test_corrupt_favorites_warn_and_block_replacement(self):
        path = self.root / "favorites.json"
        path.write_text("{broken", encoding="utf-8")
        self.favorites.load()
        self.assertIsNotNone(self.favorites._load_error)
        self.assertIsNone(self.favorites.add("Test", "Host", "192.0.2.1"))
        self.assertEqual(path.read_text(), "{broken")

    def test_settings_survive_reload(self):
        self.settings.set("theme", "light")
        self.settings._settings = {}
        self.settings.load()
        self.assertEqual(self.settings.get("theme"), "light")

    def test_invalid_settings_fall_back_without_overwriting_file(self):
        path = self.root / "settings.json"
        original = '{"theme": []}'
        path.write_text(original, encoding="utf-8")
        self.settings.load()
        self.assertEqual(self.settings.get("theme"), "dark")
        self.assertIsNotNone(self.settings._load_error)
        self.settings.set("theme", "light")
        self.assertEqual(path.read_text(), original)
