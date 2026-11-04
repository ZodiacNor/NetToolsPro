# Workspace update — v1.10.0 (local/unreleased)

## What changed

The start page now builds only the dashboard. Each tool is created on its first visit and retained afterward, so revisiting a page keeps its state. Opening the Stream Viewer through Camera Finder still uses the same target/probe handoff. The four camera slots, decoding, polling, fullscreen handling, and glyph-safety wrappers are unchanged.

Use **Ctrl+K** to focus tool search. Search by name, category, or terms such as RTSP, packet loss, BlueZ, and wake on LAN. All words must match. **Enter** opens the first result; **Escape** clears the search. Quick-launch buttons open tools; they do not run scans.

Dashboard metrics are read on one background thread. Updates are normally sampled every two seconds; slower socket/route lookups are refreshed at most once per ten seconds. Hiding the dashboard pauses future samples; an in-flight read may finish. Metrics are local and do not initiate a network scan. Download/upload are aggregate adapter counter deltas, not an internet speed test. The first traffic sample displays `--` until a rate can be calculated. Missing permissions or metrics display N/A. The socket count includes visible TCP/UDP sockets, not just established sessions.

## Saved data

Settings and favorites now live outside the executable and its extraction directory:

| Platform | Directory |
|---|---|
| Linux | `$XDG_CONFIG_HOME/nettools-pro`, normally `~/.config/nettools-pro` |
| Windows | `%APPDATA%\NetTools Pro` |

`NETTOOLS_DATA_DIR` overrides the directory for isolated tests or an explicitly portable setup. When this override is used, legacy files are not imported.

If no new saved file exists, the app looks for the matching legacy JSON beside the source/executable (and the project parent of a `dist` executable). Valid files are copied into the new store; originals are not removed. An existing new-store file always wins, including an intentionally empty favorites list. Data already lost by an old one-file executable cannot be recovered automatically.

Writes use a temporary file in the same directory, flush it, and replace the target atomically. New files have owner-only permissions on POSIX. This protects against partial writes, but is not a substitute for backups or encryption. Favorites are still plain JSON; avoid saving credentials inside URLs. If a file is unreadable or malformed, startup warns and blocks saving that store until the original is repaired or moved and the app restarted. Other tools remain usable. Disk/permission failures are reported, not silently ignored.

## Verification on Fedora/KDE

```bash
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B tests/gui_workspace.py --full
# Optional local screenshots through KDE Spectacle:
.venv/bin/python -B tests/gui_workspace.py --full --screenshots
.venv/bin/pyinstaller --noconfirm NetToolsPro.bin.spec
.venv/bin/python -B tests/frozen_smoke.py
```

Desktop checks need access to the graphical session. The GUI fixture replaces target addresses with documentation addresses, prevents automatic adapter/ARP refreshes, and never connects to a camera. It tests all 25 pages, repeated searches without accumulating scroll containers, cached navigation, history, four synthetic camera images, fullscreen/restore, Camera Finder handoff, and mocked tray lifecycle. The binary smoke uses an isolated working/data directory and intentionally terminates only its own process group after 15 seconds.

Verification on 2026-11-04 ran **66 tests: 65 passed, one hardware Bluetooth integration test skipped** on Linux. Windows CPython under Wine passed 61 tests and skipped five (the hardware test and four Linux pipe tests). All 25 GUI pages passed on both platforms with synthetic camera images and mocked network/Bluetooth operations. Both local binaries passed 15-second isolated startup checks without stderr. Protected-code SHA-256 checks compare the camera classes, glyph wrappers, Linux tray-import guard, and Bluetooth GUI against the pre-change dirty-worktree backup, not Git HEAD.

### Startup measurements

Same machine and mocked automatic tool refreshes, timing the App constructor after Python imports:

| Measurement | Before | After |
|---|---:|---:|
| Pages created at startup | 25 | 1 |
| Tk widgets at startup | 2,125 | 257 |
| Constructor time, observed runs | 3.07–3.34 s | 0.55–0.68 s |

This is approximately five times faster window construction, not a claim about cold-start binary extraction or network operation speed. Once every tool has been visited, those pages remain in memory by design.

## Limits and next checks

- Physical RTSP/MJPEG camera playback and active Bluetooth radio scanning still need a user-controlled hardware acceptance check. The synthetic test does not certify those paths end-to-end.
- Windows tray behavior was checked with mocks under Wine. A local Windows executable was built, but physical Windows and native tray acceptance tests remain pending.
- Rapid resize/screenshot sequences can produce intermittent text redraw artifacts on this KDE/XWayland session. Similar artifacts were reproduced in the untouched backup UI, including the old footer/activity area. The cause is not established; no font installation, driver changes, or desktop configuration changes were attempted.
- The Linux binary is a local Fedora build. The existing published release files and tags were not changed.
- Stream Wall profiles, further platform support, and broader visual redesign are deferred to separate, testable changes.
