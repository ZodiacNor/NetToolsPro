# ============================================================
#  WindowsDebloater.ps1
#  Tilpasset konfigurasjon for Bengt Simon Dragseth
#  ASUS Gaming/Dev PC - Sist oppdatert: 20.03.2026
#
#  BRUK: Kjør som Administrator i PowerShell
#  powershell -ExecutionPolicy Bypass -File WindowsDebloater.ps1
#
#  BEHOLDER:
#   - ArmoryCrate (fan-kontroll + RGB)
#   - ASUS AURA SYNC (RGB)
#   - Bluetooth
#   - Print Spooler (printer)
#   - Windows Push Notifications
#   - Gaming Services (Steam/WoW)
#   - Lyd og nettverkstjenester
#   - Windows Defender / Sikkerhet
# ============================================================

# Krever Administrator
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")) {
    Write-Host ""
    Write-Host "  FEIL: Kjør PowerShell som Administrator!" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

# Header
Clear-Host
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   WindowsDebloater - Bengt Simon Dragseth" -ForegroundColor Cyan
Write-Host "   ASUS Gaming/Dev PC                      " -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# Tell kjørende tjenester før
$forAntall = (Get-Service | Where-Object {$_.Status -eq "Running"}).Count
Write-Host "  Kjørende tjenester FØR: $forAntall" -ForegroundColor Yellow
Write-Host ""

# ============================================================
# TJENESTER SOM SKAL DEAKTIVERES
# ============================================================
$deaktiver = @(

    # --- ASUS BLOAT (beholder Armoury Crate + AURA) ---
    "AsusAppService",           # ASUS App Service
    "ASUSSoftwareManager",      # ASUS Software Manager - auto-oppdatering
    "ASUSSwitch",               # ASUS Switch
    "AsusCertService",          # ASUS Certificate Service
    "ASUSOptimization",         # ASUS Optimization
    "ASUSSystemAnalysis",       # ASUS System Analysis
    "ASUSSystemDiagnosis",      # ASUS System Diagnosis
    "AsusPTPService",           # ASUS PTP Service

    # --- DIAGNOSTIKK OG TELEMETRI ---
    "DPS",                      # Diagnostic Policy Service
    "WdiServiceHost",           # Diagnostic Service Host
    "WdiSystemHost",            # Diagnostic System Host
    "DiagTrack",                # Connected User Experiences and Telemetry
    "whesvc",                   # Windows-tilstand og optimaliserte opplevelser
    "WerSvc",                   # Windows Error Reporting
    "wisvc",                    # Windows Insider-tjeneste

    # --- UNØDVENDIGE NETTVERKSTJENESTER ---
    "SharedAccess",             # Internet Connection Sharing
    "SSDPSRV",                  # SSDP Discovery / UPnP
    "lmhosts",                  # TCP/IP NetBIOS Helper
    "dot3svc",                  # Wired AutoConfig (bruker WiFi)
    "WwanSvc",                  # WWAN AutoConfig (mobilnett)
    "WinRM",                    # Windows Remote Management
    "WebClient",                # WebClient
    "upnphost",                 # UPnP Device Host

    # --- XBOX (ikke nødvendig) ---
    "XboxGipSvc",               # Xbox Accessory Management
    "XblAuthManager",           # Xbox Live godkjenning
    "XboxNetApiSvc",            # Xbox Live nettverkstjeneste
    "XblGameSave",              # Xbox Live spillagring

    # --- VIRTUALISERING (ikke i bruk) ---
    "hns",                      # Vertsnettverkstjeneste
    "WSLService",               # WSL Service (starter on-demand)
    "HvHost",                   # Hyper-V Host

    # --- STEDSTJENESTER ---
    "lfsvc",                    # Geolocation Service

    # --- DIVERSE BLOAT ---
    "wmiApSrv",                 # WMI Performance Adapter
    "InventorySvc",             # Vurderingstjeneste for beholdning
    "PcaSvc",                   # Program Compatibility Assistant
    "StiSvc",                   # Windows Image Acquisition (skanner)
    "TapiSrv",                  # Telephony (modem/faks)
    "WbioSrvc",                 # Windows Biometric Service
    "wcncsvc",                  # Windows Connect Now
    "PushToInstall",            # Windows PushToInstall
    "WManSvc",                  # Windows Management-tjeneste
    "perceptionsimulation",     # Windows Perception Simulation
    "RetailDemo",               # Retail Demo Service
    "RemoteRegistry",           # Remote Registry
    "Fax",                      # Faks
    "MapsBroker"                # Downloaded Maps Manager
)

# ============================================================
# KJØR DEAKTIVERING
# ============================================================
$suksess = 0
$feilet = 0
$ikkeInstallert = 0

foreach ($t in $deaktiver) {
    $tjeneste = Get-Service -Name $t -ErrorAction SilentlyContinue
    if (-not $tjeneste) {
        Write-Host "  - Ikke installert: $t" -ForegroundColor DarkGray
        $ikkeInstallert++
        continue
    }
    try {
        if ($tjeneste.Status -eq "Running") {
            Stop-Service -Name $t -Force -ErrorAction Stop
        }
        Set-Service -Name $t -StartupType Disabled -ErrorAction Stop
        Write-Host "  ✓ Deaktivert: $t" -ForegroundColor Green
        $suksess++
    } catch {
        Write-Host "  ! Kunne ikke deaktivere: $t" -ForegroundColor Yellow
        $feilet++
    }
}

# ============================================================
# SETT NOEN TIL MANUELL (ikke disabled - men starter ikke automatisk)
# ============================================================
Write-Host ""
Write-Host "  Setter til Manuell oppstart..." -ForegroundColor Cyan

$manuell = @(
    "UsoSvc",       # Windows Update Orchestrator - manuell er tryggere enn disabled
    "WSearch"       # Windows Search - manuell hvis du ikke bruker Windows søk aktivt
)

foreach ($t in $manuell) {
    $tjeneste = Get-Service -Name $t -ErrorAction SilentlyContinue
    if ($tjeneste) {
        try {
            Set-Service -Name $t -StartupType Manual -ErrorAction Stop
            Write-Host "  ✓ Manuell: $t" -ForegroundColor Cyan
        } catch {
            Write-Host "  ! Kunne ikke endre: $t" -ForegroundColor Yellow
        }
    }
}

# ============================================================
# RESULTAT
# ============================================================
$etterAntall = (Get-Service | Where-Object {$_.Status -eq "Running"}).Count
$frigjort = $forAntall - $etterAntall

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   FERDIG!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Kjørende tjenester FØR:  $forAntall" -ForegroundColor Yellow
Write-Host "  Kjørende tjenester ETTER: $etterAntall" -ForegroundColor Green
Write-Host "  Frigjort: $frigjort tjenester" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Deaktivert:      $suksess" -ForegroundColor Green
Write-Host "  Feilet:          $feilet" -ForegroundColor Yellow
Write-Host "  Ikke installert: $ikkeInstallert" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Anbefalt: Start PC på nytt for full effekt!" -ForegroundColor Yellow
Write-Host ""
pause
