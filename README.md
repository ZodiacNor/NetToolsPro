# NetTools Pro

> Cross-platform network diagnostics, camera discovery, stream viewing, and system utility toolkit.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

NetTools Pro is a portable desktop toolkit for network troubleshooting, camera discovery, live stream viewing, system diagnostics, and utility workflows.

It is built with Python and CustomTkinter, with standalone builds available for Windows and Linux.

---

## Downloads

Prebuilt standalone binaries are available from the [GitHub Releases](https://github.com/ZodiacNor/NetToolsPro/releases) page.

| Platform | Release asset | Notes |
|---|---|---|
| Windows x64 | `NetToolsPro-windows-x64.exe` | Portable executable |
| Linux x86_64 | `NetToolsPro-linux-x86_64.bin` | Portable Linux binary |

### Linux

```bash
chmod +x NetToolsPro-linux-x86_64.bin
./NetToolsPro-linux-x86_64.bin
```

### Windows

Download and run:

```text
Run NetToolsPro-windows-x64.exe
```

Some tools may require Administrator or root privileges depending on the operation.

---

## Platform Support

| Platform | Status |
|---|---|
| Windows | Supported |
| Fedora Linux | Supported during current Linux port work |
| Ubuntu / Debian-style Linux distributions | Supported by `install.sh` package detection |

Linux support is actively improving. Some low-level diagnostics and capture features may depend on distribution packages and local privileges.

---

## Highlights

### Network Diagnostics

- Ping testing
- Port scanning
- Traceroute
- DNS lookup
- CIDR/network scanning
- ARP table inspection
- Subnet calculations
- Interface overview

### Camera Discovery & Stream Wall

- IP camera discovery
- HTTP, RTSP, MJPEG, and JPEG stream support
- 4-slot Camera Stream Wall
- Camera Finder integration
- Stream probing and candidate detection
- Snapshot support
- Useful for testing local IP cameras and service cameras

### Monitoring

- Interface statistics
- Bandwidth monitoring
- Active TCP/UDP connection view
- System and network status overview

### System Utilities

- System diagnostics
- Backup/restore helper workflows
- Windows utility functions
- Linux-aware command wrappers where supported

### Script Lab

- Built-in script editor
- Run and inspect command/script output
- Useful for repeatable diagnostics and field troubleshooting

### Cross-platform Build

- PyInstaller-based Windows executable builds
- PyInstaller-based Linux onefile binary builds
- Shared codebase with platform-specific wrappers where needed
- Fedora and Ubuntu/Debian-aware Linux bootstrap script

---

## Safety and Responsible Use

NetTools Pro is intended for legitimate troubleshooting, diagnostics, learning, and authorized network work.

Use it only on systems and networks you own or have permission to test.

The application is designed around user-controlled actions. It does not automatically modify network or system settings without user action, but some features may require elevated privileges.

---

## Run from Source

### Linux

```bash
git clone https://github.com/ZodiacNor/NetToolsPro.git
cd NetToolsPro

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

python3 nettools.py
```

You can also use the Linux bootstrap script:

```bash
bash install.sh
source .venv/bin/activate
python3 nettools.py
```

### Windows

```powershell
git clone https://github.com/ZodiacNor/NetToolsPro.git
cd NetToolsPro

py -3 -m venv .venv
.venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

python nettools.py
```

---

## Build from Source

### Linux binary

```bash
cd NetToolsPro
source .venv/bin/activate

python3 -m py_compile nettools.py
pyinstaller --clean -y NetToolsPro.bin.spec

chmod +x dist/NetToolsPro.bin
```

### Windows executable

```bat
cd NetToolsPro
build.bat
```

Or build directly with PyInstaller:

```powershell
pyinstaller --clean -y "NetTools Pro.spec"
```

---

## Dependencies

Main Python dependencies include:

- `customtkinter`
- `Pillow`
- `opencv-python-headless`
- `psutil`
- `dnspython`
- `pystray`

Additional system tools may be required for some Linux diagnostics, depending on the distribution and feature used.

---

## Project Structure

```text
NetToolsPro/
├── nettools.py              # Main application
├── platform_utils/          # Platform-specific wrappers/helpers
├── system_backend.py        # System/backend operations
├── requirements.txt         # Python dependencies
├── install.sh               # Linux bootstrap installer
├── build.bat                # Windows build script
├── NetToolsPro.bin.spec     # Linux PyInstaller spec
├── NetTools Pro.spec        # Windows PyInstaller spec
├── INSTALL-LINUX.md         # Linux setup notes
├── CHANGELOG.md             # Release history
├── LICENSE                  # MIT License
└── README.md
```

---

## Screenshots

Screenshots will be added in a future release.

---

## Roadmap

Planned and ongoing work includes:

- Improved Camera Finder to Stream Wall workflow
- Persistent Stream Wall profiles
- Better cross-platform diagnostics
- Expanded Linux support
- More structured release packaging
- Additional documentation and screenshots

---

## Contributing

Bug reports, feature requests, and pull requests are welcome.

If you want to contribute:

1. Fork the repository
2. Create a feature branch
3. Make focused changes
4. Submit a pull request with a clear description

Please keep changes scoped and avoid mixing unrelated fixes in the same pull request.

---

## Author

Created by Bengt Simon Røch Dragseth.

NetTools Pro started as a practical field tool for network diagnostics, camera troubleshooting, and system utility workflows.

---

## License

MIT License.

See [LICENSE](LICENSE) for details.
