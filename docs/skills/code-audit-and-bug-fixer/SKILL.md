---
name: code-audit-and-bug-fixer
version: 1.2
description: >
  Audit an existing software project for real bugs, broken logic, thread safety issues, resource leaks,
  UI/layout problems, portability gaps, packaging issues, and theme inconsistencies — then apply safe,
  targeted fixes directly in the codebase. Use this skill whenever the user asks to audit a project,
  review and fix bugs, check a codebase, verify portability, fix layout/theme issues, inspect for thread
  safety, do a final polish pass, stabilize a project, or investigate tracebacks and runtime problems.
  Especially strong with Python desktop apps using Tkinter/CustomTkinter, threading, sockets, subprocesses,
  OpenCV/video streams, and PyInstaller on Windows.
  v1.2: Merged best of two skill versions. Added frozen-app path fix, NetTools Pro specific patterns,
  SIO_RCVALL cleanup, accordion sidebar checks, checkbox audit format, and concrete code fix examples.
---

# Code Audit and Bug Fixer v1.2

You are performing a structured audit of a software project. Your job is to find real bugs, unsafe patterns,
broken UX, and packaging/runtime problems — then fix them with minimal, safe edits that preserve the existing
architecture.

This skill is built for medium-to-large Python desktop applications, especially single-file or small
multi-file GUI apps heading toward real-world use and packaging. It works best with
Tkinter/CustomTkinter, threading/queue patterns, socket/network tools, OpenCV/video streams,
and PyInstaller workflows on Windows.

Core principle:
**Inspect deeply. Fix conservatively. Verify honestly.**
You are a careful mechanic, not a renovation crew.

Never rewrite stable areas just because you can imagine a cleaner design.
Every change must be justified by a concrete bug, crash risk, packaging/runtime issue,
or meaningful usability defect.

---

## Mandatory operating rules

- Work in a single coherent pass for the user's requested scope.
- Preserve existing naming, style, and architecture where practical.
- Do not remove working features unless clearly broken or unsafe.
- Do not introduce new dependencies unless required to solve a real problem.
- Do not claim a fix is complete unless the saved file on disk actually contains the change.
- Do not rely on planned edits or editor-buffer assumptions — verify the real saved file when needed.
- If code was modified, invoke the `version-manager` skill for version bumping and changelog handling.
- If you cannot fully solve a problem, say exactly what remains and why.

---

## Workflow

Follow these six phases in order every time. Do not skip phases.

---

### Phase 1 — Project scan

Before changing anything, build a complete mental map of the project:

- Identify all files, entry points, and main class/function structure
- Identify all dependencies:
  - standard library
  - pip packages
  - optional imports / guarded dependencies
- Identify the GUI framework and UI structure (frames, windows, sidebar)
- Identify the worker/thread model in use (Thread, ThreadPoolExecutor, after())
- Identify all network/socket/subprocess usage
- Identify all file I/O operations and where persistent files are written
- Identify the build/packaging method (PyInstaller flags, spec file, build scripts, version metadata)
- Identify major features, tool frames, or modules
- Summarize the architecture briefly before fixing anything

Goal: understand how the app is actually wired before touching it.

---

### Phase 2 — Audit

Read the code carefully. Check every category below.
Mark each item: **OK** | **ISSUE** | **N/A**

---

#### 2A — Correctness and crashes

- [ ] Syntax errors (py_compile passes clean)
- [ ] Runtime exceptions from unhandled edge cases
- [ ] Missing `__name__ == "__main__"` guard
- [ ] Missing guards around optional dependency imports
  - Required pattern: `try: import X / X_AVAILABLE = True / except ImportError: X_AVAILABLE = False`
  - Every optional module MUST have this guard before any use
- [ ] Logic bugs, off-by-one errors, wrong operator precedence
- [ ] Unguarded dict/list access that could raise KeyError/IndexError
- [ ] Any bare `except:` clauses — replace with `except Exception:`
- [ ] Wrong assumptions about return values (None checks missing, etc.)
- [ ] Incomplete error handling in network / subprocess paths
- [ ] Thread worker functions missing `try/finally → ui_done()`:
  - A worker that crashes without calling ui_done() leaves Start permanently disabled
  - Every worker MUST have: `finally: self.after(0, self.ui_done)`

---

#### 2B — Thread safety and resource handling

- [ ] Widget state reads from worker threads
  - `StringVar.get()`, `Entry.get()`, `Combobox.get()` etc. MUST be called on main thread
  - Capture values BEFORE `thread.start()`, pass as arguments to worker
- [ ] Direct widget updates from worker threads
  - `widget.configure()`, `widget.insert()`, `widget.delete()` from threads → CRASH
  - Must go through `self.q()` / `self.after(0, callback)`
- [ ] Unbounded `after()` callback buildup
  - `after(0, lambda frame=...)` patterns in high-frequency paths can queue unbounded callbacks
  - Use a queue/poller pattern with a single recurring `after()` call instead
- [ ] Race conditions on shared mutable state
  - If two threads write to the same list/dict without a lock, flag it
- [ ] Socket leaks — sockets not closed on error paths
  - All sockets must be in `try/finally` or context manager
  - **Raw sockets: `SIO_RCVALL` MUST be turned OFF in `finally` block**
- [ ] Subprocess leaks — Popen handles not waited/closed
- [ ] File handles left open — use `with open(...)` everywhere
- [ ] `ThreadPoolExecutor` not shut down on stop
- [ ] `threading.Thread` missing `daemon=True`
  - Non-daemon threads prevent clean app exit
  - ALL worker threads must be `daemon=True`
- [ ] Duplicate finish/finalize calls (`ui_done` called twice)
- [ ] `after()` pollers continuing after frame is hidden
  - Use `if not self.winfo_ismapped(): return` guard in all long-running pollers
- [ ] Video/image resource leaks
  - `PhotoImage` objects garbage-collected if not referenced → blank images
  - PIL `Image` objects not closed after use
  - `cv2.VideoCapture` objects not released on stop/error

---

#### 2C — Portability and packaging

- [ ] All `open()` calls specify `encoding="utf-8"`
- [ ] All subprocess calls include `creationflags=SUBPROCESS_FLAGS`
  where `SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW` on Windows
- [ ] No hardcoded Unix paths (`/tmp/`, `~/`, forward-slash-only paths)
- [ ] All file path construction uses `pathlib.Path` (not string concatenation)
- [ ] **FROZEN APP PATH BUG — CRITICAL in PyInstaller onefile builds:**
  When packaged with PyInstaller `--onefile`, `__file__` does NOT point to
  the app directory. It points inside a temp extraction folder that is
  deleted on exit. Persistent files written relative to `__file__` are
  silently lost every restart.

  **Correct pattern — apply to ALL persistent file path constants:**
  ```python
  BASE_DIR = pathlib.Path(
      sys.executable if getattr(sys, "frozen", False) else __file__
  ).parent
  FAVORITES_FILE = BASE_DIR / "favorites.json"
  SETTINGS_FILE  = BASE_DIR / "settings.json"
  ```

- [ ] PyInstaller `--hidden-import` flags cover all guarded optional imports
- [ ] build.bat / build script VERSION variable matches `APP_VERSION`
- [ ] version_info.txt tuples and strings match `APP_VERSION`
- [ ] No missing `--collect-all` entries for packages with dynamic imports

---

#### 2D — UI, layout, and theming

- [ ] Fixed pixel widths on widgets in dense rows (clip at different DPI/font sizes)
- [ ] Parent containers missing `fill`/`expand` (pack) or `columnconfigure(weight=1)` (grid)
- [ ] Buttons or controls unreachable at minimum window size
- [ ] Panels with long content missing scrollable containers
- [ ] ttk / native widgets that do not match CustomTkinter dark theme
  - Look for `ttk.Treeview`, `ttk.Scrollbar` rendered with native Windows styling
  - Fix: `style.theme_use("default")` + `relief="flat"` + replace with `CTkScrollbar`
- [ ] Incorrect sidebar/content navigation sync
  - Programmatic navigation must update both the frame and the sidebar highlight
- [ ] Misleading labels, status text, or confidence wording
- [ ] Accordion sidebar (if present):
  - [ ] `select_no_callback()` auto-expands correct category
  - [ ] Active tool stays highlighted after category collapse/expand
  - [ ] All expand/collapse transitions work cleanly
  - [ ] No orphaned buttons outside any category
- [ ] Dashboard (if present):
  - [ ] `winfo_ismapped()` guard in auto-refresh prevents wasted CPU
  - [ ] All `psutil` calls are fast (no blocking I/O in main-thread `after()`)
  - [ ] Stat cards don't overflow at small window sizes
- [ ] `OutputText` widget: no direct widget calls from threads
- [ ] `CTkButton` text color not accidentally same as `fg_color` (invisible text)

---

#### 2E — Duplicate code and constants

- [ ] Duplicate helper functions doing the same thing
  (two ARP parsers, two ping wrappers, two IP validators)
- [ ] Duplicate entries in constant dicts/lists
  (same MAC OUI prefix defined twice, same port listed twice)
- [ ] Copy-pasted `_build()` / worker blocks that could share a helper
- [ ] Duplicate color constant definitions
- [ ] Sidebar: duplicate keys in `SIDEBAR_TOOLS` or `cls_map`
  (two entries with the same key string → one frame permanently unreachable)

---

#### 2F — Code quality (fix only if clearly problematic)

- [ ] `TODO` / `FIXME` comments referring to already-fixed issues
- [ ] Commented-out code blocks no longer needed
- [ ] Class docstrings missing or wildly inaccurate
- [ ] `APP_NAME` / `APP_VERSION` / `APP_AUTHOR` used inconsistently
  (mixed with hardcoded strings in window title, About dialog, etc.)
- [ ] Dead imports at top of file

---

### Phase 3 — Prioritize findings

Classify every finding:

| Severity | Meaning | Examples |
|----------|---------|---------|
| **Critical** | Crash, data loss, severe broken behavior | Unhandled exception, unsafe UI-thread access, broken startup, frozen path bug losing user data, infinite queue buildup |
| **High** | Broken feature or likely runtime failure | Missing `daemon=True`, missing `try/finally` in worker, race condition, resource leak, PyInstaller missing import, `SIO_RCVALL` not cleaned up |
| **Medium** | Degraded UX, fragile portability, misleading UI | ttk theme mismatch, wrong sidebar highlight, missing `encoding=`, missing `CREATE_NO_WINDOW`, missing `winfo_ismapped` guard, video resource leak |
| **Low** | Small cleanup with real value | Misleading constant, stale comment, harmless dead code, dead import |

Fix order: Critical → High → Medium → Low
Do not spend the user's budget on low-priority cleanup if high-value bugs remain.

---

### Phase 4 — Apply fixes

Rules:
- **One logical fix per edit** — don't bundle unrelated changes
- **Minimal change** — fewest lines that correctly fix the issue
- **Preserve naming, style, architecture** — match existing conventions
- **No new dependencies** unless essential to fix a real bug
- **No feature removal** — only fix what's broken
- **No speculative refactors** — if it works and isn't causing a problem, leave it
- **Explain every fix:** what was wrong, why it matters, what changed
- **If code changes are made, invoke `version-manager`**

---

#### Standard fixes — apply confidently when found:

**Frozen app path fix (CRITICAL):**
```python
# WRONG — broken in PyInstaller onefile:
FAVORITES_FILE = pathlib.Path(__file__).parent / "favorites.json"

# CORRECT — works in both dev and frozen:
BASE_DIR = pathlib.Path(
    sys.executable if getattr(sys, "frozen", False) else __file__
).parent
FAVORITES_FILE = BASE_DIR / "favorites.json"
SETTINGS_FILE  = BASE_DIR / "settings.json"
```

**Worker thread safety (HIGH):**
```python
# WRONG — leaves Start button disabled if worker crashes:
def _worker(self, target):
    # work that might raise
    self.after(0, self.ui_done)

# CORRECT — always restores UI state:
def _worker(self, target):
    try:
        # work
    except Exception as e:
        self.q(f"Error: {e}", "error")
    finally:
        self.after(0, self.ui_done)
```

**Daemon threads (HIGH):**
```python
# WRONG:
t = threading.Thread(target=self._worker, args=(val,))
t.start()

# CORRECT:
t = threading.Thread(target=self._worker, args=(val,), daemon=True)
t.start()
```

**Capture widget values before threading (HIGH):**
```python
# WRONG — reads widget from worker thread:
def _start(self):
    t = threading.Thread(target=self._worker)
    t.start()
def _worker(self):
    target = self._entry.get()  # ← UNSAFE: widget read from thread

# CORRECT — captured on main thread:
def _start(self):
    target = self._entry.get()  # ← safe: main thread
    t = threading.Thread(target=self._worker, args=(target,), daemon=True)
    t.start()
def _worker(self, target):
    # use target directly
```

**Raw socket cleanup (HIGH — LiveCaptureFrame / SIO_RCVALL):**
```python
# WRONG — SIO_RCVALL left ON if exception occurs:
sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
while not self.stop_event.is_set():
    data = sock.recv(65535)
sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
sock.close()

# CORRECT — always cleaned up:
sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
try:
    while not self.stop_event.is_set():
        data = sock.recv(65535)
finally:
    try:
        sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        sock.close()
    except Exception:
        pass
```

**Polling guard for hidden frames (MEDIUM):**
```python
def _refresh_stats(self):
    if not self.winfo_ismapped():
        self.after(2000, self._refresh_stats)
        return
    # ... do the work ...
    self.after(2000, self._refresh_stats)
```

**ttk theme fix (MEDIUM):**
```python
# Fix native Windows look in Treeview:
style = tk.ttk.Style()
style.theme_use("default")
style.configure("Treeview.Heading", relief="flat", borderwidth=0)
# Replace ttk.Scrollbar with CTkScrollbar for visual consistency
```

**cv2 VideoCapture cleanup (MEDIUM):**
```python
# Ensure capture is always released:
cap = cv2.VideoCapture(url)
try:
    while self.running:
        ret, frame = cap.read()
        # ...
finally:
    cap.release()
```

---

### Phase 5 — Verify

After applying all fixes:

- `python -m py_compile nettools.py` — must pass, zero errors
- All imports resolve without `ModuleNotFoundError`
- Packaging assumptions still hold (hidden imports, spec file, build.bat)
- No new dependency gaps introduced
- UI layout changes consistent (expand/fill/sticky)
- Version strings consistent across all locations (if version was bumped)
- Zero duplicate keys in sidebar/navigation structures
- No direct widget calls from worker threads remain
- Queue/poller flow is coherent
- Stop/start cleanup is complete

---

### Phase 6 — Report

```
## Audit Summary
Architecture overview. Total lines. Classes identified. Scope of audit.

## Findings by Severity
### Critical
### High
### Medium
### Low

## Applied Changes
For each fix:
  File: [filename] (approximate line range)
  Issue: what was wrong
  Fix: what was changed
  Why: concrete risk this prevents

## Verification Results
py_compile:           PASS / FAIL
Version consistency:  confirmed / issues found
Duplicate key check:  clean / issues found
Thread safety check:  clean / issues found
Other checks:         [list]

## Remaining Risks / Manual Test Suggestions
[list specific manual tests needed]
```

Report honestly. No filler. No claiming success without evidence.

---

## Quick reference — NetTools Pro specific patterns

Check each of these explicitly when auditing NetTools Pro.

### FROZEN PATH — CRITICAL
```python
# WRONG in PyInstaller onefile — __file__ points to temp dir, deleted on exit:
FAVORITES_FILE = pathlib.Path(__file__).parent / "favorites.json"

# CORRECT:
BASE_DIR = pathlib.Path(
    sys.executable if getattr(sys, "frozen", False) else __file__
).parent
FAVORITES_FILE = BASE_DIR / "favorites.json"
SETTINGS_FILE  = BASE_DIR / "settings.json"
```

### WORKER THREAD COMPLETION — HIGH
```python
def _worker(self, ...):
    try:
        ...
    except Exception as e:
        self.q(f"Error: {e}", "error")
    finally:
        self.after(0, self.ui_done)
```

### DAEMON THREADS — HIGH
All `threading.Thread()` calls must include `daemon=True`.
Non-daemon threads keep the process alive after window close.

### SIO_RCVALL CLEANUP — HIGH (LiveCaptureFrame)
The `SIO_RCVALL` ioctl puts the network adapter in promiscuous mode.
It MUST be turned off in a `finally` block, not just at normal exit.
Failure leaves the adapter in promiscuous mode system-wide after a crash.

### WIDGET VALUES IN THREADS — HIGH
All `CTkEntry.get()`, `CTkCombobox.get()`, `StringVar.get()` calls
must happen on the main thread before the worker is spawned.

### CV2 CAPTURE RELEASE — MEDIUM (StreamViewerFrame)
`cv2.VideoCapture` objects must be released in a `finally` block.
Unreleased captures hold the RTSP connection open indefinitely.

### POLLING IN HIDDEN FRAMES — MEDIUM
Frames using `self.after()` for continuous polling must guard with:
`if not self.winfo_ismapped(): ...`
Affects: DashboardFrame, BandwidthFrame, ConnectionsFrame, InterfacesFrame.

### TTK THEME MISMATCH — MEDIUM
Any `ttk.Treeview` or `ttk.Scrollbar` without explicit theme override
will render with native Windows styling, breaking the dark theme.
Fix: `style.theme_use("default")` + `CTkScrollbar` replacement.

### SIDEBAR DUPLICATE KEYS — HIGH
If `SIDEBAR_TOOLS` or `cls_map` contains duplicate key strings,
one frame will always be permanently unreachable.
Check explicitly after any sidebar restructuring.

### PHOTOIMAGE REFERENCE — MEDIUM
`PhotoImage` objects must be kept alive via an instance variable or
they are garbage-collected and render as blank.
Pattern: `self._img = ImageTk.PhotoImage(...)` (not a local variable).
