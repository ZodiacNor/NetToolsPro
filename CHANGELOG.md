# Changelog

All notable changes to NetTools Pro are documented here.

## [Unreleased — v1.9.0-dev] - Linux port in progress

### Added
- **Linux bootstrap** — `install.sh` detects `dnf` or `apt`, installs system packages, creates `.venv`, and installs `requirements.txt`; supports Ubuntu/Debian and Fedora
- `INSTALL-LINUX.md` — concise installation guide for Linux
- `BaseToolFrame._safe_after()` — thread-safe wrapper around `self.after()` that silently drops scheduling errors (`RuntimeError`, `TclError`) when a widget is destroyed or the event loop is not yet running

### Changed
- Linux Layer 2 discovery now uses `arp-scan` instead of `netdiscover`

### Fixed
- [UI] Fixed missing icons and black glyph squares on Linux
- [UI] Replaced unstable emoji with safe labels
- [UI] Styled context menu for dark theme
- [UI] Fixed context menu not closing on outside click
- **Linux startup crash: `main thread is not in main loop`** — `ConnectionsFrame._worker` was reading `tk.StringVar.get()` directly from a background thread; value is now snapshotted in the main thread before the worker starts
- **Linux startup crash: `self.after()` from worker threads** — `InterfacesFrame`, `ConnectionsFrame`, and `ARPFrame` all auto-refresh on init, spawning threads before the Tk mainloop is fully active; all `self.after(0, ...)` calls in these workers replaced with `self._safe_after(0, ...)`

### Infrastructure (platform_utils — fase 1–8)
- `platform_utils/` package: `detect`, `net`, `shell`, `scripting`, `capabilities`, `parsers/linux`, `parsers/windows`
- `system_backend.py`: `SystemBackend` ABC, `WindowsBackend` (full), `LinuxBackend` (diagnostics only — fase 8)
- Linux network wrappers: `ip addr`, `ip neigh`, `ip -4 route show default`, `ss -anop`
- `build.bat` patched with `py -3` launcher strategy and pip retry loop
- [BUILD] Improved Linux .bin build stability
- [REPO] Updated ignore rules for local build, cache, runtime, and agent artifacts

## [1.9.0] - 2026-04-22

### Added
- Netdiscover backend in `platform_utils/net.py`
- Netdiscover GUI via `NetdiscoverFrame`
- Linux bootstrap script `install.sh`
- Linux installation guide `INSTALL-LINUX.md`
- Linux diagnostics in `LinuxBackend`

### Changed
- `SystemToolsFrame` refactored to backend-driven architecture
- `nettools.py` reduced by moving direct PowerShell/SFC/DISM handling into `system_backend.py`
- `build.bat` improved with Python detection and pip retry handling

### Fixed
- Thread-safety issue for Tkinter updates from worker threads
- Startup flicker where the app visually switched through tabs before landing on Dashboard
- Missing `traceroute` binary now handled with explicit user-facing Linux error
- Linux live capture raw socket path corrected for platform-specific socket behavior

### Linux
- ARP parsing via `ip neigh`
- Default gateway parsing via `ip route`
- `LinuxBackend` added with diagnostics support
- Netdiscover integrated as a Linux-only feature
- Conditional rendering for unsupported platform features

### Technical
- Backend owns commands, GUI owns control flow
- Generator-based backend streams with `yield`
- JSON streaming for netdiscover device data
- `_safe_after()` added for thread-safe UI updates
- `install.sh` handles system dependencies and virtual environment setup

## [1.8.1] - 2026-03-26

### Changed
- Sidebar: replaced flat 23-item list with collapsible accordion categories (Diagnostics, Discovery, Camera, Monitoring, System, My Tools); only one category open at a time; Dashboard always visible as standalone button; tool buttons indented within categories; scrollable navigation area

## [1.8.0] - 2026-03-26

### Added
- **Dashboard** — live system stats start page with CPU, RAM, Disk, Network I/O, Active Connections, Local IP, Gateway; color-coded usage thresholds; auto-refresh every 2s; recent session activity feed; replaces Ping as default view
- **System Tray** — minimize to tray on window close (pystray); right-click menu with Show/Exit; programmatic tray icon; graceful fallback if pystray unavailable
- **Settings Persistence** — SettingsManager class with JSON-backed settings.json; theme preference now persists across sessions; minimize-to-tray toggle

### Changed
- Theme toggle now persists selection via SettingsManager (was session-only)
- Default start page changed from Ping to Dashboard
- Added pystray to requirements.txt and PyInstaller hidden-imports

## [1.7.0] - 2026-03-26

### Added
- **Live Packet Capture** — raw socket capture on selected adapter with protocol filtering (TCP/UDP/ICMP/Other), IP packet parsing with ports and TCP flags display, color-coded output by protocol, requires Administrator
- **WHOIS Lookup** — raw TCP WHOIS queries via stdlib socket (no python-whois dependency); automatic referral following (IANA to authoritative server); key field highlighting for netname, org, registrar, dates, abuse contacts
- **mDNS / Bonjour Discovery** — UDP multicast listener on 224.0.0.251:5353; DNS wire format parser for A/PTR/SRV records; device grouping by hostname; service type labeling (HTTP, RTSP, AirPlay, Chromecast, etc.); active PTR query stimulus

## [1.6.0] - 2026-03-24

### Added
- **Export output** — Export button on 10 tools (Ping, Port Scanner, Traceroute, DNS, Net Scanner, Interfaces, Connections, ARP, Camera Finder, Cam Analysis) saves output to .txt file via save dialog
- **Session History** — History sidebar panel shows all tool actions performed this session with timestamps; supports clear and export to file
- **Favorites** — Favorites sidebar panel for saving/loading frequently used targets and RTSP URLs; persists to `favorites.json`; type filter (All/Host/RTSP URL/Scan Profile/Script Path); Use copies to clipboard, Delete removes entry
- **Save as Favorite** — Save button on 6 tools (Ping, Port Scanner, Traceroute, Net Scanner, Stream Viewer, Cam Analysis) to quickly bookmark targets and URLs
- `SessionHistory` class for in-memory session logging with listener/subscriber pattern
- `FavoritesManager` class with JSON persistence for saved favorites
- `BaseToolFrame.export_output()` shared helper for file export
- `BaseToolFrame._save_favorite_dialog()` shared helper for favorite save dialog with CTkToplevel name input

## [1.5.1] - 2026-03-24

### Fixed
- **Network Scanner: Windows 95 look** — Added `style.theme_use("default")` to force the ttk theme away from native Windows rendering which caused classic 3D-border headings and legacy widget appearance
- **Network Scanner: Heading relief** — Added `relief="flat"` and `borderwidth=0` to Treeview heading style, matching the dark theme used by other Treeview instances in the app
- **Network Scanner: Scrollbar mismatch** — Replaced `tk.ttk.Scrollbar` with `ctk.CTkScrollbar` for visual consistency with the rest of the CustomTkinter UI

## [1.5.0] - 2026-03-24

### Added
- **Port Scanner: Scan profiles** — Quick Scan, Web Scan, Camera Scan, Common Ports, Full (1-1024), and Custom with dropdown selector
- **Service fingerprinting** — lightweight identification for open ports: HTTP (Server + title), HTTPS (Server), RTSP (OPTIONS handshake + Server), SSH/FTP/SMTP/MySQL/VNC (banner grab), SMB/RDP (type identification)
- **Fingerprinting toggle** — checkbox to enable/disable service detection per scan
- **Copy Results button** — copies all open port results to clipboard in formatted text
- **Service Details summary** — post-scan section showing banner/vendor details for all fingerprinted ports
- **Profile description label** — shows which ports will be scanned for the selected profile

### Changed
- Port Scanner result columns updated: PORT, STATE, SERVICE, DETAILS (was PORT, PROTO, STATE, SERVICE)
- Scan header now shows profile name and fingerprint status
- Custom scan mode options hidden by default, shown only when "Custom" profile selected
- `_scan_one()` now returns service + detail alongside port state

## [1.4.0] - 2026-03-24

### Added
- **Network Scanner: Host enrichment** — each discovered host now shows MAC address, vendor, open ports, hostname, and device type
- **Device type classification** — automatic identification: Camera (Confirmed/Likely/Possible), Router/Gateway, Windows PC, Linux/Unix, Server, Web Device, Unknown
- **Port snapshot** — fast TCP probe of 8 common ports (HTTP, HTTPS, RTSP, SSH, SMB, RDP, HTTP-Alt, HTTPS-Alt) per host
- **MAC/vendor lookup** — ARP cache integration with camera OUI database for vendor identification
- **Split-pane UI** — treeview with color-coded device types (left) + detail panel (right)
- **Host detail view** — full evidence display: basic info, MAC/vendor, ports & services, device classification with reasoning, camera-specific RTSP candidates
- **Two-phase scan** — Phase 1: ping sweep discovery, Phase 2: parallel enrichment with progress tracking
- **HTTP camera banner detection** — lightweight HTTP probe for camera keyword matching during enrichment

### Changed
- Network Scanner upgraded from simple ping-sweep list to professional network discovery tool
- Results now displayed in sortable treeview with colored device-type tags instead of plain text output

## [1.3.0] - 2026-03-24

### Added
- **Auto-Conclusion engine** — generates a plain-language technical conclusion from all available evidence (reachability, ports, vendor, MAC class, ping)
- **Smart Action engine** — selects ONE primary recommended next action with evidence-based reasoning and optional secondary action
- **Best Stream Match** — identifies and highlights the single best stream candidate with confidence label (Verified / Likely / Guess)
- **Failure Reasoning** — dedicated "Why Access May Fail" section explaining specific obstacles (subnet mismatch, closed ports, gateway-only MAC, etc.)
- **Confidence Breakdown** — transparent per-factor scoring display with network-context modifiers (ping, subnet, MAC class adjustments)
- `score_camera_breakdown()` helper for itemized score decomposition
- `CANDIDATE_SCORE_WEIGHTS` dict with human-readable labels for each scoring factor

### Changed
- Candidate detail view restructured: Camera Candidate → MAC/Vendor → Network Position → Path/Route → Confidence Breakdown → Final Assessment → Recommended Next Action → Best Stream Match → Why Access May Fail → Suggested Adapter Config → Candidate RTSP URLs
- Smart Action replaces generic numbered step list with a single evidence-driven recommendation
- `score_camera_candidate()` refactored to use shared `CANDIDATE_SCORE_WEIGHTS` constant

## [1.2.0] - 2026-03-24

### Added
- **MAC classification** — `_classify_mac()` distinguishes direct camera MAC vs gateway next-hop MAC vs unavailable, with clear labeling
- **Gateway detection** — `_get_default_gateway()` parses Windows route table to identify next-hop for routed traffic
- **Path / Route visualization** — ASCII route diagrams in candidate detail view (e.g., `Adapter → [Gateway] → Camera`)
- **Ping reachability evidence** — ICMP ping result shown in candidate detail with route confirmation
- **Confidence label upgrades** — "Confirmed Camera" / "Likely Camera" / "Manual Target" / "Not Reachable" based on combined evidence

### Changed
- Candidate detail view restructured into clear sections: Camera Candidate, MAC / Vendor, Network Position, Path / Route, Evidence, Recommended Next Action, Suggested Adapter Config, Candidate RTSP URLs
- MAC/Vendor section distinguishes direct vs gateway MAC with explanatory labels
- Evidence section adapts OUI and ARP display based on MAC classification
- Recommendations incorporate ping reachability for smarter next-step advice
- `_worker_direct_target()` now performs gateway detection, MAC classification, and ping checks
- `_analyze_and_score()` propagates mac_info, ping_ok, gateway_ip to all candidates

## [1.1.1] - 2026-03-24

### Added
- **Cam Analysis: Direct target mode** — enter a camera IP directly for focused analysis without relying on adapter-based discovery alone
- Mode indicator label shows active analysis type during runs

### Changed
- Cam Analysis now supports three workflows: adapter-based discovery, direct target analysis, and combined (adapter context + specific target)
- Target IP field includes validation and clear placeholder text

## [1.1.0] - 2026-03-24

### Added
- **RTSP stream validation** — RTSP OPTIONS handshake check to verify stream endpoints actually respond
- **Stream confidence levels** — candidates labeled as Verified, Likely, or Guess based on probe evidence
- **"Show all candidates" toggle** in Stream Viewer to show/hide unverified stream candidates
- **Expanded subnet/routing analysis** — reachability states: direct, possibly routed, likely unreachable
- RFC 1918 class comparison and routing-aware recommendations
- Subnet reachability display in Camera Finder detail panel
- Vendor-aware RTSP probing with priority sorting based on OUI/HTTP vendor hints
- 11 new RTSP path templates (Hikvision sub-streams, Dahua alt, Samsung, Hanwha, generic)
- 6 new HTTP stream/snapshot paths (Mobotix, Axis alt, generic MJPEG)

### Fixed
- **Sidebar navigation sync** — "View Stream" from Camera Finder now correctly updates sidebar selection
- Stream candidate tuple handling in connect logic

### Changed
- `compare_adapter_to_candidate()` returns expanded dict with reachability state and human-readable explanation
- Recommendation section adapts to routing context instead of blanket "will fail" messaging

## [1.0.0] - 2026-03-01

### Initial release
- Network diagnostic toolkit with 16 tools
- Camera Finder with ONVIF, SSDP, ping sweep, HTTP banner, RTSP probe
- Stream Viewer with HTTP/MJPEG/JPEG and RTSP (via OpenCV) support
- Camera Analysis with ARP cache, live DHCP capture, candidate scoring
- Single-file portable Windows executable via PyInstaller
