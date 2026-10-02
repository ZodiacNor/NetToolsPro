"""Guard the recovered camera/glyph baseline during the workspace update.

Fingerprints came from the complete dirty worktree backup on 2026-09-06,
not from Git HEAD (which lacks the existing Bluetooth work). Deliberate
changes require a new verified baseline, not simply replacing these hashes.
"""
import ast
import hashlib
from pathlib import Path
import unittest

EXPECTED = {
    "_safe_ui_text": "e819a7cdfa1559ae492787b684ef4d4fa02e53df3dc366986bf6d79369596b71",
    "_install_safe_ctk_text_wrappers": "5949c5e21aeaf3fa0f8e76c432b94c563bac0ad6a6b588bbeffe1e1f2a4fd88d",
    "_load_pystray": "073a6999d7b63d4f9ef35c26d7f0b28c33e9a01c0ac7d84757b43dc895e74bd2",
    "_CameraStreamSlot": "8a52811c1bbfafd2fb62d3e48dd694a8213b4680bea6f4c68c2fc3ad6612a6a3",
    "CameraViewerFrame": "a941a34becda4c4d8caeb5eaa760fd0ad9483835d4c392eeaf28f3a9abe0be6c",
    "BluetoothScannerFrame": "a051d6874f72d8093e4edb084a4fca0d60d66a6fdbc3fd9a7534d968ffc3e960",
}


class ProtectedBaselineTests(unittest.TestCase):
    def test_recovered_camera_glyph_and_existing_bluetooth_code_unchanged(self):
        source = (Path(__file__).resolve().parents[1] / "nettools.py").read_text(encoding="utf-8")
        actual = {
            node.name: hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest()
            for node in ast.parse(source).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in EXPECTED
        }
        self.assertEqual(actual, EXPECTED)
