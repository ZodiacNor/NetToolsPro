"""Opt-in desktop smoke/benchmark: no scans, cameras, or real saved targets.

Run from the repository: .venv/bin/python -B tests/gui_workspace.py
"""
import contextlib
import argparse
import json
import pathlib
import subprocess
import sys
import tarfile
import time
import types
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if "--baseline" in sys.argv:
    app_module = types.ModuleType("nettools_baseline")
    app_module.__file__ = str(ROOT / "nettools.py")
    with tarfile.open(ROOT / ".backups/2026-09-06-before-workspace/source.tar.gz") as backup:
        source = backup.extractfile("./nettools.py").read()
    exec(compile(source, app_module.__file__, "exec"), app_module.__dict__)
else:
    import nettools as app_module


def widget_count(widget):
    return 1 + sum(widget_count(child) for child in widget.winfo_children())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Visit all pages and exercise navigation")
    parser.add_argument("--screenshots", action="store_true", help="Capture sanitized KDE windows locally")
    parser.add_argument("--baseline", action="store_true", help="Benchmark the local pre-change source backup")
    args = parser.parse_args()
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(app_module, "get_local_ip", return_value="192.0.2.10"))
        stack.enter_context(patch.object(app_module, "get_local_network", return_value="192.0.2.0/24"))
        stack.enter_context(patch.object(app_module._pu_net, "default_gateway", return_value="192.0.2.1"))
        stack.enter_context(patch.object(app_module.FavoritesManager, "load"))
        stack.enter_context(patch.object(app_module.SettingsManager, "load"))
        stack.enter_context(patch.object(app_module.SettingsManager, "save"))
        app_module.FavoritesManager._favorites = []
        app_module.SettingsManager._settings = dict(app_module.SettingsManager._defaults)
        for cls, method in (
            (app_module.InterfacesFrame, "_refresh"),
            (app_module.ConnectionsFrame, "_refresh"),
            (app_module.ARPFrame, "_refresh"),
            (app_module.BluetoothScannerFrame, "_refresh_adapters"),
            (app_module.ScriptLabFrame, "_refresh_script_list"),
        ):
            stack.enter_context(patch.object(cls, method))
        errors = []
        started = time.perf_counter()
        app = app_module.App()
        constructed = time.perf_counter() - started
        app.report_callback_exception = lambda *args: errors.append(str(args[1]))

        def capture(name):
            if args.screenshots:
                destination = ROOT / ".test-work" / name
                destination.parent.mkdir(exist_ok=True)
                app.lift()
                app.focus_force()
                app.update_idletasks()
                # Let Tk and the Wayland compositor finish redraws after resizing.
                painted = app_module.tk.BooleanVar(value=False)
                app.after(700, lambda: painted.set(True))
                app.wait_variable(painted)
                # Keep the event loop running while the compositor takes its image.
                process = subprocess.Popen(["spectacle", "-a", "-b", "-n", "-e", "-S", "-o", str(destination)],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                captured = app_module.tk.BooleanVar(value=False)
                deadline = time.monotonic() + 15

                def poll_capture():
                    if process.poll() is not None:
                        captured.set(True)
                    elif time.monotonic() >= deadline:
                        process.kill()
                        process.wait()
                        captured.set(True)
                    else:
                        app.after(50, poll_capture)

                app.after(50, poll_capture)
                app.wait_variable(captured)
                assert process.returncode == 0, "Screenshot capture failed"

        def verify_full():
            try:
                assert list(app._frames) == ["dashboard"], "Startup built unopened pages"
                dashboard = app._frames["dashboard"]
                capture("dashboard.png")
                app.geometry("980x640")
                app.update_idletasks()
                capture("dashboard-small.png")
                assert dashboard._activity_label.winfo_rooty() + dashboard._activity_label.winfo_height() <= app.winfo_rooty() + app.winfo_height()
                app.geometry("1340x820")
                sidebar = app._sidebar
                sidebar._search_var.set("ping")
                sidebar._clear_search()
                sidebar_children = len(sidebar.winfo_children())
                for _ in range(5):
                    sidebar._search_var.set("ping")
                    sidebar._clear_search()
                assert len(sidebar.winfo_children()) == sidebar_children, "Search leaked scroll containers"
                sidebar.focus_search()
                sidebar._search_var.set("RTSP")
                assert [result[0] for result in sidebar._search_matches] == ["camview"]
                capture("tool-search.png")
                sidebar._open_search_result()
                assert app._current_key == "camview"
                assert not dashboard._active.is_set()
                assert dashboard._poll_id is None
                viewer = app._frames["camview"]
                assert len(viewer._slots) == 4
                app.update_idletasks()
                from PIL import Image
                for slot in viewer._slots:
                    viewer._display_pil_image(slot, Image.new("RGB", (640, 360), "#264663"))
                    assert slot.current_photo is not None
                    assert slot.lost_count == 0
                viewer._toggle_fullscreen_slot(2)
                assert viewer._fullscreen_slot_idx == 2
                viewer._toggle_fullscreen_slot(2)
                assert viewer._fullscreen_slot_idx is None
                capture("camera-wall.png")
                with patch.object(viewer, "_probe_streams") as probe:
                    app._open_viewer("192.0.2.20", 8080, "Test camera")
                    probe.assert_called_once()
                    assert viewer._ip_var.get() == "192.0.2.20"
                app_module.SessionHistory.log("GUI test", "Synthetic action", "No network request")
                for key in app._frame_classes:
                    app._show(key)
                    assert app._current_key == key
                assert len(app._frames) == 25
                app._show("history")
                assert "Synthetic action" in app._frames["history"].output.get("1.0", "end")
                app._show("dashboard")
                assert dashboard._active.is_set()
                app._show("camview")
                assert app._frames["camview"] is viewer
                assert all(slot.current_photo is not None for slot in viewer._slots)
                sidebar._search_var.set("not-a-real-tool")
                sidebar._open_search_result()
                assert app._current_key == "camview"
                sidebar._clear_search()
                assert not sidebar._search_var.get()
                app._show("dashboard")
                with patch.object(app._tray, "is_ready", return_value=True), patch.object(app._tray, "minimize_to_tray"):
                    app._on_close()
                    assert not dashboard._active.is_set()
                    assert not dashboard._stopped.is_set()
                    app._restore_from_tray()
                    assert dashboard._active.is_set()
                assert "pystray" not in sys.modules, "Linux must not import tray backend"
                print("PASS: 25 pages, search, lazy caching, history, four camera canvases, fullscreen, viewer handoff, tray lifecycle")
            except Exception as error:
                errors.append(repr(error))
            finally:
                app._exit_app()

        def verify_baseline():
            try:
                capture("baseline-dashboard.png")
                app.geometry("980x640")
                capture("baseline-small.png")
                app.geometry("1340x820")
                capture("baseline-resized.png")
            finally:
                app._stop_background_tools()
                app.destroy()

        def finish():
            print(json.dumps({
                "constructor_seconds": round(constructed, 4),
                "frames_at_startup": len(app._frames),
                "widgets_at_startup": widget_count(app),
                "callback_errors": errors,
            }))
            if args.baseline and args.screenshots:
                app.after(1500, verify_baseline)
            elif args.full:
                app.after(1500, verify_full)
            else:
                app._stop_background_tools()
                app.destroy()

        app.after(100, finish)
        app.mainloop()
        if errors:
            raise AssertionError(errors)


if __name__ == "__main__":
    main()
