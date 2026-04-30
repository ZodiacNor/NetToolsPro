# NetTools Pro v1.9.0

NetTools Pro v1.9.0 is a cross-platform release with standalone builds for both Windows and Linux. It introduces a working 4-slot Camera Stream Wall, Linux GUI rendering improvements, dark-themed input context menus, and cleaner build and release handling.

---

## Summary

- First polished cross-platform release: Windows and Linux standalone builds
- 4-slot Camera Stream Wall built around the established stream engine
- Linux GUI fixes for missing glyphs and rendering artifacts
- Improved Windows build script reliability
- Cleaner repository and release hygiene

---

## Downloads

| Platform | Asset |
|---|---|
| Windows x64 | `NetToolsPro-windows-x64.exe` |
| Linux x86_64 | `NetToolsPro-linux-x86_64.bin` |

---

## Windows

Download and run:

```text
NetToolsPro-windows-x64.exe
```

Some diagnostics or system-level operations may require Administrator privileges.

### Build notes

The Windows build process has been improved. `build.bat` now detects Python more reliably:

- Uses `py -3` when the Python Launcher is available
- Falls back to `python` when `py` is not available
- Creates and uses `.venv`
- Runs pip, compile checks, and PyInstaller through `.venv\Scripts\python.exe`
- Builds with `NetTools Pro.spec`
- Copies the build artifact to `release\NetToolsPro-windows-x64.exe`

To run the build:

PowerShell:

```powershell
.\build.bat
```

Command Prompt:

```cmd
build.bat
```

---

## Linux

Download and run:

```bash
chmod +x NetToolsPro-linux-x86_64.bin
./NetToolsPro-linux-x86_64.bin
```

The Linux binary is provided for x86_64 Linux systems. It has been built and tested on Fedora. For other distributions, running from source or rebuilding locally may provide the best compatibility.

### Build notes

The Linux standalone binary is built with PyInstaller using `NetToolsPro.bin.spec`:

```bash
source .venv/bin/activate
python3 -m py_compile nettools.py
pyinstaller --clean -y NetToolsPro.bin.spec
chmod +x dist/NetToolsPro.bin
```

---

## Camera Stream Wall

This release adds a working 4-slot Camera Stream Wall built around the established single-camera stream engine.

Highlights:

- View up to four camera streams simultaneously
- RTSP, MJPEG, JPEG, and HTTP camera endpoint support
- Per-slot URL and credential input
- Camera Finder integration
- Snapshot support
- Fullscreen and restore per slot
- Designed for local IP camera troubleshooting and service workflows

The stream engine was kept conservative and built around the known working single-stream implementation to preserve MJPEG and RTSP behavior and avoid regressions.

---

## GUI Improvements

- Fixed missing icon glyphs and black square artifacts on Linux
- Replaced unstable emoji symbols with font-safe text labels
- Improved sidebar and category rendering on Fedora and other Linux distributions
- Added dark-themed right-click context menus for key text input fields
- Added Cut, Copy, Paste, and Select All to relevant input fields
- Context menus now close on outside click, Escape, and focus loss
- Fixed Camera Stream Wall fullscreen and restore behavior so slots return cleanly to the 2x2 layout
- Fixed delayed Tk callback error handling in several UI paths

---

## Build and Repository Hygiene

- Improved Windows `build.bat` reliability
- Added Linux PyInstaller spec (`NetToolsPro.bin.spec`)
- Added a local `release/` output folder, excluded from version control
- Removed obsolete PowerShell helper scripts from the repository
- Updated `.gitignore` for Python cache, virtual environments, build output, logs, and local release artifacts
- Modernized the README for cross-platform release

---

## Responsible Use

NetTools Pro is intended for legitimate diagnostics, troubleshooting, learning, and authorized network work.

- Use it only on systems and networks you own or have permission to test.
- Some features may require Administrator or root privileges depending on platform and operation.
- All actions are user-initiated; the operator is responsible for how the tool is used.

---

## Known Notes and Compatibility

- The Linux binary has been built and tested on Fedora x86_64. Compatibility with older or significantly different distributions is not guaranteed; running from source is recommended where the binary does not work out of the box.
- Some network and system tools may require Administrator or root privileges.
- Some external utilities used by the toolkit may depend on packages provided by the host operating system or distribution.

---

## Verification

SHA-256 checksums are published alongside the release files in `SHA256SUMS.txt`.

```text
274ab798b6c4630443b3b4428a7379b263e7263e34c58fa1faace43dc8134bb5  NetToolsPro-linux-x86_64.bin
f50d7ce473896896e86eadb4d147c1085bc36cc3ef84f7f80cc0c82eaa70925d  NetToolsPro-windows-x64.exe
```

Users are encouraged to verify downloads before running them:

```bash
sha256sum -c SHA256SUMS.txt
```
