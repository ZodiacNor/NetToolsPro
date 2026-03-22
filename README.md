# NetTools Pro

> A personal network diagnostics and utility toolkit — built from scratch as my first Python project.

---

## ⚠️ Disclaimer

This is my **first real software project**. I am not a professional developer — I am a maritime engineer and outdoor enthusiast who got curious about Python and decided to build something useful.

**What that means for you:**

- The code is almost certainly full of bugs
- Some features may be incomplete or behave unexpectedly
- Error handling may be inconsistent
- Documentation may be lacking in places
- **Use at your own risk**

This software is provided **AS IS**, with no warranties or guarantees of any kind. See the [LICENSE](LICENSE) for full details.

That said — feedback, bug reports, suggestions, and pull requests are **very welcome!** 🙏

---

## What is NetTools Pro?

NetTools Pro is a Windows desktop application for network diagnostics and troubleshooting. It was built to solve real problems I run into in my daily work — things like finding IP cameras on unfamiliar networks, diagnosing connectivity issues, and analyzing network traffic.

It is built in Python with a modern GUI using CustomTkinter.

---

## Features

- **Network adapter overview** — view current adapter configuration including IP, subnet mask, and gateway
- **Ping tool** — test connectivity to any host or IP address
- **Traceroute** — trace the path to a destination
- **DNS lookup** — resolve hostnames and inspect DNS records
- **IP camera finder** — scan for IP cameras on the local network
- **Packet capture analysis** — load and analyze `.pcap`/`.pcapng` capture files
- **Camera candidate detection** — identify likely camera devices from capture data, including:
  - DHCP-based device discovery
  - Subnet mismatch detection between your adapter and the detected camera
  - Suggested temporary static IP configuration
  - Candidate RTSP stream URL generation (Hikvision, Dahua, Axis, and generic paths)
- **IP conflict detection** — identify conflicting IPs on the network

---

## Requirements

- **Windows 10 / 11** (64-bit)
- Python 3.10+ (if running from source)

### Python dependencies (for running from source)

```
customtkinter>=5.2.2
psutil>=5.9.0
dnspython>=2.6.0
Pillow>=10.0.0
opencv-python-headless>=4.8.0
```

Install with:

```bash
pip install -r requirements.txt
```

---

## Running from source

```bash
git clone https://github.com/YOUR_USERNAME/NetTools-Pro.git
cd NetTools-Pro
pip install -r requirements.txt
python nettools.py
```

> Some features (such as live packet capture) may require running as Administrator on Windows.

---

## Building the executable

NetTools Pro uses [PyInstaller](https://pyinstaller.org/) to build a standalone `.exe`.

```bash
pip install pyinstaller
pyinstaller NetTools_Pro.spec
```

The built executable will appear in the `dist/` folder.

---

## Known limitations

- Windows only — no macOS or Linux support planned at this time
- Live packet capture requires Administrator privileges
- Some camera detection heuristics may produce false positives or miss devices depending on network configuration
- RTSP stream URLs are generated as candidates only — the tool does not verify whether streams are actually accessible
- The tool never automatically changes your network adapter configuration — recommendations only

---

## Contributing

All contributions are welcome — whether that is:

- Bug reports
- Feature suggestions
- Code improvements
- Documentation fixes

Please open an issue or submit a pull request. I am learning as I go, so constructive feedback is genuinely appreciated.

---

## License

This project is licensed under the **MIT License**.

Copyright (c) 2026 Bengt Simon Røch Dragseth

See [LICENSE](LICENSE) for full license text.

---

## Author

**Bengt Simon Røch Dragseth**

Maritime engineer, outdoor enthusiast, and amateur developer from Northern Norway.
Built this project to scratch my own itch — and to learn Python properly along the way.

---

*If this tool helps you, great. If you find bugs, even better — let me know!* 😄
