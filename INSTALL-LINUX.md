# NetTools Pro — Linux installation

Tested on Ubuntu 22.04+, Debian 12+, and Fedora 43.

## Quick start

```bash
bash install.sh
source .venv/bin/activate
python3 nettools.py
```

## What install.sh does

1. Detects `dnf` or `apt` and installs system packages (requires sudo)
2. Creates a Python virtual environment in `.venv/`
3. Installs all Python dependencies from `requirements.txt`
4. Rebuilds `.venv/` automatically if the system Python version has changed

## System packages installed

`install.sh` auto-detects `dnf` or `apt` and installs distro-appropriate packages.

| Distro | Packages |
|---|---|
| Ubuntu / Debian | `python3-pip`, `python3-venv`, `python3-tk`, `python3-pil.imagetk`, `traceroute`, `net-tools`, `arp-scan`, `iproute2`, `xdg-utils`, `nmap`, `lshw`, `dmidecode` |
| Fedora | `python3-tkinter`, `traceroute`, `net-tools`, `arp-scan`, `iproute`, `xdg-utils`, `nmap`, `lshw`, `dmidecode` |

## ARP Scan note

`arp-scan` requires root privileges or `CAP_NET_RAW` to run. The app will show a clear
message if the binary is installed but does not have the required privileges.

## Python dependencies

See `requirements.txt`. All packages are optional at runtime except `customtkinter` —
missing packages disable the relevant feature with a visible message.

## Known limitations (work in progress)

- System Tools: only diagnostics available on Linux (SFC/DISM are Windows-only)
- Camera Viewer: requires `opencv-python-headless` (included in requirements.txt)
- System tray: `pystray` may not work under all Wayland compositors
- Some features require `CAP_NET_RAW` or root (Live Capture, raw socket operations)
