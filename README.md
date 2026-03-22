# 🌐 NetTools Pro

> **v1.0.0 — Network Engineering Toolkit for Windows**
> *"Small tools. Big control."*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)]()
[![Status](https://img.shields.io/badge/Status-Alpha%20%E2%80%93%20First%20Project-orange.svg)]()

---

## ⚠️ Honest Disclaimer

This is my **first real software project**. I am a maritime engineer and outdoor enthusiast — not a professional developer.

**What that means:**
- The code is almost certainly full of bugs
- Some features may be incomplete or behave unexpectedly
- Error handling may be inconsistent
- **Use at your own risk — provided AS IS**

That said — feedback, bug reports, and pull requests are **genuinely very welcome!** 🙏

---

## 📌 Overview

NetTools Pro is a portable, all-in-one network diagnostic toolkit designed for:

- 🔧 Troubleshooting networks and connectivity issues
- 📡 Discovering devices — including IP cameras
- 🎥 Viewing live streams (RTSP, MJPEG, JPEG)
- 🛠 Running system diagnostics and scripts
- 📊 Monitoring connections, bandwidth, and interfaces

Built with **CustomTkinter**, runs as a **standalone executable** with no installation required.

---

## ✨ Features

### 🧭 Network Tools
| Tool | Description |
|---|---|
| Ping | Multi-threaded ping with response time |
| Port Scanner | Scan open ports on any host |
| Traceroute | Trace the path to any destination |
| DNS Lookup | Resolve hostnames and inspect records |
| Network Scanner | CIDR-based host discovery |
| ARP Table Viewer | View active ARP cache |
| Subnet Calculator | Calculate subnets and ranges |

### 📡 Device & Camera Tools
- IP Camera Finder (ONVIF, SSDP, HTTP, RTSP)
- Camera candidate analysis from packet captures
- DHCP inference and ARP-based device detection
- Subnet mismatch detection with suggested IP config
- Vendor detection via MAC OUI lookup
- IP conflict / duplicate address detection

### 🎥 Stream Viewer
- HTTP MJPEG / JPEG stream support
- Full RTSP playback via OpenCV (H.264)
- Auto stream probing across HTTP and RTSP
- One-click connect to detected streams

### 📊 Monitoring
- Bandwidth monitor per interface
- Active TCP/UDP connections viewer
- Network interfaces overview

### ⚙️ System Tools
- Safe and aggressive Windows debloat modes
- System diagnostics (SFC, DISM)
- Backup and restore system states

### 🧪 Script Lab
- Built-in script editor
- Run PowerShell, Python, Batch, and CMD
- Real-time output logging

---

## 🧠 Smart Features

- 🔍 Camera detection via DHCP analysis, ARP cache, and RTSP probing
- 🌐 Subnet mismatch detection with automatic IP config suggestion
- 🎯 Confidence scoring for detected camera candidates
- 🚫 Noise filtering — ignores OEM chatter and irrelevant broadcast traffic
- 📋 Copy-ready commands (RTSP URLs / netsh config)

---

## ⚙️ Installation

### 🔹 Option 1 — Portable EXE *(Recommended)*

1. Download the latest release from the [Releases](https://github.com/ZodiacNor/NetToolsPro/releases) page
2. Run `NetTools Pro.exe`
3. No installation required ✅

### 🔹 Option 2 — Run from Source

```bash
git clone https://github.com/ZodiacNor/NetToolsPro.git
cd NetToolsPro
pip install -r requirements.txt
python nettools.py
```

> Some features (live capture, raw sockets) may require running as **Administrator**.

---

## 🏗️ Build from Source

```bash
build.bat
```

Includes PyInstaller packaging, automatic dependency install, OpenCV bundling, and produces a fully portable `.exe` in the `dist/` folder.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| customtkinter | Modern GUI framework |
| psutil | System and network stats |
| Pillow | Image handling |
| dnspython | DNS queries |
| opencv-python-headless | RTSP stream playback *(optional)* |

---

## 🎥 RTSP Support

NetTools Pro supports live RTSP streams via OpenCV — no VLC required.

Common stream URL formats supported:
```
rtsp://[camera-ip]:554/Streaming/Channels/1        # Hikvision
rtsp://[camera-ip]:554/cam/realmonitor?channel=1   # Dahua
rtsp://[camera-ip]:554/axis-media/media.amp        # Axis
rtsp://[camera-ip]:554/live.sdp                    # Generic
rtsp://[camera-ip]:554/stream1                     # Generic
```

---

## 🛡️ Safety & Philosophy

- ❌ No automatic system modifications
- ❌ No forced network changes
- ✅ All actions are user-controlled
- ✅ Designed for ethical and professional use

---

## 📁 Project Structure

```
NetToolsPro/
├── nettools.py          # Main application
├── build.bat            # Build script
├── requirements.txt     # Python dependencies
├── NetTools_Pro.spec    # PyInstaller spec
├── version_info.txt     # Windows version metadata
├── LICENSE              # MIT License
└── README.md
```

---

## 🖥️ Screenshots

> *Screenshots coming soon — contributions welcome!*

---

## 🚀 Roadmap

- [ ] Full packet capture integration
- [ ] AI-assisted network diagnostics
- [ ] Cybersecurity modules
- [ ] Remote device management

---

## 🤝 Contributing

All contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

Bug reports, feature requests, and honest feedback are equally appreciated. I am learning as I go! 😄

---

## 👨‍💻 Author

**Bengt Simon Røch Dragseth**
Maritime engineer, outdoor enthusiast, and amateur developer from Northern Norway.

🔗 [github.com/ZodiacNor](https://github.com/ZodiacNor)

---

## 📄 License

MIT License — Copyright (c) 2026 Bengt Simon Røch Dragseth

See [LICENSE](LICENSE) for full details.

---

## ⭐ Support

If you find this useful:
- ⭐ Star the repo
- 🛠 Share feedback via Issues
- 🚀 Help improve it with a pull request
