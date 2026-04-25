#requires -version 5.1
<#
    SkipperToolkit.ps1
    Samlet Windows-verktøykasse for diagnostikk, reparasjon og kontrollert debloat.

    Bygget for Bengt Simon Dragseth.

    HOVEDPRINSIPP:
    - Ingen skjulte nedlastinger
    - Ingen automatiske systemendringer uten at bruker velger det i menyen
    - Safe og Aggressive profiler er skilt tydelig
    - Backup av tjenester tas før endringer
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ------------------------------------------------------------
# KONFIG
# ------------------------------------------------------------
$Script:ToolkitName = 'Skipper Toolkit'
$Script:ToolkitVersion = '1.0'
$Script:ToolkitRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$Script:LogRoot = Join-Path $env:USERPROFILE 'Desktop\SkipperToolkit_Logs'
$Script:Timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$Script:CurrentRunFolder = Join-Path $Script:LogRoot $Script:Timestamp
$Script:ServiceBackupFolder = Join-Path $Script:CurrentRunFolder 'ServiceBackups'
$Script:DryRun = $false

# Profilvalg
$Script:SafeDisableServices = @(
    # ASUS / OEM
    'AsusAppService',
    'ASUSSoftwareManager',
    'ASUSSwitch',
    'AsusCertService',
    'ASUSOptimization',
    'ASUSSystemAnalysis',
    'ASUSSystemDiagnosis',
    'AsusPTPService',

    # Telemetri / diverse
    'DiagTrack',
    'whesvc',
    'wisvc',
    'InventorySvc',
    'RetailDemo',
    'MapsBroker',
    'Fax',
    'RemoteRegistry',
    'PushToInstall',
    'WbioSrvc',
    'wcncsvc',
    'lfsvc',

    # Xbox
    'XboxGipSvc',
    'XblAuthManager',
    'XboxNetApiSvc',
    'XblGameSave',

    # Nettverk som ofte er unødvendig hjemme
    'SharedAccess',
    'SSDPSRV',
    'upnphost',
    'WwanSvc',
    'WebClient'
)

$Script:AggressiveExtraDisableServices = @(
    # Mer aggressivt - kan påvirke feilsøking og dev-oppsett
    'DPS',
    'WdiServiceHost',
    'WdiSystemHost',
    'WerSvc',
    'lmhosts',
    'dot3svc',
    'WinRM',
    'hns',
    'WSLService',
    'HvHost',
    'wmiApSrv',
    'PcaSvc',
    'StiSvc',
    'TapiSrv',
    'WManSvc',
    'perceptionsimulation'
)

$Script:ManualServices = @(
    'UsoSvc',
    'WSearch'
)

# ------------------------------------------------------------
# HJELPEFUNKSJONER
# ------------------------------------------------------------
function Ensure-Admin {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )

    if (-not $isAdmin) {
        Write-Host ''
        Write-Host 'FEIL: Dette scriptet må kjøres som Administrator.' -ForegroundColor Red
        Write-Host ''
        Read-Host 'Trykk Enter for å avslutte'
        exit 1
    }
}

function Ensure-Folders {
    foreach ($folder in @($Script:LogRoot, $Script:CurrentRunFolder, $Script:ServiceBackupFolder)) {
        if (-not (Test-Path $folder)) {
            New-Item -ItemType Directory -Path $folder -Force | Out-Null
        }
    }
}

function Write-Section {
    param([string]$Title)
    Write-Host ''
    Write-Host ('=' * 60) -ForegroundColor Cyan
    Write-Host (' ' + $Title) -ForegroundColor Cyan
    Write-Host ('=' * 60) -ForegroundColor Cyan
}

function Pause-Toolkit {
    Write-Host ''
    Read-Host 'Trykk Enter for å fortsette'
}

function New-TextReport {
    param(
        [string]$BaseName,
        [string[]]$Content
    )

    $path = Join-Path $Script:CurrentRunFolder ("{0}_{1}.txt" -f $BaseName, (Get-Date -Format 'HH-mm-ss'))
    $Content | Out-File -FilePath $path -Encoding UTF8
    return $path
}

function Get-ServiceSnapshot {
    Get-CimInstance Win32_Service |
        Sort-Object Name |
        Select-Object Name, DisplayName, State, StartMode, StartName
}

function Save-ServiceBackup {
    $snapshot = Get-ServiceSnapshot
    $jsonPath = Join-Path $Script:ServiceBackupFolder ("Services_Backup_{0}.json" -f (Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'))
    $csvPath  = Join-Path $Script:ServiceBackupFolder ("Services_Backup_{0}.csv" -f (Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'))

    $snapshot | ConvertTo-Json -Depth 3 | Out-File -FilePath $jsonPath -Encoding UTF8
    $snapshot | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8

    return @{
        Json = $jsonPath
        Csv  = $csvPath
    }
}

function Restore-ServiceBackup {
    Write-Section 'Gjenopprett tjenester fra backup'

    $files = Get-ChildItem -Path $Script:ServiceBackupFolder -Filter '*.json' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending

    if (-not $files) {
        Write-Host 'Fant ingen JSON-backup i dagens mappe.' -ForegroundColor Yellow
        Write-Host "Sjekk manuelt her: $Script:ServiceBackupFolder" -ForegroundColor DarkGray
        return
    }

    Write-Host 'Tilgjengelige backups:' -ForegroundColor Yellow
    for ($i = 0; $i -lt $files.Count; $i++) {
        Write-Host ("[{0}] {1}" -f ($i + 1), $files[$i].Name)
    }

    $choice = Read-Host 'Velg nummer på backup du vil gjenopprette'
    if (-not [int]::TryParse($choice, [ref]$null)) {
        Write-Host 'Ugyldig valg.' -ForegroundColor Red
        return
    }

    $index = [int]$choice - 1
    if ($index -lt 0 -or $index -ge $files.Count) {
        Write-Host 'Valget er utenfor listen.' -ForegroundColor Red
        return
    }

    $selected = $files[$index].FullName
    $services = Get-Content $selected -Raw | ConvertFrom-Json

    $log = New-Object System.Collections.Generic.List[string]
    $log.Add("Gjenoppretter fra: $selected")
    $log.Add('')

    foreach ($svc in $services) {
        try {
            $current = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
            if (-not $current) {
                $log.Add("Ikke funnet: $($svc.Name)")
                continue
            }

            if ($Script:DryRun) {
                $log.Add("DRY-RUN: Ville satt $($svc.Name) til StartMode=$($svc.StartMode)")
                continue
            }

            switch ($svc.StartMode) {
                'Auto'   { Set-Service -Name $svc.Name -StartupType Automatic }
                'Manual' { Set-Service -Name $svc.Name -StartupType Manual }
                'Disabled' { Set-Service -Name $svc.Name -StartupType Disabled }
                default  { $log.Add("Hoppet over ukjent StartMode for $($svc.Name): $($svc.StartMode)") }
            }

            $log.Add("OK: $($svc.Name) -> $($svc.StartMode)")
        }
        catch {
            $log.Add("FEIL: $($svc.Name) -> $($_.Exception.Message)")
        }
    }

    $report = New-TextReport -BaseName 'ServiceRestore' -Content $log
    Write-Host "Rapport lagret: $report" -ForegroundColor Green
}

function Invoke-ExternalCommandCapture {
    param(
        [string]$FilePath,
        [string]$Arguments,
        [string]$Title,
        [switch]$ShowLiveOutput
    )

    Write-Section $Title
    Write-Host "$FilePath $Arguments" -ForegroundColor DarkGray

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = $Arguments
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi

    [void]$process.Start()

    $stdout = New-Object System.Collections.Generic.List[string]
    $stderr = New-Object System.Collections.Generic.List[string]

    while (-not $process.HasExited) {
        while (-not $process.StandardOutput.EndOfStream) {
            $line = $process.StandardOutput.ReadLine()
            $stdout.Add($line)
            if ($ShowLiveOutput) { Write-Host $line }
        }
        Start-Sleep -Milliseconds 200
    }

    while (-not $process.StandardOutput.EndOfStream) {
        $line = $process.StandardOutput.ReadLine()
        $stdout.Add($line)
        if ($ShowLiveOutput) { Write-Host $line }
    }

    while (-not $process.StandardError.EndOfStream) {
        $line = $process.StandardError.ReadLine()
        $stderr.Add($line)
        if ($ShowLiveOutput -and $line) { Write-Host $line -ForegroundColor Yellow }
    }

    $process.WaitForExit()

    return [PSCustomObject]@{
        ExitCode = $process.ExitCode
        StdOut   = $stdout
        StdErr   = $stderr
    }
}

function Invoke-SFCScan {
    $start = Get-Date
    $result = Invoke-ExternalCommandCapture -FilePath 'sfc.exe' -Arguments '/scannow' -Title 'SFC /SCANNOW' -ShowLiveOutput
    $end = Get-Date

    $allText = @()
    $allText += "Startet : $($start.ToString('dd.MM.yyyy HH:mm:ss'))"
    $allText += "Ferdig  : $($end.ToString('dd.MM.yyyy HH:mm:ss'))"
    $allText += "ExitCode: $($result.ExitCode)"
    $allText += ''
    $allText += '--- STDOUT ---'
    $allText += $result.StdOut
    $allText += ''
    $allText += '--- STDERR ---'
    $allText += $result.StdErr

    $cbsLog = 'C:\Windows\Logs\CBS\CBS.log'
    if (Test-Path $cbsLog) {
        $allText += ''
        $allText += '--- Siste 50 linjer fra CBS.log ---'
        $allText += (Get-Content $cbsLog -Tail 50)
    }

    $report = New-TextReport -BaseName 'SFC' -Content $allText

    $joined = ($result.StdOut -join "`n")
    if ($joined -match 'did not find any integrity violations|fant ingen integritetsbrudd') {
        Write-Host 'Resultat: Ingen integritetsfeil funnet.' -ForegroundColor Green
    }
    elseif ($joined -match 'successfully repaired|reparerte dem') {
        Write-Host 'Resultat: Feil ble funnet og reparert.' -ForegroundColor Yellow
    }
    elseif ($joined -match 'unable to fix|kunne ikke reparere') {
        Write-Host 'Resultat: Feil ble funnet, men ikke reparert.' -ForegroundColor Red
        Write-Host 'Anbefaling: Kjør DISM og deretter SFC på nytt.' -ForegroundColor Yellow
    }
    else {
        Write-Host 'Resultat: Uklart. Se rapport.' -ForegroundColor Yellow
    }

    Write-Host "Rapport lagret: $report" -ForegroundColor Green
}

function Invoke-DISMRepair {
    $steps = @(
        @{ Name = 'CheckHealth';   Args = '/Online /Cleanup-Image /CheckHealth' },
        @{ Name = 'ScanHealth';    Args = '/Online /Cleanup-Image /ScanHealth' },
        @{ Name = 'RestoreHealth'; Args = '/Online /Cleanup-Image /RestoreHealth' }
    )

    $reportLines = New-Object System.Collections.Generic.List[string]
    $reportLines.Add("DISM-rapport startet: $(Get-Date -Format 'dd.MM.yyyy HH:mm:ss')")
    $reportLines.Add('')

    foreach ($step in $steps) {
        $result = Invoke-ExternalCommandCapture -FilePath 'dism.exe' -Arguments $step.Args -Title ("DISM {0}" -f $step.Name) -ShowLiveOutput
        $reportLines.Add(("=== {0} ===" -f $step.Name))
        $reportLines.Add(("ExitCode: {0}" -f $result.ExitCode))
        $reportLines.AddRange([string[]]$result.StdOut)
        if ($result.StdErr.Count -gt 0) {
            $reportLines.Add('--- STDERR ---')
            $reportLines.AddRange([string[]]$result.StdErr)
        }
        $reportLines.Add('')
    }

    $dismLog = 'C:\Windows\Logs\DISM\dism.log'
    if (Test-Path $dismLog) {
        $reportLines.Add('--- Siste 50 linjer fra dism.log ---')
        $reportLines.AddRange([string[]](Get-Content $dismLog -Tail 50))
    }

    $report = New-TextReport -BaseName 'DISM' -Content $reportLines
    Write-Host "Rapport lagret: $report" -ForegroundColor Green
    Write-Host 'Anbefaling: Kjør SFC etter DISM dersom du reparerer systemfiler.' -ForegroundColor Cyan
}

function Get-InstalledAppsSafe {
    $paths = @(
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )

    $items = foreach ($path in $paths) {
        Get-ItemProperty $path -ErrorAction SilentlyContinue |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_.DisplayName) } |
            Select-Object DisplayName, DisplayVersion, Publisher, InstallDate
    }

    $items | Sort-Object DisplayName -Unique
}

function Invoke-PCDiagnostikk {
    Write-Section 'PC Diagnostikk'

    $report = New-Object System.Collections.Generic.List[string]
    $report.Add("Diagnostikk startet: $(Get-Date -Format 'dd.MM.yyyy HH:mm:ss')")
    $report.Add(("Maskin: {0}" -f $env:COMPUTERNAME))
    $report.Add(("Bruker: {0}" -f $env:USERNAME))
    $report.Add('')

    try {
        $cs = Get-CimInstance Win32_ComputerSystem
        $os = Get-CimInstance Win32_OperatingSystem
        $bios = Get-CimInstance Win32_BIOS
        $report.Add('=== SYSTEM ===')
        $report.Add(("Produsent: {0}" -f $cs.Manufacturer))
        $report.Add(("Modell: {0}" -f $cs.Model))
        $report.Add(("OS: {0}" -f $os.Caption))
        $report.Add(("Versjon: {0}" -f $os.Version))
        $report.Add(("Build: {0}" -f $os.BuildNumber))
        $report.Add(("BIOS: {0}" -f $bios.SMBIOSBIOSVersion))
        $report.Add('')
    }
    catch {
        $report.Add("FEIL SYSTEM: $($_.Exception.Message)")
    }

    try {
        $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
        $report.Add('=== CPU / RAM ===')
        $report.Add(("CPU: {0}" -f $cpu.Name))
        $report.Add(("Kjerner: {0}" -f $cpu.NumberOfCores))
        $report.Add(("Logiske prosessorer: {0}" -f $cpu.NumberOfLogicalProcessors))
        $totalRamGB = [math]::Round((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1GB, 2)
        $report.Add(("RAM installert: {0} GB" -f $totalRamGB))
        $report.Add('')
    }
    catch {
        $report.Add("FEIL CPU/RAM: $($_.Exception.Message)")
    }

    try {
        $report.Add('=== DISK ===')
        foreach ($drive in (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -gt 0 })) {
            $total = [math]::Round(($drive.Used + $drive.Free) / 1GB, 2)
            $free = [math]::Round($drive.Free / 1GB, 2)
            $used = [math]::Round($drive.Used / 1GB, 2)
            $pct = if ($total -gt 0) { [math]::Round(($free / $total) * 100, 1) } else { 0 }
            $report.Add(("{0}: Total {1} GB | Brukt {2} GB | Ledig {3} GB | Ledig {4}%" -f $drive.Name, $total, $used, $free, $pct))
        }
        $report.Add('')
    }
    catch {
        $report.Add("FEIL DISK: $($_.Exception.Message)")
    }

    try {
        $report.Add('=== GPU ===')
        foreach ($gpu in (Get-CimInstance Win32_VideoController)) {
            $report.Add(("GPU: {0}" -f $gpu.Caption))
            $report.Add(("Driver: {0}" -f $gpu.DriverVersion))
            $report.Add(("Status: {0}" -f $gpu.Status))
            $report.Add('')
        }
    }
    catch {
        $report.Add("FEIL GPU: $($_.Exception.Message)")
    }

    try {
        $report.Add('=== NETTVERK ===')
        foreach ($nic in (Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled })) {
            $report.Add(("Adapter: {0}" -f $nic.Description))
            $report.Add(("IP: {0}" -f (($nic.IPAddress -join ', '))))
            $report.Add(("Gateway: {0}" -f (($nic.DefaultIPGateway -join ', '))))
            $report.Add(("DNS: {0}" -f (($nic.DNSServerSearchOrder -join ', '))))
            $report.Add('')
        }
    }
    catch {
        $report.Add("FEIL NETTVERK: $($_.Exception.Message)")
    }

    try {
        $report.Add('=== KJØRENDE TJENESTER ===')
        $runningServices = Get-Service | Where-Object Status -eq 'Running' | Sort-Object DisplayName
        foreach ($svc in $runningServices) {
            $report.Add(("{0} ({1})" -f $svc.DisplayName, $svc.Name))
        }
        $report.Add('')
    }
    catch {
        $report.Add("FEIL TJENESTER: $($_.Exception.Message)")
    }

    try {
        $report.Add('=== WINDOWS UPDATE (Siste 10 HotFix) ===')
        foreach ($hf in (Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10)) {
            $dateString = if ($hf.InstalledOn) { $hf.InstalledOn.ToString('dd.MM.yyyy') } else { 'Ukjent' }
            $report.Add(("{0} | {1} | {2}" -f $dateString, $hf.HotFixID, $hf.Description))
        }
        $report.Add('')
    }
    catch {
        $report.Add("FEIL HOTFIX: $($_.Exception.Message)")
    }

    try {
        $report.Add('=== AUTOSTART ===')
        foreach ($path in @(
            'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
            'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run'
        )) {
            $props = Get-ItemProperty $path -ErrorAction SilentlyContinue
            if ($props) {
                $props.PSObject.Properties |
                    Where-Object { $_.Name -notlike 'PS*' } |
                    ForEach-Object { $report.Add(("{0} | {1}" -f $_.Name, $path)) }
            }
        }
        $report.Add('')
    }
    catch {
        $report.Add("FEIL AUTOSTART: $($_.Exception.Message)")
    }

    try {
        $report.Add('=== INSTALLERTE PROGRAMMER (første 100 alfabetisk) ===')
        foreach ($app in (Get-InstalledAppsSafe | Select-Object -First 100)) {
            $report.Add(("{0} | {1} | {2}" -f $app.DisplayName, $app.DisplayVersion, $app.Publisher))
        }
        $report.Add('')
    }
    catch {
        $report.Add("FEIL PROGRAMMER: $($_.Exception.Message)")
    }

    try {
        $report.Add('=== Siste 30 kritiske/system-relaterte hendelser ===')
        $events = Get-WinEvent -FilterHashtable @{ LogName='System'; Level=1,2; StartTime=(Get-Date).AddDays(-7) } -MaxEvents 30 -ErrorAction SilentlyContinue
        foreach ($event in $events) {
            $report.Add(("{0} | ID {1} | {2}" -f $event.TimeCreated.ToString('dd.MM.yyyy HH:mm:ss'), $event.Id, $event.ProviderName))
            $report.Add(("Melding: {0}" -f (($event.Message -replace '\r|\n', ' ') -replace '\s+', ' ')))
            $report.Add('')
        }
    }
    catch {
        $report.Add("FEIL EVENTS: $($_.Exception.Message)")
    }

    $path = New-TextReport -BaseName 'PC_Diagnostikk' -Content $report
    Write-Host "Rapport lagret: $path" -ForegroundColor Green
}

function Set-ServiceStartupSafe {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [ValidateSet('Automatic','Manual','Disabled')]
        [string]$StartupType,

        [switch]$StopIfRunning,

        [ref]$Counters
    )

    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $svc) {
        $Counters.Value.NotInstalled++
        Write-Host ("- Ikke installert: {0}" -f $Name) -ForegroundColor DarkGray
        return
    }

    try {
        if ($Script:DryRun) {
            Write-Host ("[DRY-RUN] {0} -> {1}" -f $Name, $StartupType) -ForegroundColor Cyan
            $Counters.Value.Success++
            return
        }

        if ($StopIfRunning -and $svc.Status -eq 'Running') {
            Stop-Service -Name $Name -Force -ErrorAction SilentlyContinue
        }

        Set-Service -Name $Name -StartupType $StartupType -ErrorAction Stop
        Write-Host ("OK: {0} -> {1}" -f $Name, $StartupType) -ForegroundColor Green
        $Counters.Value.Success++
    }
    catch {
        Write-Host ("FEIL: {0} -> {1}" -f $Name, $_.Exception.Message) -ForegroundColor Yellow
        $Counters.Value.Failed++
    }
}

function Invoke-DebloatProfile {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('SAFE','AGGRESSIVE')]
        [string]$Profile
    )

    Write-Section ("Debloat-profil: {0}" -f $Profile)

    $warning = switch ($Profile) {
        'SAFE' {
            'SAFE-profil: Holder diagnostikk, WSL/Hyper-V og sentrale feilsøkingstjenester i fred.'
        }
        'AGGRESSIVE' {
            'AGGRESSIVE-profil: Kan påvirke WSL, Hyper-V, feilsøking, WinRM og generell dev-/pentest-rigg.'
        }
    }
    Write-Host $warning -ForegroundColor Yellow

    $confirm = Read-Host ("Skriv JA for å fortsette med {0}-profil" -f $Profile)
    if ($confirm -ne 'JA') {
        Write-Host 'Avbrutt av bruker.' -ForegroundColor Yellow
        return
    }

    $backup = Save-ServiceBackup
    Write-Host "Service-backup lagret: $($backup.Json)" -ForegroundColor Green
    Write-Host "CSV-backup lagret:     $($backup.Csv)" -ForegroundColor Green

    $serviceList = @($Script:SafeDisableServices)
    if ($Profile -eq 'AGGRESSIVE') {
        $serviceList += $Script:AggressiveExtraDisableServices
    }

    $counters = [PSCustomObject]@{
        Success      = 0
        Failed       = 0
        NotInstalled = 0
    }

    foreach ($name in $serviceList | Sort-Object -Unique) {
        Set-ServiceStartupSafe -Name $name -StartupType Disabled -StopIfRunning -Counters ([ref]$counters)
    }

    Write-Host ''
    Write-Host 'Setter manuelle tjenester ...' -ForegroundColor Cyan
    foreach ($name in $Script:ManualServices | Sort-Object -Unique) {
        Set-ServiceStartupSafe -Name $name -StartupType Manual -Counters ([ref]$counters)
    }

    $lines = @(
        "Profil         : $Profile",
        "DryRun         : $Script:DryRun",
        "Success        : $($counters.Success)",
        "Failed         : $($counters.Failed)",
        "NotInstalled   : $($counters.NotInstalled)",
        "Backup JSON    : $($backup.Json)",
        "Backup CSV     : $($backup.Csv)",
        '',
        'Deaktiverte tjenester:',
        ($serviceList | Sort-Object -Unique),
        '',
        'Manuelle tjenester:',
        ($Script:ManualServices | Sort-Object -Unique)
    )

    $report = New-TextReport -BaseName ("Debloat_{0}" -f $Profile) -Content $lines
    Write-Host ''
    Write-Host 'Ferdig.' -ForegroundColor Green
    Write-Host ("Rapport lagret: {0}" -f $report) -ForegroundColor Green
    Write-Host 'Anbefaling: Start PC-en på nytt for at alle endringer skal slå inn.' -ForegroundColor Yellow
}

function Show-ToolkitMenu {
    Clear-Host
    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host (' {0} v{1}' -f $Script:ToolkitName, $Script:ToolkitVersion) -ForegroundColor Cyan
    Write-Host ' Diagnostikk, reparasjon og kontrollert debloat' -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''
    Write-Host ('Loggmappe : {0}' -f $Script:CurrentRunFolder) -ForegroundColor DarkGray
    Write-Host ('Dry-run   : {0}' -f $Script:DryRun) -ForegroundColor DarkGray
    Write-Host ''
    Write-Host ' [1] PC-diagnostikk rapport'
    Write-Host ' [2] Kjør SFC /scannow'
    Write-Host ' [3] Kjør DISM reparasjon'
    Write-Host ' [4] Safe debloat'
    Write-Host ' [5] Aggressive debloat'
    Write-Host ' [6] Ta backup av tjenester nå'
    Write-Host ' [7] Gjenopprett tjenester fra dagens backup'
    Write-Host ' [8] Bytt Dry-run av/på'
    Write-Host ' [9] Åpne loggmappe'
    Write-Host ' [0] Avslutt'
    Write-Host ''
}

# ------------------------------------------------------------
# OPPSTART
# ------------------------------------------------------------
Ensure-Admin
Ensure-Folders

while ($true) {
    Show-ToolkitMenu
    $choice = Read-Host 'Velg menyvalg'

    switch ($choice) {
        '1' {
            Invoke-PCDiagnostikk
            Pause-Toolkit
        }
        '2' {
            Invoke-SFCScan
            Pause-Toolkit
        }
        '3' {
            Invoke-DISMRepair
            Pause-Toolkit
        }
        '4' {
            Invoke-DebloatProfile -Profile 'SAFE'
            Pause-Toolkit
        }
        '5' {
            Invoke-DebloatProfile -Profile 'AGGRESSIVE'
            Pause-Toolkit
        }
        '6' {
            $backup = Save-ServiceBackup
            Write-Host "Backup lagret: $($backup.Json)" -ForegroundColor Green
            Write-Host "Backup lagret: $($backup.Csv)" -ForegroundColor Green
            Pause-Toolkit
        }
        '7' {
            Restore-ServiceBackup
            Pause-Toolkit
        }
        '8' {
            $Script:DryRun = -not $Script:DryRun
            Write-Host ("Dry-run er nå satt til: {0}" -f $Script:DryRun) -ForegroundColor Green
            Pause-Toolkit
        }
        '9' {
            Start-Process explorer.exe $Script:CurrentRunFolder
        }
        '0' {
            break
        }
        default {
            Write-Host 'Ugyldig valg.' -ForegroundColor Red
            Start-Sleep -Seconds 1
        }
    }
}
