# Windows build — 1.10.0

The local Windows executable is `dist/NetToolsPro.exe` (x64 PE GUI).
It includes the same 1.10.0 workspace code as the Linux binary. File and product
version resources now match the application version.

## Build on Windows

Install Windows CPython 3.11 or newer, then run:

```bat
build.bat --setup
build.bat
```

Set `NETTOOLS_PYTHON` to a Python executable when the launcher is not on PATH.
The environment is `.venv-windows`, separate from Linux `.venv`. Build dependencies
are pinned in `requirements-windows-build.txt`. Setup installs project dependencies;
the normal build runs tests and packages without upgrading dependencies.

The script uses `build/windows-pyinstaller` and `build/windows-staging`. It backs
up an existing Windows executable before replacing it, and preserves the Linux
binary and all existing release files. It no longer deletes `build/` or `dist/`.
The Windows spec uses the Windows tray backend and disables UPX.

## Local Wine verification

The project has an isolated `build/windows-wine` prefix containing Windows
CPython 3.13.15 at `C:\Python313`. It was seeded from the previously verified
Media Organizer toolchain, without changing that source prefix. User Wine
profiles and desktop associations were not changed.

```bash
bash build-windows-wine.sh setup
bash build-windows-wine.sh build
bash build-windows-wine.sh gui
```

The helper requires a prepared project-owned CPython prefix. It verifies its
private N: drive points to this project. Wine and CPython must already exist;
it does not install system packages.

Verification on 2026-11-04: 66 source unit tests (61 passed, five skipped), a real
Windows Tk GUI visiting all 25 pages, search, synthetic four-slot camera rendering,
fullscreen/restore, viewer handoff, scan cancellation/restart, bandwidth timers,
and mocked tray lifecycle. Packaged PE startup also stayed alive for 15 seconds
with isolated saved data and no stderr. This is Wine evidence,
not a physical Windows, real camera, Bluetooth, or Windows tray acceptance test.
No provider, camera, network scan, or Bluetooth discovery was invoked.

The GUI test now waits for Windows Configure events before measuring resized
widgets. It retains the minimum-window layout assertion and applies the
Linux-only no-pystray assertion only on Linux.
