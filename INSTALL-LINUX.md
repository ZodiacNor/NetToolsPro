# NetTools Pro — Linux installation

Tested on Ubuntu 22.04+ and Debian 12+.

## Quick start

```bash
bash install.sh
source .venv/bin/activate
python3 nettools.py
```

## What install.sh does

1. Installs system packages via apt (requires sudo)
2. Creates a Python virtual environment in `.venv/`
3. Installs all Python dependencies from `requirements.txt`

## System packages installed

| Package | Why |
|---|---|
| `python3-pip` | pip package manager |
| `python3-venv` | virtual environment support |
| `python3-tk` | tkinter GUI backend (required by customtkinter) |
| `python3-pil.imagetk` | PIL + tkinter image integration |
| `traceroute` | Traceroute tool (app raises clear error if missing) |
| `net-tools` | `arp` command for ARP table view |
| `iproute2` | `ip` and `ss` commands for interface/connection info |
| `xdg-utils` | `xdg-open` for opening URLs and folders |

## Python dependencies

See `requirements.txt`. All packages are optional at runtime except `customtkinter` —
missing packages disable the relevant feature with a visible message.

## Known limitations (work in progress)

- System Tools: only diagnostics available on Linux (SFC/DISM are Windows-only)
- Camera Viewer: requires `opencv-python-headless` (included in requirements.txt)
- System tray: `pystray` may not work under all Wayland compositors
- Some features require `CAP_NET_RAW` or root (Live Capture, raw socket operations)
