"""
system_backend.py — Platform backend for SystemToolsFrame.

Abstract layer between SystemToolsFrame and OS-specific tools
(PowerShell/SFC/DISM on Windows, future Linux equivalents).

Generator-based streaming methods yield (line, tag) tuples.
The frame consumes the generator and calls self.q(line, tag) for each item.
"""

import os
import re
import shutil
import socket
import struct
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Event
from typing import Iterator, Tuple

from platform_utils import SUBPROCESS_FLAGS, IS_WINDOWS, IS_LINUX

try:
    import fcntl
except ImportError:  # pragma: no cover - not available on Windows
    fcntl = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

# (line_text, tag) where tag ∈ {"header", "normal", "info", "success", "warning", "error", "dim"}
OutputLine = Tuple[str, str]

# ── Module-level constants (copied verbatim from nettools.py) ─────────────────

# Inline PowerShell script for system diagnostics.
# Mirrors the sections in SkipperToolkit.ps1 Invoke-PCDiagnostikk:
# System, CPU/RAM, Disk, GPU, Network, Running Services, Windows Update,
# Autostart, Installed Programs, and last 30 critical/error events (7 days).
_PS_DIAGNOSTICS = r"""
$ErrorActionPreference = 'SilentlyContinue'
Write-Output ("Diagnostics started: {0}  Machine: {1}  User: {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $env:COMPUTERNAME, $env:USERNAME)
Write-Output ""

Write-Output "=== SYSTEM ==="
try {
    $cs   = Get-CimInstance Win32_ComputerSystem
    $os   = Get-CimInstance Win32_OperatingSystem
    $bios = Get-CimInstance Win32_BIOS
    Write-Output ("  Manufacturer : {0}" -f $cs.Manufacturer)
    Write-Output ("  Model        : {0}" -f $cs.Model)
    Write-Output ("  OS           : {0}" -f $os.Caption)
    Write-Output ("  Version      : {0}" -f $os.Version)
    Write-Output ("  Build        : {0}" -f $os.BuildNumber)
    Write-Output ("  BIOS         : {0}" -f $bios.SMBIOSBIOSVersion)
} catch { Write-Output "  (Error reading system info)" }

Write-Output ""
Write-Output "=== CPU / RAM ==="
try {
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $ramGB = [math]::Round((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1GB, 2)
    Write-Output ("  CPU    : {0}" -f $cpu.Name)
    Write-Output ("  Cores  : {0}  Logical: {1}" -f $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors)
    Write-Output ("  RAM    : {0} GB installed" -f $ramGB)
} catch { Write-Output "  (Error reading CPU/RAM)" }

Write-Output ""
Write-Output "=== DISK ==="
try {
    foreach ($d in (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -gt 0 })) {
        $tot  = [math]::Round(($d.Used + $d.Free) / 1GB, 2)
        $free = [math]::Round($d.Free / 1GB, 2)
        $used = [math]::Round($d.Used / 1GB, 2)
        $pct  = if ($tot -gt 0) { [math]::Round(($free / $tot) * 100, 1) } else { 0 }
        Write-Output ("  {0}: Total {1} GB | Used {2} GB | Free {3} GB ({4}% free)" -f $d.Name, $tot, $used, $free, $pct)
    }
} catch { Write-Output "  (Error reading disk)" }

Write-Output ""
Write-Output "=== GPU ==="
try {
    foreach ($g in (Get-CimInstance Win32_VideoController)) {
        Write-Output ("  GPU    : {0}" -f $g.Caption)
        Write-Output ("  Driver : {0}  Status: {1}" -f $g.DriverVersion, $g.Status)
    }
} catch { Write-Output "  (Error reading GPU)" }

Write-Output ""
Write-Output "=== NETWORK ADAPTERS ==="
try {
    foreach ($n in (Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled })) {
        Write-Output ("  Adapter : {0}" -f $n.Description)
        Write-Output ("  IP      : {0}" -f ($n.IPAddress -join ', '))
        Write-Output ("  Gateway : {0}" -f ($n.DefaultIPGateway -join ', '))
        Write-Output ("  DNS     : {0}" -f ($n.DNSServerSearchOrder -join ', '))
        Write-Output ""
    }
} catch { Write-Output "  (Error reading network)" }

Write-Output "=== RUNNING SERVICES ==="
try {
    Get-Service | Where-Object { $_.Status -eq 'Running' } | Sort-Object DisplayName |
        ForEach-Object { Write-Output ("  {0} ({1})" -f $_.DisplayName, $_.Name) }
} catch { Write-Output "  (Error reading services)" }

Write-Output ""
Write-Output "=== WINDOWS UPDATE — LAST 10 HOTFIXES ==="
try {
    Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 |
        ForEach-Object {
            $d = if ($_.InstalledOn) { $_.InstalledOn.ToString('yyyy-MM-dd') } else { 'Unknown' }
            Write-Output ("  {0} | {1} | {2}" -f $d, $_.HotFixID, $_.Description)
        }
} catch { Write-Output "  (Error reading hotfixes)" }

Write-Output ""
Write-Output "=== AUTOSTART ==="
try {
    foreach ($regPath in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
                            'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run')) {
        $props = Get-ItemProperty $regPath -ErrorAction SilentlyContinue
        if ($props) {
            $props.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } |
                ForEach-Object { Write-Output ("  {0} | {1}" -f $_.Name, $regPath) }
        }
    }
} catch { Write-Output "  (Error reading autostart)" }

Write-Output ""
Write-Output "=== INSTALLED PROGRAMS (first 100, alphabetical) ==="
try {
    $regPaths = @('HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
                  'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
                  'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*')
    Get-ItemProperty $regPaths -ErrorAction SilentlyContinue |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_.DisplayName) } |
        Sort-Object DisplayName -Unique | Select-Object -First 100 |
        ForEach-Object { Write-Output ("  {0} | {1} | {2}" -f $_.DisplayName, $_.DisplayVersion, $_.Publisher) }
} catch { Write-Output "  (Error reading installed programs)" }

Write-Output ""
Write-Output "=== CRITICAL/ERROR EVENTS — LAST 7 DAYS (max 30) ==="
try {
    Get-WinEvent -FilterHashtable @{ LogName='System'; Level=1,2;
        StartTime=(Get-Date).AddDays(-7) } -MaxEvents 30 -ErrorAction Stop |
    ForEach-Object {
        Write-Output ("  [{0}] ID {1} | {2}" -f $_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'), $_.Id, $_.ProviderName)
        Write-Output ("        {0}" -f (($_.Message -replace '\r|\n',' ' -replace '\s+',' ').Substring(0, [math]::Min(120,$_.Message.Length))))
    }
} catch { Write-Output "  (No events found or access denied)" }

Write-Output ""
Write-Output "=== DONE ==="
"""

# Result keywords for SFC output parsing
_SFC_RESULTS = [
    ("did not find any integrity violations", "success",
     "No integrity violations found."),
    ("successfully repaired",                "success",
     "Violations found — repaired successfully."),
    ("found corrupt files and was unable",   "error",
     "Corrupt files found — repair FAILED. Run DISM first, then re-run SFC."),
]


# ── Abstract base class ───────────────────────────────────────────────────────

class SystemBackend(ABC):
    """Abstract platform backend for system tools.

    Generator-based methods yield output while the process is running.
    The frame consumes the generator and calls self.q(line, tag) for each line.
    """

    # ── Capability reporting ──────────────────────────────────────────────────

    @abstractmethod
    def available_tools(self) -> set:
        """Return a set of tool names supported on this platform.
        Names: 'diagnostics', 'sfc', 'dism', 'backup', 'restore', 'debloat', 'arpscan'."""

    @abstractmethod
    def admin_required_for(self, tool: str) -> bool:
        """True if the tool requires admin/root privileges to work."""

    # ── Streaming operations (generators) ────────────────────────────────────

    @abstractmethod
    def run_diagnostics(self, stop_event: Event) -> Iterator[OutputLine]:
        """Run system diagnostics. Yield (line, tag) per output line.
        Check stop_event.is_set() between lines and terminate the process on abort."""

    @abstractmethod
    def run_sfc(self, stop_event: Event) -> Iterator[OutputLine]:
        """Run an SFC scan. Yield (line, tag). The final yield should be
        a result line with tag 'success'/'error'/'warning' based on the output."""

    @abstractmethod
    def run_dism(self, stop_event: Event) -> Iterator[OutputLine]:
        """Run DISM restore-health. Yield (line, tag)."""

    # ── Service primitives (synchronous) ─────────────────────────────────────

    @abstractmethod
    def export_services(self, path: str) -> None:
        """Export all services to a JSON file. Raise IOError on failure."""

    @abstractmethod
    def set_service_startup(self, name: str, startup_type: str, dry: bool) -> tuple:
        """Set the startup type for one service.
        Returns (success, display_line).
        dry=True returns a preview line without running the command."""

    @abstractmethod
    def run_arp_scan(self, stop_event: Event, **kwargs) -> Iterator[OutputLine]:
        """Run arp-scan (supported on Linux only).
        Yield (line, tag) tuples where tag='data' means a JSON-serialized device."""


# ── Windows implementation ────────────────────────────────────────────────────

class WindowsBackend(SystemBackend):
    """Full Windows implementation based on PowerShell, SFC, and DISM."""

    def available_tools(self) -> set:
        return {"diagnostics", "sfc", "dism", "backup", "restore", "debloat"}

    def admin_required_for(self, tool: str) -> bool:
        return {
            "diagnostics": False,
            "sfc": True,
            "dism": True,
            "backup": False,
            "restore": True,
            "debloat": True,
        }.get(tool, True)

    def run_diagnostics(self, stop_event: Event) -> Iterator[OutputLine]:
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_DIAGNOSTICS],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=SUBPROCESS_FLAGS)
        for line in proc.stdout:
            if stop_event.is_set():
                proc.terminate()
                break
            line = line.rstrip()
            tag = "header" if line.startswith("===") else "normal"
            yield (line, tag)
        proc.wait()
        yield ("Diagnostics complete.", "success")

    def run_sfc(self, stop_event: Event) -> Iterator[OutputLine]:
        proc = subprocess.Popen(
            ["sfc", "/scannow"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=SUBPROCESS_FLAGS)
        lines = []
        for line in proc.stdout:
            if stop_event.is_set():
                proc.terminate()
                break
            stripped = line.rstrip()
            if stripped:
                yield (stripped, "normal")
                lines.append(stripped.lower())
        proc.wait()
        # Parse result from the last 15 output lines
        result_tag, result_msg = "info", "SFC scan complete."
        for needle, tag, msg in _SFC_RESULTS:
            if any(needle in l for l in lines[-15:]):
                result_tag, result_msg = tag, msg
                break
        yield (result_msg, result_tag)

    def run_dism(self, stop_event: Event) -> Iterator[OutputLine]:
        proc = subprocess.Popen(
            ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=SUBPROCESS_FLAGS)
        for line in proc.stdout:
            if stop_event.is_set():
                proc.terminate()
                break
            stripped = line.rstrip()
            if stripped:
                # Highlight percentage progress lines
                tag = "info" if re.search(r'\d+\.\d+%', stripped) else "normal"
                yield (stripped, tag)
        proc.wait()
        yield ("DISM repair complete.", "success")

    def export_services(self, path: str) -> None:
        ps = (
            "Get-Service | ForEach-Object { [PSCustomObject]@{ "
            "Name=$_.Name; Status=$_.Status.ToString(); "
            "StartType=$_.StartType.ToString() } } "
            f"| ConvertTo-Json -Depth 2 "
            f"| Set-Content -Path '{path}' -Encoding UTF8"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        if res.returncode != 0:
            raise IOError(res.stderr)

    def set_service_startup(self, name: str, startup_type: str, dry: bool) -> tuple:
        if dry:
            return True, f"WOULD: Set-Service '{name}' -StartupType {startup_type}"
        ps = (f"try {{ Set-Service -Name '{name}' -StartupType {startup_type} "
              f"-ErrorAction Stop; Write-Output 'OK: {name} -> {startup_type}' }} "
              f"catch {{ Write-Output ('FAIL: {name}: ' + $_.Exception.Message) }}")
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        line = res.stdout.strip() or res.stderr.strip()
        return line.startswith("OK:"), line

    def run_arp_scan(self, stop_event: Event, **kwargs) -> Iterator[OutputLine]:
        """ARP Scan is Linux-only. The frontend should not call this on Windows."""
        raise NotImplementedError("ARP Scan is not available on Windows")
        yield  # pragma: no cover - needed to make this a generator


# ── Linux-stub ────────────────────────────────────────────────────────────────

class LinuxBackend(SystemBackend):
    """Read-only Linux diagnostics backend for SystemToolsFrame."""

    _SIOCGIFADDR = 0x8915

    @staticmethod
    def _read_os_name() -> str:
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"') or "Linux"
        except OSError:
            pass
        return "Linux"

    @staticmethod
    def _linux_package_manager() -> str:
        if shutil.which("dnf"):
            return "dnf"
        if shutil.which("apt"):
            return "apt"
        if shutil.which("apt-get"):
            return "apt"
        return "unknown"

    @staticmethod
    def _arp_scan_capability_fix_lines(pkg_manager: str | None = None) -> list[OutputLine]:
        manager = pkg_manager or LinuxBackend._linux_package_manager()
        if manager == "dnf":
            return [
                ("Run this command and try again:", "warning"),
                ('sudo dnf install -y libcap && sudo setcap cap_net_raw+p "$(command -v arp-scan)"', "info"),
            ]
        if manager == "apt":
            return [
                ("Run this command and try again:", "warning"),
                ('sudo apt install -y libcap2-bin && sudo setcap cap_net_raw+p "$(command -v arp-scan)"', "info"),
            ]
        return [
            ("Run one of these commands and try again:", "warning"),
            ('Fedora/RHEL: sudo dnf install -y libcap && sudo setcap cap_net_raw+p "$(command -v arp-scan)"', "info"),
            ('Ubuntu/Debian: sudo apt install -y libcap2-bin && sudo setcap cap_net_raw+p "$(command -v arp-scan)"', "info"),
        ]

    @staticmethod
    def _run_command(cmd: list[str], timeout: float = 5.0) -> tuple[str | None, str | None]:
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=SUBPROCESS_FLAGS,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return None, "timed out"
        except OSError as e:
            return None, str(e)
        if res.returncode != 0:
            detail = res.stderr.strip() or res.stdout.strip() or f"exit {res.returncode}"
            return None, detail
        return res.stdout.strip(), None

    @staticmethod
    def _abort(stop_event: Event) -> tuple[bool, OutputLine | None]:
        if stop_event.is_set():
            return True, ("Diagnostics aborted.", "error")
        return False, None

    @staticmethod
    def _format_bytes(value: int | float | None) -> str:
        if value is None:
            return "n/a"
        size = float(value)
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if abs(size) < 1024.0 or unit == "TiB":
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TiB"

    @staticmethod
    def _read_first_line(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.readline().strip()
        except OSError:
            return ""

    @staticmethod
    def _read_int_file(path: Path) -> int | None:
        try:
            return int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    @staticmethod
    def _battery_health_percent(battery_dir: Path) -> float | None:
        now_full = None
        design_full = None

        for current_name, design_name in (
            ("charge_full", "charge_full_design"),
            ("energy_full", "energy_full_design"),
        ):
            now_full = LinuxBackend._read_int_file(battery_dir / current_name)
            design_full = LinuxBackend._read_int_file(battery_dir / design_name)
            if now_full is not None and design_full:
                break

        if now_full is None or not design_full or design_full <= 0:
            return None
        return max(min((now_full / design_full) * 100.0, 100.0), 0.0)

    @staticmethod
    def _battery_lines() -> list[OutputLine]:
        battery_dirs = sorted(
            [
                path for path in Path("/sys/class/power_supply").glob("BAT*")
                if path.is_dir()
            ],
            key=lambda path: path.name,
        )

        if not battery_dirs and PSUTIL_AVAILABLE:
            try:
                battery = psutil.sensors_battery()
                if battery is not None:
                    status = "Charging" if battery.power_plugged else "Discharging"
                    if battery.percent is not None and battery.power_plugged and battery.percent >= 99:
                        status = "Full"
                    return [
                        (f"Status: {status}", "info"),
                        (f"Capacity: {battery.percent:.0f}%", "info"),
                        ("Health: unavailable", "dim"),
                    ]
            except Exception:
                pass

        if not battery_dirs:
            return [("Battery telemetry unavailable.", "dim")]

        lines: list[OutputLine] = []
        for battery_dir in battery_dirs:
            status = LinuxBackend._read_first_line(str(battery_dir / "status")) or "Unknown"
            capacity = LinuxBackend._read_int_file(battery_dir / "capacity")
            health = LinuxBackend._battery_health_percent(battery_dir)
            cycle_count = LinuxBackend._read_int_file(battery_dir / "cycle_count")

            prefix = f"{battery_dir.name} " if len(battery_dirs) > 1 else ""
            lines.append((f"{prefix}Status: {status}", "info"))
            if capacity is not None:
                lines.append((f"{prefix}Capacity: {capacity}%", "info"))
            else:
                lines.append((f"{prefix}Capacity: unavailable", "dim"))

            if health is not None:
                lines.append((f"{prefix}Health: {health:.1f}% of design capacity", "info"))
            else:
                lines.append((f"{prefix}Health: unavailable", "dim"))

            if cycle_count is not None:
                lines.append((f"{prefix}Cycle count: {cycle_count}", "info"))

        return lines

    @staticmethod
    def _read_load_average() -> str:
        try:
            one, five, fifteen = os.getloadavg()
            return f"{one:.2f} {five:.2f} {fifteen:.2f}"
        except (OSError, AttributeError):
            line = LinuxBackend._read_first_line("/proc/loadavg")
            return " ".join(line.split()[:3]) if line else ""

    @staticmethod
    def _parse_key_value_output(output: str) -> dict[str, str]:
        values: dict[str, str] = {}
        for line in output.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
        return values

    @staticmethod
    def _cpu_snapshot() -> dict[str, str | int | float | None]:
        model = ""
        logical = None
        physical = None
        usage = None

        output, error = LinuxBackend._run_command(["lscpu"])
        if output:
            values = LinuxBackend._parse_key_value_output(output)
            model = values.get("Model name", "")
            try:
                logical = int(values.get("CPU(s)", "") or 0) or None
            except ValueError:
                logical = None
            sockets = values.get("Socket(s)", "1")
            cores_per_socket = values.get("Core(s) per socket", "")
            try:
                sockets_i = int(sockets or 1)
                cores_i = int(cores_per_socket or 0)
                physical = sockets_i * cores_i if cores_i else None
            except ValueError:
                physical = None
        elif error:
            model = ""

        if not model:
            try:
                with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("model name"):
                            model = line.split(":", 1)[1].strip()
                            break
            except OSError:
                pass

        if PSUTIL_AVAILABLE:
            try:
                logical = logical or psutil.cpu_count(logical=True)
                physical = physical or psutil.cpu_count(logical=False)
                usage = psutil.cpu_percent(interval=0.15)
            except Exception:
                pass

        return {
            "model": model or "Unknown CPU",
            "logical": logical,
            "physical": physical,
            "load": LinuxBackend._read_load_average(),
            "usage": usage,
        }

    @staticmethod
    def _memory_lines() -> list[OutputLine]:
        if PSUTIL_AVAILABLE:
            try:
                vm = psutil.virtual_memory()
                swap = psutil.swap_memory()
                return [
                    (f"Total: {LinuxBackend._format_bytes(vm.total)}", "info"),
                    (
                        f"Used: {LinuxBackend._format_bytes(vm.used)} ({vm.percent:.1f}%)"
                        f"  Available: {LinuxBackend._format_bytes(vm.available)}",
                        "info",
                    ),
                    (
                        f"Swap: {LinuxBackend._format_bytes(swap.used)} / "
                        f"{LinuxBackend._format_bytes(swap.total)} ({swap.percent:.1f}%)",
                        "info",
                    ),
                ]
            except Exception as e:
                return [(f"psutil memory snapshot failed ({e})", "warning")]

        output, error = LinuxBackend._run_command(["free", "-h"])
        if error:
            return [(f"Command failed: free -h ({error})", "error")]
        return [(line.strip(), "info") for line in output.splitlines() if line.strip()]

    @staticmethod
    def _disk_lines() -> list[OutputLine]:
        lines: list[OutputLine] = []
        shown_mounts: set[str] = set()

        if PSUTIL_AVAILABLE:
            try:
                partitions = psutil.disk_partitions(all=False)
                root_part = next((p for p in partitions if p.mountpoint == "/"), None)
                if root_part:
                    usage = psutil.disk_usage(root_part.mountpoint)
                    lines.append(
                        (
                            f"/ ({root_part.fstype or 'unknown'}): "
                            f"{LinuxBackend._format_bytes(usage.used)} / "
                            f"{LinuxBackend._format_bytes(usage.total)} used "
                            f"({usage.percent:.1f}%)",
                            "info",
                        )
                    )
                    shown_mounts.add("/")

                for part in partitions:
                    if part.mountpoint in shown_mounts:
                        continue
                    if part.mountpoint.startswith("/snap"):
                        continue
                    if part.mountpoint not in {"/home", "/boot", "/boot/efi", "/tmp"}:
                        continue
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                    except Exception:
                        continue
                    lines.append(
                        (
                            f"{part.mountpoint} ({part.fstype or 'unknown'}): "
                            f"{LinuxBackend._format_bytes(usage.used)} / "
                            f"{LinuxBackend._format_bytes(usage.total)} used "
                            f"({usage.percent:.1f}%)",
                            "info",
                        )
                    )
                    shown_mounts.add(part.mountpoint)
            except Exception as e:
                lines.append((f"psutil disk snapshot failed ({e})", "warning"))

        if not lines:
            output, error = LinuxBackend._run_command(["df", "-h", "/"])
            if error:
                lines.append((f"Command failed: df -h / ({error})", "error"))
            else:
                for line in output.splitlines():
                    if line.strip():
                        lines.append((line.strip(), "info"))
            fstype, fs_error = LinuxBackend._run_command(["findmnt", "-no", "FSTYPE", "/"])
            if fstype:
                lines.append((f"Root filesystem type: {fstype}", "info"))
            elif fs_error:
                lines.append((f"Root filesystem type unavailable ({fs_error})", "dim"))
        return lines

    @staticmethod
    def _default_gateway() -> tuple[str, str]:
        try:
            with open("/proc/net/route", "r", encoding="utf-8") as f:
                next(f, None)
                for line in f:
                    fields = line.strip().split()
                    if len(fields) < 4:
                        continue
                    if fields[1] != "00000000":
                        continue
                    gateway = socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))
                    return fields[0], gateway
        except (OSError, ValueError, struct.error):
            pass
        return "", ""

    @staticmethod
    def _interface_ipv4(name: str) -> list[str]:
        ipv4s: list[str] = []
        if PSUTIL_AVAILABLE:
            try:
                addrs = psutil.net_if_addrs()
                for addr in addrs.get(name, []):
                    family = getattr(addr, "family", None)
                    if family == socket.AF_INET and getattr(addr, "address", ""):
                        ipv4s.append(addr.address)
                if ipv4s:
                    return ipv4s
            except Exception:
                pass

        if fcntl is None:
            return ipv4s

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ifreq = struct.pack("256s", name[:15].encode("utf-8"))
            result = fcntl.ioctl(sock.fileno(), LinuxBackend._SIOCGIFADDR, ifreq)
            ipv4s.append(socket.inet_ntoa(result[20:24]))
        except Exception:
            pass
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        return ipv4s

    @staticmethod
    def _network_io_snapshot() -> tuple[int, int] | None:
        if PSUTIL_AVAILABLE:
            try:
                totals = psutil.net_io_counters(pernic=True)
                rx_total = 0
                tx_total = 0
                for iface_name, counters in totals.items():
                    if iface_name == "lo":
                        continue
                    rx_total += int(getattr(counters, "bytes_recv", 0) or 0)
                    tx_total += int(getattr(counters, "bytes_sent", 0) or 0)
                return rx_total, tx_total
            except Exception:
                pass

        try:
            rx_total = 0
            tx_total = 0
            with open("/proc/net/dev", "r", encoding="utf-8") as f:
                for line in f.readlines()[2:]:
                    if ":" not in line:
                        continue
                    iface_name, raw_values = line.split(":", 1)
                    if iface_name.strip() == "lo":
                        continue
                    fields = raw_values.split()
                    if len(fields) < 9:
                        continue
                    rx_total += int(fields[0])
                    tx_total += int(fields[8])
            return rx_total, tx_total
        except (OSError, ValueError):
            return None

    @staticmethod
    def _format_mb_per_second(bytes_per_second: float | None) -> str:
        if bytes_per_second is None:
            return "n/a"
        return f"{bytes_per_second / (1024 ** 2):.2f} MB/s"

    @staticmethod
    def _sleep_with_abort(stop_event: Event, duration_s: float, slice_s: float = 0.1) -> bool:
        deadline = time.monotonic() + duration_s
        while True:
            if stop_event.is_set():
                return False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            time.sleep(min(slice_s, remaining))

    @staticmethod
    def _network_speed_lines(stop_event: Event, sample_seconds: float = 1.0) -> list[OutputLine]:
        first = LinuxBackend._network_io_snapshot()
        if first is None:
            return [("Live throughput unavailable.", "dim")]

        started = time.monotonic()
        if not LinuxBackend._sleep_with_abort(stop_event, sample_seconds):
            raise InterruptedError

        second = LinuxBackend._network_io_snapshot()
        elapsed = max(time.monotonic() - started, 0.001)
        if second is None:
            return [("Live throughput unavailable.", "dim")]

        rx_rate = max(second[0] - first[0], 0) / elapsed
        tx_rate = max(second[1] - first[1], 0) / elapsed
        return [
            (
                "Live throughput (all non-loopback, 1s sample): "
                f"Download {LinuxBackend._format_mb_per_second(rx_rate)}  "
                f"Upload {LinuxBackend._format_mb_per_second(tx_rate)}",
                "info",
            )
        ]

    @staticmethod
    def _network_lines(stop_event: Event) -> list[OutputLine]:
        lines: list[OutputLine] = []
        try:
            interfaces = sorted(Path("/sys/class/net").iterdir(), key=lambda p: p.name)
        except OSError as e:
            return [(f"Interface listing unavailable ({e})", "warning")]

        active_count = 0
        for iface in interfaces:
            if iface.name == "lo":
                continue
            state = LinuxBackend._read_first_line(str(iface / "operstate")) or "unknown"
            ipv4s = LinuxBackend._interface_ipv4(iface.name)
            if state == "up" or ipv4s:
                active_count += 1
                lines.append(
                    (
                        f"{iface.name}: state={state}"
                        f"{'  IPv4=' + ', '.join(ipv4s) if ipv4s else '  IPv4=unavailable'}",
                        "info",
                    )
                )

        if active_count == 0:
            lines.append(("No active non-loopback interfaces detected.", "warning"))

        gw_iface, gateway = LinuxBackend._default_gateway()
        if gateway:
            lines.append((f"Default gateway: {gateway} via {gw_iface}", "info"))
        else:
            lines.append(("Default gateway unavailable.", "dim"))

        established = 0
        if PSUTIL_AVAILABLE:
            try:
                conns = psutil.net_connections(kind="inet")
                established = sum(1 for c in conns if getattr(c, "status", "") == "ESTABLISHED")
            except Exception:
                established = 0
        if not established:
            for path in ("/proc/net/tcp", "/proc/net/tcp6"):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        next(f, None)
                        established += sum(1 for line in f if line.split()[3] == "01")
                except Exception:
                    pass
        lines.append((f"Established connections: {established}", "info"))
        lines.extend(LinuxBackend._network_speed_lines(stop_event))
        return lines

    @staticmethod
    def _process_lines() -> list[OutputLine]:
        if not PSUTIL_AVAILABLE:
            return [("psutil unavailable — process snapshot skipped.", "dim")]

        try:
            proc_count = len(psutil.pids())
            processes = []
            for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
                try:
                    proc.cpu_percent(None)
                    processes.append(proc)
                except Exception:
                    continue
            time.sleep(0.1)

            rows = []
            for proc in processes:
                try:
                    info = proc.info
                    rows.append({
                        "pid": info.get("pid"),
                        "name": info.get("name") or "?",
                        "memory_percent": float(info.get("memory_percent") or 0.0),
                        "cpu_percent": proc.cpu_percent(None),
                    })
                except Exception:
                    continue

            rows.sort(key=lambda item: (item["cpu_percent"], item["memory_percent"]), reverse=True)
            if not rows:
                rows.sort(key=lambda item: item["memory_percent"], reverse=True)

            lines: list[OutputLine] = [(f"Total processes: {proc_count}", "info")]
            for item in rows[:5]:
                lines.append(
                    (
                        f"PID {item['pid']:<6} {item['name'][:24]:<24} "
                        f"CPU {item['cpu_percent']:>5.1f}%  MEM {item['memory_percent']:>5.1f}%",
                        "info",
                    )
                )
            return lines
        except Exception as e:
            return [(f"Process snapshot failed ({e})", "warning")]

    @staticmethod
    def _temperature_lines() -> list[OutputLine]:
        if PSUTIL_AVAILABLE:
            try:
                temps = psutil.sensors_temperatures(fahrenheit=False)
                lines: list[OutputLine] = []
                for sensor_name, entries in temps.items():
                    if not entries:
                        continue
                    for entry in entries[:2]:
                        label = entry.label or sensor_name
                        current = getattr(entry, "current", None)
                        if current is None:
                            continue
                        lines.append((f"{label}: {current:.1f} C", "info"))
                    if len(lines) >= 5:
                        break
                if lines:
                    return lines[:5]
            except Exception:
                pass

        lines: list[OutputLine] = []
        try:
            for zone in sorted(Path("/sys/class/thermal").glob("thermal_zone*"))[:5]:
                zone_type = LinuxBackend._read_first_line(str(zone / "type")) or zone.name
                temp_raw = LinuxBackend._read_first_line(str(zone / "temp"))
                if not temp_raw:
                    continue
                value = float(temp_raw)
                current = value / 1000.0 if value > 1000 else value
                lines.append((f"{zone_type}: {current:.1f} C", "info"))
            if lines:
                return lines
        except OSError:
            pass
        return [("Temperature sensors unavailable.", "dim")]

    @staticmethod
    def _read_assignment_file(path: Path) -> dict[str, str]:
        values: dict[str, str] = {}
        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError:
            return values

        for line in raw_text.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        return values

    @staticmethod
    def _pci_device_label(slot_name: str, fallback: str) -> str:
        if not slot_name:
            return fallback

        output, error = LinuxBackend._run_command(["lspci", "-s", slot_name, "-nn"], timeout=2.0)
        if error or not output:
            return fallback

        first_line = output.splitlines()[0].strip()
        if ": " in first_line:
            return first_line.split(": ", 1)[1].strip() or fallback
        return first_line or fallback

    @staticmethod
    def _read_first_matching_int(base_dir: Path, patterns: tuple[str, ...]) -> int | None:
        for pattern in patterns:
            for candidate in sorted(base_dir.glob(pattern)):
                value = LinuxBackend._read_int_file(candidate)
                if value is not None:
                    return value
        return None

    @staticmethod
    def _intel_gpu_temperature_c(card_dir: Path) -> float | None:
        value = LinuxBackend._read_first_matching_int(
            card_dir,
            (
                "device/hwmon/hwmon*/temp1_input",
                "device/hwmon/hwmon*/temp*_input",
            ),
        )
        if value is None:
            return None
        return value / 1000.0 if value > 1000 else float(value)

    @staticmethod
    def _intel_gpu_utilization_percent(card_dir: Path) -> int | None:
        value = LinuxBackend._read_first_matching_int(
            card_dir,
            (
                "gpu_busy_percent",
                "device/gpu_busy_percent",
                "gt/gt*/busy_percent",
                "device/gt/gt*/busy_percent",
            ),
        )
        if value is None:
            return None
        return max(min(value, 100), 0)

    @staticmethod
    def _intel_gpu_lines() -> list[OutputLine]:
        try:
            drm_cards = sorted(Path("/sys/class/drm").glob("card[0-9]"), key=lambda path: path.name)
        except OSError:
            return []

        intel_cards = [
            card_dir for card_dir in drm_cards
            if LinuxBackend._read_first_line(str(card_dir / "device" / "vendor")).lower() == "0x8086"
        ]
        if not intel_cards:
            return []

        lines: list[OutputLine] = []
        multiple_cards = len(intel_cards) > 1

        for card_dir in intel_cards:
            device_dir = card_dir / "device"
            uevent = LinuxBackend._read_assignment_file(device_dir / "uevent")
            driver = uevent.get("DRIVER", "unknown")
            pci_id = uevent.get("PCI_ID", "")
            slot_name = uevent.get("PCI_SLOT_NAME", "")
            fallback = f"Intel GPU {pci_id}" if pci_id else "Intel GPU"
            label = LinuxBackend._pci_device_label(slot_name, fallback)
            prefix = f"{card_dir.name}: " if multiple_cards else ""

            lines.append((f"{prefix}{label}", "info"))

            detail_parts = []
            if driver:
                detail_parts.append(f"driver {driver}")
            if pci_id:
                detail_parts.append(f"PCI {pci_id}")
            if slot_name:
                detail_parts.append(f"slot {slot_name}")
            if detail_parts:
                lines.append((f"{prefix}{'  '.join(detail_parts)}", "info"))

            temp_c = LinuxBackend._intel_gpu_temperature_c(card_dir)
            util_pct = LinuxBackend._intel_gpu_utilization_percent(card_dir)
            if temp_c is not None:
                lines.append((f"{prefix}Temperature: {temp_c:.1f} C", "info"))
            else:
                lines.append((f"{prefix}Temperature: unavailable", "dim"))

            if util_pct is not None:
                lines.append((f"{prefix}Utilization: {util_pct}%", "info"))
            else:
                lines.append((f"{prefix}Utilization: unavailable", "dim"))

        return lines

    @staticmethod
    def _nvidia_value(value: str, suffix: str = "") -> str:
        normalized = value.strip()
        if not normalized:
            return "n/a"
        if normalized.lower() in {"n/a", "[n/a]", "not supported"}:
            return "n/a"
        return f"{normalized}{suffix}"

    @staticmethod
    def _parse_nvidia_smi_row(raw_line: str) -> str | None:
        parts = [part.strip() for part in raw_line.split(",")]
        if len(parts) != 5:
            return None

        name, utilization, temp, used, total = parts
        gpu_text = LinuxBackend._nvidia_value(utilization, "%")
        temp_text = LinuxBackend._nvidia_value(temp, " C")
        used_text = LinuxBackend._nvidia_value(used)
        total_text = LinuxBackend._nvidia_value(total)
        vram_text = (
            f"{used_text} / {total_text} MiB"
            if used_text != "n/a" and total_text != "n/a"
            else "n/a"
        )
        return f"{name}: GPU {gpu_text}  Temp {temp_text}  VRAM {vram_text}"

    @staticmethod
    def _gpu_lines() -> list[OutputLine]:
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return [("NVIDIA GPU telemetry unavailable.", "dim")]

        output, error = LinuxBackend._run_command(
            [
                nvidia_smi,
                "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            timeout=4.0,
        )
        if error:
            return [("NVIDIA GPU telemetry unavailable.", "dim")]

        lines: list[OutputLine] = []
        for raw_line in output.splitlines():
            formatted = LinuxBackend._parse_nvidia_smi_row(raw_line)
            if not formatted:
                continue
            lines.append((formatted, "info"))
        return lines or [("NVIDIA GPU telemetry unavailable.", "dim")]

    def _yield_section(self, title: str, entries: list[OutputLine]) -> Iterator[OutputLine]:
        yield (f"=== {title} ===", "header")
        if not entries:
            yield ("No data available.", "dim")
        else:
            for text, tag in entries:
                yield (text, tag)
        yield ("", "normal")

    def available_tools(self) -> set:
        tools = {"diagnostics"}
        from platform_utils import net as _pu_net
        if _pu_net.arp_scan_available():
            tools.add("arpscan")
        return tools

    def admin_required_for(self, tool: str) -> bool:
        return False

    def run_diagnostics(self, stop_event: Event) -> Iterator[OutputLine]:
        try:
            yield ("Running Linux diagnostics...", "info")
            sections: list[tuple[str, list[OutputLine]]] = []

            hostname, hostname_error = self._run_command(["hostname"])
            kernel, kernel_error = self._run_command(["uname", "-r"])
            uptime, uptime_error = self._run_command(["uptime", "-p"])
            system_lines: list[OutputLine] = [
                (f"OS: {self._read_os_name()}", "info"),
                (f"Hostname: {hostname.splitlines()[0].strip()}", "info") if hostname else
                (f"Hostname unavailable ({hostname_error})", "warning"),
                (f"Kernel: {kernel.splitlines()[0].strip()}", "info") if kernel else
                (f"Kernel unavailable ({kernel_error})", "warning"),
                (f"Uptime: {uptime.splitlines()[0].strip()}", "info") if uptime else
                (f"Uptime unavailable ({uptime_error})", "warning"),
            ]
            sections.append(("SYSTEM", system_lines))

            cpu = self._cpu_snapshot()
            cpu_lines: list[OutputLine] = [
                (f"Model: {cpu['model']}", "info"),
                (
                    f"Cores/Threads: {cpu['physical'] or 'n/a'} physical / "
                    f"{cpu['logical'] or 'n/a'} logical",
                    "info",
                ),
            ]
            if cpu["load"]:
                cpu_lines.append((f"Load average: {cpu['load']}", "info"))
            if cpu["usage"] is not None:
                cpu_lines.append((f"CPU usage: {cpu['usage']:.1f}%", "info"))
            else:
                cpu_lines.append(("CPU usage unavailable.", "dim"))
            sections.append(("CPU", cpu_lines))

            sections.append(("MEMORY", self._memory_lines()))
            sections.append(("DISK", self._disk_lines()))
            sections.append(("BATTERY", self._battery_lines()))
            sections.append(("NETWORK", self._network_lines(stop_event)))
            sections.append(("PROCESSES", self._process_lines()))
            sections.append(("TEMPERATURE", self._temperature_lines()))
            intel_gpu_lines = self._intel_gpu_lines()
            if intel_gpu_lines:
                sections.append(("INTEL GPU", intel_gpu_lines))
            sections.append(("GPU", self._gpu_lines()))

            for title, entries in sections:
                aborted, line = self._abort(stop_event)
                if aborted:
                    yield line
                    return
                yield from self._yield_section(title, entries)
            yield ("Diagnostics complete.", "success")
        except Exception as e:
            yield (f"Diagnostics failed: {e}", "error")

    def run_sfc(self, stop_event: Event) -> Iterator[OutputLine]:
        raise NotImplementedError("SFC is not supported on Linux in Phase 8")
        yield

    def run_dism(self, stop_event: Event) -> Iterator[OutputLine]:
        raise NotImplementedError("DISM is not supported on Linux in Phase 8")
        yield

    def export_services(self, path: str) -> None:
        raise NotImplementedError("Service backup is not supported on Linux in Phase 8")

    def set_service_startup(self, name: str, startup_type: str, dry: bool) -> tuple:
        raise NotImplementedError("Service changes are not supported on Linux in Phase 8")

    # ── ARP Scan (Linux-only) ────────────────────────────────────────────────

    def run_arp_scan(self, stop_event: Event,
                     interface: str | None = None,
                     cidr: str | None = None) -> Iterator[OutputLine]:
        """Run arp-scan and yield (line, tag) tuples.

        Yields both info lines (header, progress) and data lines (per device found).
        Data lines are serialized as JSON with tag 'data' so the frame can parse
        them and update table rows. Info lines use tags 'info'/'warning'/'error'.
        """
        import json as _json
        from platform_utils import net as _pu_net

        if not _pu_net.arp_scan_available():
            yield ("arp-scan is not installed on this system.", "error")
            yield ("On Ubuntu/Debian: sudo apt install arp-scan", "info")
            yield ("On Fedora: sudo dnf install arp-scan", "info")
            return

        yield ("Starting arp-scan...", "header")
        if interface:
            yield (f"Interface: {interface}", "info")
        if cidr:
            yield (f"Network: {cidr}", "info")
        else:
            yield ("Network: local subnet via selected interface", "info")

        found_count = 0
        scan_iter = _pu_net.arp_scan_scan(
            interface=interface,
            cidr=cidr,
            timeout_s=120,
        )
        try:
            for raw_line in scan_iter:
                if stop_event.is_set():
                    yield ("Scan aborted by user.", "warning")
                    return

                record = _pu_net.parse_arp_scan_line(raw_line)
                if record is None:
                    continue

                found_count += 1
                yield (_json.dumps(record), "data")

        except FileNotFoundError as e:
            yield (str(e), "error")
            return
        except PermissionError as e:
            yield (str(e), "error")
            for line in self._arp_scan_capability_fix_lines():
                yield line
            return
        except subprocess.TimeoutExpired:
            yield ("Scan timeout — process was terminated.", "warning")
            return
        except Exception as e:
            yield (f"Unexpected error during scan: {e}", "error")
            return
        finally:
            close = getattr(scan_iter, "close", None)
            if callable(close):
                close()

        if found_count == 0:
            yield ("No devices found.", "warning")
        else:
            yield (f"Scan complete — {found_count} devices found.", "success")


# ── Factory ───────────────────────────────────────────────────────────────────

def get_backend() -> SystemBackend:
    if IS_WINDOWS:
        return WindowsBackend()
    if IS_LINUX:
        return LinuxBackend()
    raise RuntimeError("Unsupported platform for SystemBackend")
