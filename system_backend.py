"""
system_backend.py — Plattform-backend for SystemToolsFrame.

Abstrakt lag mellom SystemToolsFrame og OS-spesifikke verktøy
(PowerShell/SFC/DISM på Windows, fremtidige Linux-ekvivalenter).

Generator-baserte streaming-metoder yielder (linje, tag)-tupler.
Framen konsumerer generatoren og kaller self.q(line, tag) per element.
"""

import subprocess
import re
import json
from abc import ABC, abstractmethod
from threading import Event
from typing import Iterator, Tuple

from platform_utils import SUBPROCESS_FLAGS, IS_WINDOWS, IS_LINUX

# (linje_tekst, tag) der tag ∈ {"header", "normal", "info", "success", "warning", "error", "dim"}
OutputLine = Tuple[str, str]

# ── Modul-level konstanter (kopiert verbatim fra nettools.py) ─────────────────

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


# ── Abstrakt baseklasse ───────────────────────────────────────────────────────

class SystemBackend(ABC):
    """Abstrakt plattform-backend for system-verktøy.

    Generator-baserte metoder yielder output mens prosessen kjører.
    Frame konsumerer generator og kaller self.q(line, tag) for hver line.
    """

    # ── Capability-rapportering ───────────────────────────────────────────────

    @abstractmethod
    def available_tools(self) -> set:
        """Returnerer set av verktøy-navn som er støttet på denne plattformen.
        Navn: 'diagnostics', 'sfc', 'dism', 'backup', 'restore', 'debloat'."""

    @abstractmethod
    def admin_required_for(self, tool: str) -> bool:
        """True hvis verktøyet krever admin/root for å fungere."""

    # ── Streaming-operasjoner (generatorer) ──────────────────────────────────

    @abstractmethod
    def run_diagnostics(self, stop_event: Event) -> Iterator[OutputLine]:
        """Kjører systemdiagnostikk. Yielder (line, tag) per output-linje.
        Sjekk stop_event.is_set() mellom linjer og terminer prosess ved abort."""

    @abstractmethod
    def run_sfc(self, stop_event: Event) -> Iterator[OutputLine]:
        """Kjører SFC-scan. Yielder (line, tag). Siste yield skal være
        en resultat-linje med tag 'success'/'error'/'warning' basert på output."""

    @abstractmethod
    def run_dism(self, stop_event: Event) -> Iterator[OutputLine]:
        """Kjører DISM restore-health. Yielder (line, tag)."""

    # ── Service-primitiver (synkron) ─────────────────────────────────────────

    @abstractmethod
    def export_services(self, path: str) -> None:
        """Eksporterer alle services til JSON-fil. Kaster IOError ved feil."""

    @abstractmethod
    def set_service_startup(self, name: str, startup_type: str, dry: bool) -> tuple:
        """Setter oppstartstype for én service.
        Returnerer (success, display_line).
        dry=True returnerer preview-linje uten å kjøre kommandoen."""


# ── Windows-implementasjon ────────────────────────────────────────────────────

class WindowsBackend(SystemBackend):
    """Full Windows-implementasjon basert på PowerShell, SFC og DISM."""

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


# ── Linux-stub ────────────────────────────────────────────────────────────────

class LinuxBackend(SystemBackend):
    """Linux-stub — full implementasjon i Fase 8."""

    def available_tools(self) -> set:
        return set()

    def admin_required_for(self, tool: str) -> bool:
        return True

    def run_diagnostics(self, stop_event: Event) -> Iterator[OutputLine]:
        raise NotImplementedError("Linux backend — implementeres i Fase 8")
        yield  # gjør funksjonen til en generator

    def run_sfc(self, stop_event: Event) -> Iterator[OutputLine]:
        raise NotImplementedError("Linux backend — implementeres i Fase 8")
        yield

    def run_dism(self, stop_event: Event) -> Iterator[OutputLine]:
        raise NotImplementedError("Linux backend — implementeres i Fase 8")
        yield

    def export_services(self, path: str) -> None:
        raise NotImplementedError("Linux backend — implementeres i Fase 8")

    def set_service_startup(self, name: str, startup_type: str, dry: bool) -> tuple:
        raise NotImplementedError("Linux backend — implementeres i Fase 8")


# ── Factory ───────────────────────────────────────────────────────────────────

def get_backend() -> SystemBackend:
    if IS_WINDOWS:
        return WindowsBackend()
    if IS_LINUX:
        return LinuxBackend()
    raise RuntimeError("Unsupported platform for SystemBackend")
