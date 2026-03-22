# ============================================================
#  PC_Diagnostikk.ps1 v2.0
#  Komplett systemdiagnostikk - av Viggo for Bengt Simon
#  Lagrer rapport til skrivebordet
#
#  BRUK: Kjør som Administrator i PowerShell
#  powershell -ExecutionPolicy Bypass -File PC_Diagnostikk.ps1
# ============================================================

# Krever Administrator
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")) {
    Write-Host ""
    Write-Host "  FEIL: Kjør PowerShell som Administrator!" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

# Tidsstempel og filnavn
$startTid    = Get-Date
$tidsstempel = $startTid.ToString("yyyy-MM-dd_HH-mm-ss")
$rapportFil  = "$env:USERPROFILE\Desktop\PC_Diagnostikk_$tidsstempel.txt"
$dato        = $startTid.ToString("dd.MM.yyyy HH:mm:ss")

Clear-Host
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   PC Diagnostikk v2.0 - Samler data..." -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# HJELPEFUNKSJON - Skriv seksjon
# ============================================================
function Seksjon {
    param([string]$Tittel)
    $linje = "=" * 60
    return "`r`n$linje`r`n  $Tittel`r`n$linje`r`n"
}

# ============================================================
# START RAPPORT
# ============================================================
$rapport = @()
$rapport += "============================================================"
$rapport += "  PC DIAGNOSTIKKRAPPORT v2.0"
$rapport += "  Generert: $($startTid.ToString('dd.MM.yyyy HH:mm:ss'))"
$rapport += "  Av: PC_Diagnostikk.ps1"
$rapport += "============================================================"

# ============================================================
# 1. SYSTEMINFORMASJON
# ============================================================
Write-Host "  [1/11] Samler systeminformasjon..." -ForegroundColor Yellow

$rapport += Seksjon "1. SYSTEMINFORMASJON"

try {
    $os         = Get-CimInstance Win32_OperatingSystem
    $cs         = Get-CimInstance Win32_ComputerSystem
    $bios       = Get-CimInstance Win32_BIOS
    $cpu        = Get-CimInstance Win32_Processor
    $board      = Get-CimInstance Win32_BaseBoard
    $oppetid    = (Get-Date) - $os.LastBootUpTime
    $oppetidTxt = "{0} dager, {1} timer, {2} minutter" -f [int]$oppetid.TotalDays, $oppetid.Hours, $oppetid.Minutes

    $rapport += "Datamaskinnavn    : $($cs.Name)"
    $rapport += "Bruker (innlogget): $($env:USERNAME)"
    $rapport += ""
    $rapport += "--- Operativsystem ---"
    $rapport += "OS                : $($os.Caption)"
    $rapport += "Versjon           : $($os.Version)"
    $rapport += "Build             : $($os.BuildNumber)"
    $rapport += "Arkitektur        : $($os.OSArchitecture)"
    $rapport += "Installert        : $($os.InstallDate)"
    $rapport += "Siste oppstart    : $($os.LastBootUpTime)"
    $rapport += "Oppetid           : $oppetidTxt"
    $rapport += ""
    $rapport += "--- Maskinvare ---"
    $rapport += "Produsent         : $($cs.Manufacturer)"
    $rapport += "Modell            : $($cs.Model)"
    $rapport += "Hovedkort         : $($board.Manufacturer) $($board.Product)"
    $rapport += "BIOS versjon      : $($bios.SMBIOSBIOSVersion)"
    $rapport += "BIOS dato         : $($bios.ReleaseDate)"
    $rapport += ""
    $rapport += "--- Prosessor ---"
    $rapport += "CPU               : $($cpu.Name)"
    $rapport += "Kjerner           : $($cpu.NumberOfCores)"
    $rapport += "Logiske prosessorer: $($cpu.NumberOfLogicalProcessors)"
    $rapport += "Maks klokkefrekvens: $($cpu.MaxClockSpeed) MHz"
    $rapport += "Arkitektur        : $($cpu.AddressWidth)-bit"

} catch {
    $rapport += "FEIL ved innhenting av systeminformasjon: $($_.Exception.Message)"
}

# ============================================================
# 2. OPPSTARTSTID
# ============================================================
Write-Host "  [2/11] Samler oppstartstid..." -ForegroundColor Yellow

$rapport += Seksjon "2. OPPSTARTSTID"

try {
    $bootEvents = Get-WinEvent -LogName "Microsoft-Windows-Diagnostics-Performance/Operational" -ErrorAction SilentlyContinue |
                  Where-Object { $_.Id -eq 100 } | Select-Object -First 5

    if ($bootEvents) {
        $rapport += "{0,-25} {1}" -f "Tidspunkt", "Boot tid"
        $rapport += "-" * 45
        foreach ($e in $bootEvents) {
            $xml     = [xml]$e.ToXml()
            $bootMs  = $xml.Event.EventData.Data | Where-Object { $_.Name -eq "BootTime" } | Select-Object -ExpandProperty '#text'
            $bootSek = if ($bootMs) { "$([math]::Round([int]$bootMs / 1000, 1)) sekunder" } else { "Ukjent" }
            $rapport += "{0,-25} {1}" -f $e.TimeCreated.ToString("dd.MM.yyyy HH:mm"), $bootSek
        }
    } else {
        $rapport += "Siste oppstart: $((Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('dd.MM.yyyy HH:mm:ss'))"
        $rapport += "Detaljert boot-analyse ikke tilgjengelig."
    }

    $rapport += ""
    $rapport += "--- Tjenester med forsinket autostart ---"
    Get-Service | Where-Object { $_.StartType -eq "AutomaticDelayedStart" } | Sort-Object DisplayName | ForEach-Object {
        $rapport += "  $($_.DisplayName) - Status: $($_.Status)"
    }

} catch {
    $rapport += "FEIL ved innhenting av oppstartstid: $($_.Exception.Message)"
}

# ============================================================
# 3. TEMPERATUR
# ============================================================
Write-Host "  [3/11] Samler temperaturdata..." -ForegroundColor Yellow

$rapport += Seksjon "3. TEMPERATUR"

try {
    $temps = Get-CimInstance -Namespace "root/wmi" -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue

    if ($temps) {
        $rapport += "--- Termiske soner (ACPI) ---"
        foreach ($t in $temps) {
            $celsius = [math]::Round(($t.CurrentTemperature / 10) - 273.15, 1)
            $advarsel = if ($celsius -gt 90) { " << KRITISK!" } elseif ($celsius -gt 75) { " << HØYT" } else { "" }
            $rapport += "Sone: $($t.InstanceName.PadRight(45)) Temp: $celsius °C$advarsel"
        }
    } else {
        $rapport += "ACPI temperaturdata ikke tilgjengelig via WMI."
        $rapport += "Anbefalt verktøy for temperaturer:"
        $rapport += "  - HWiNFO64 : https://www.hwinfo.com"
        $rapport += "  - Core Temp: CPU-temperaturer"
        $rapport += "  - GPU-Z    : GPU-temperaturer"
    }

    $rapport += ""
    $rapport += "--- CPU belastning (indikator) ---"
    $load1 = (Get-CimInstance Win32_Processor).LoadPercentage
    Start-Sleep -Seconds 1
    $load2 = (Get-CimInstance Win32_Processor).LoadPercentage
    $snitt = [math]::Round(($load1 + $load2) / 2, 1)
    $rapport += "CPU belastning: $snitt%"
    if ($snitt -gt 80) { $rapport += "ADVARSEL: Høy CPU-belastning!" }

} catch {
    $rapport += "FEIL ved innhenting av temperaturdata: $($_.Exception.Message)"
}

# ============================================================
# 4. BATTERI / STRØM
# ============================================================
Write-Host "  [4/11] Samler batteri og strøminformasjon..." -ForegroundColor Yellow

$rapport += Seksjon "4. BATTERI / STRØM"

try {
    $batteri = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue

    if ($batteri) {
        $statusKoder = @{
            1="Annen"; 2="Ukjent"; 3="Fullt ladet"; 4="Lavt"; 5="Kritisk lavt";
            6="Lader"; 7="Lader og høyt"; 8="Lader og lavt"; 9="Lader og kritisk";
            10="Udefinert"; 11="Delvis ladet"
        }
        foreach ($b in $batteri) {
            $statusTekst = if ($statusKoder[$b.BatteryStatus]) { $statusKoder[$b.BatteryStatus] } else { "Ukjent" }
            $rapport += "Navn              : $($b.Name)"
            $rapport += "Ladenivå          : $($b.EstimatedChargeRemaining)%"
            $rapport += "Status            : $statusTekst"
            $rapport += "Estimert tid igjen: $($b.EstimatedRunTime) minutter"
            if ($b.EstimatedChargeRemaining -lt 20) { $rapport += "ADVARSEL: Lavt batteri!" }
            if ($b.DesignCapacity -and $b.FullChargeCapacity) {
                $helse = [math]::Round(($b.FullChargeCapacity / $b.DesignCapacity) * 100, 1)
                $rapport += "Batterihelse      : $helse%"
                if ($helse -lt 80) { $rapport += "ADVARSEL: Batterihelse under 80% - vurder bytte!" }
            }
            $rapport += ""
        }
    } else {
        $rapport += "Ingen batteri funnet - stasjonær PC."
    }

    $rapport += "--- Aktiv strømplan ---"
    powercfg /getactivescheme 2>$null | ForEach-Object { $rapport += $_ }
    $rapport += ""
    $rapport += "--- Alle strømplaner ---"
    powercfg /list 2>$null | ForEach-Object { $rapport += $_ }

} catch {
    $rapport += "FEIL ved innhenting av batteriinformasjon: $($_.Exception.Message)"
}

# ============================================================
# 5. RAM / MINNE
# ============================================================
Write-Host "  [5/11] Samler RAM-informasjon..." -ForegroundColor Yellow

$rapport += Seksjon "5. RAM / MINNE"

try {
    $os          = Get-CimInstance Win32_OperatingSystem
    $totalRAM    = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $ledigRAM    = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $brukRAM     = [math]::Round($totalRAM - $ledigRAM, 2)
    $brukProsent = [math]::Round(($brukRAM / $totalRAM) * 100, 1)

    $rapport += "Total RAM         : $totalRAM GB"
    $rapport += "I bruk            : $brukRAM GB ($brukProsent%)"
    $rapport += "Ledig             : $ledigRAM GB"
    if ($brukProsent -gt 90) { $rapport += "ADVARSEL: Kritisk høyt RAM-bruk!" }
    elseif ($brukProsent -gt 75) { $rapport += "INFO: Høyt RAM-bruk" }

    $rapport += ""
    $rapport += "--- RAM-moduler ---"
    Get-CimInstance Win32_PhysicalMemory | ForEach-Object {
        $størrelse = [math]::Round($_.Capacity / 1GB, 0)
        $rapport += "Spor: $($_.DeviceLocator) | $størrelse GB | $($_.Speed) MHz | $($_.Manufacturer) | $($_.PartNumber)"
    }

    $rapport += ""
    $rapport += "--- Topp 15 prosesser etter RAM-bruk ---"
    $rapport += "{0,-40} {1,10} {2,10}" -f "Prosess", "RAM (MB)", "PID"
    $rapport += "-" * 65
    Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 15 | ForEach-Object {
        $rapport += "{0,-40} {1,10} {2,10}" -f $_.Name, [math]::Round($_.WorkingSet64 / 1MB, 1), $_.Id
    }

} catch {
    $rapport += "FEIL ved innhenting av RAM-informasjon: $($_.Exception.Message)"
}

# ============================================================
# 6. CPU-BRUK
# ============================================================
Write-Host "  [6/11] Samler CPU-informasjon..." -ForegroundColor Yellow
Write-Host "         Maler idle CPU (venter 5 sek)..." -ForegroundColor DarkGray

$rapport += Seksjon "6. CPU-BRUK"

try {
    # --- IDLE-MÅLING via Performance Counter ---
    # Kalibrerer først, deretter måler over 5 sekunder for reelt snitt
    $counter = New-Object System.Diagnostics.PerformanceCounter("Processor", "% Processor Time", "_Total")
    $counter.NextValue() | Out-Null   # Første lesing kalibrerer telleren
    Start-Sleep -Seconds 5            # La systemet roe seg ned
    $idleCPU = [math]::Round($counter.NextValue(), 1)

    # --- STRESS-TEST via Win32_Processor ---
    # Denne målingen trigges mens skriptet selv kjører - viser CPU under last
    $stressCPU1 = (Get-CimInstance Win32_Processor).LoadPercentage
    # Generer litt CPU-last for å simulere stress
    $tall = 1; 1..500000 | ForEach-Object { $tall = $tall * $_ % 9999 }
    $stressCPU2 = (Get-CimInstance Win32_Processor).LoadPercentage
    $stressCPU  = [math]::Round(($stressCPU1 + $stressCPU2) / 2, 1)

    # Rapport
    $rapport += "--- CPU-bruk målt på to måter ---"
    $rapport += ""
    $rapport += "IDLE-MÅLING (Performance Counter, 5 sek snitt):"
    $rapport += "  CPU idle-bruk     : $idleCPU%"
    if ($idleCPU -gt 30) { $rapport += "  ADVARSEL: Høy idle-bruk - noe kjører i bakgrunnen!" }
    elseif ($idleCPU -gt 15) { $rapport += "  INFO: Moderat idle-bruk" }
    else { $rapport += "  Status: Normal idle-bruk" }

    $rapport += ""
    $rapport += "STRESS-TEST (Win32 under skriptkjøring):"
    $rapport += "  CPU under last    : $stressCPU%"
    if ($stressCPU -gt 90) { $rapport += "  Status: Høy belastning - CPU jobber hardt" }
    elseif ($stressCPU -gt 60) { $rapport += "  Status: Moderat belastning" }
    else { $rapport += "  Status: Lav belastning selv under stress" }

    $rapport += ""
    $rapport += "--- Topp 15 prosesser etter akkumulert CPU-tid ---"
    $rapport += "(NB: Viser total CPU-tid siden oppstart, ikke øyeblikkelig bruk)"
    $rapport += "{0,-40} {1,12} {2,10} {3,10}" -f "Prosess", "CPU-tid (sek)", "RAM (MB)", "PID"
    $rapport += "-" * 78
    Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 | ForEach-Object {
        $rapport += "{0,-40} {1,12} {2,10} {3,10}" -f $_.Name, [math]::Round($_.CPU, 1), [math]::Round($_.WorkingSet64 / 1MB, 1), $_.Id
    }

    $rapport += ""
    $rapport += "--- Kjørende tjenester ---"
    $rapport += "{0,-45} {1}" -f "Tjenestenavn", "Visningsnavn"
    $rapport += "-" * 85
    Get-Service | Where-Object {$_.Status -eq "Running"} | Sort-Object DisplayName | ForEach-Object {
        $rapport += "{0,-45} {1}" -f $_.Name, $_.DisplayName
    }

} catch {
    $rapport += "FEIL ved innhenting av CPU-informasjon: $($_.Exception.Message)"
}

# ============================================================
# 7. DISK
# ============================================================
Write-Host "  [7/11] Samler diskinformasjon..." -ForegroundColor Yellow

$rapport += Seksjon "7. DISK"

try {
    $rapport += "--- Diskstasjoner ---"
    $rapport += "{0,-5} {1,15} {2,15} {3,15} {4,10}" -f "Disk", "Total (GB)", "Brukt (GB)", "Ledig (GB)", "Ledig %"
    $rapport += "-" * 65
    Get-PSDrive -PSProvider FileSystem | Where-Object {$_.Used -gt 0} | ForEach-Object {
        $total    = [math]::Round(($_.Used + $_.Free) / 1GB, 2)
        $brukt    = [math]::Round($_.Used / 1GB, 2)
        $ledig    = [math]::Round($_.Free / 1GB, 2)
        $prosent  = [math]::Round(($ledig / $total) * 100, 1)
        $advarsel = if ($prosent -lt 10) { " << KRITISK!" } elseif ($prosent -lt 20) { " << Lite plass" } else { "" }
        $rapport += "{0,-5} {1,15} {2,15} {3,15} {4,10}{5}" -f $_.Name, $total, $brukt, $ledig, "$prosent%", $advarsel
    }

    $rapport += ""
    $rapport += "--- Fysiske disker ---"
    Get-CimInstance Win32_DiskDrive | ForEach-Object {
        $rapport += "Disk     : $($_.Caption)"
        $rapport += "Type     : $($_.MediaType)"
        $rapport += "Størrelse: $([math]::Round($_.Size / 1GB, 0)) GB"
        $rapport += "Status   : $($_.Status)"
        $rapport += ""
    }

} catch {
    $rapport += "FEIL ved innhenting av diskinformasjon: $($_.Exception.Message)"
}

# ============================================================
# 8. GPU
# ============================================================
Write-Host "  [8/11] Samler GPU-informasjon..." -ForegroundColor Yellow

$rapport += Seksjon "8. GRAFIKKORT / GPU"

try {
    Get-CimInstance Win32_VideoController | ForEach-Object {
        $vram = if ($_.AdapterRAM) { [math]::Round($_.AdapterRAM / 1GB, 1) } else { "Ukjent" }
        $rapport += "GPU               : $($_.Caption)"
        $rapport += "Driver versjon    : $($_.DriverVersion)"
        $rapport += "Driver dato       : $($_.DriverDate)"
        $rapport += "VRAM              : $vram GB"
        $rapport += "Oppløsning        : $($_.CurrentHorizontalResolution) x $($_.CurrentVerticalResolution)"
        $rapport += "Oppdateringsfrekvens: $($_.CurrentRefreshRate) Hz"
        $rapport += "Status            : $($_.Status)"
        $rapport += ""
    }
} catch {
    $rapport += "FEIL ved innhenting av GPU-informasjon: $($_.Exception.Message)"
}

# ============================================================
# 9. NETTVERK
# ============================================================
Write-Host "  [9/11] Samler nettverksinformasjon..." -ForegroundColor Yellow

$rapport += Seksjon "9. NETTVERK"

try {
    $rapport += "--- Nettverkskort ---"
    Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object {$_.IPEnabled} | ForEach-Object {
        $rapport += "Adapter           : $($_.Description)"
        $rapport += "IP-adresse        : $($_.IPAddress -join ', ')"
        $rapport += "Subnettmaske      : $($_.IPSubnet -join ', ')"
        $rapport += "Standard gateway  : $($_.DefaultIPGateway -join ', ')"
        $rapport += "DNS-servere       : $($_.DNSServerSearchOrder -join ', ')"
        $rapport += "DHCP aktivert     : $($_.DHCPEnabled)"
        $rapport += "MAC-adresse       : $($_.MACAddress)"
        $rapport += ""
    }

    $rapport += "--- Ping-tester ---"
    $gateway = (Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object {$_.DefaultIPGateway}).DefaultIPGateway | Select-Object -First 1
    $pingMål = @(
        @{Navn="Standard gateway"; Adresse=$gateway},
        @{Navn="Google DNS";       Adresse="8.8.8.8"},
        @{Navn="Cloudflare DNS";   Adresse="1.1.1.1"},
        @{Navn="Google.com";       Adresse="google.com"}
    )
    foreach ($mål in $pingMål) {
        if ([string]::IsNullOrWhiteSpace($mål.Adresse)) {
            $rapport += "$($mål.Navn.PadRight(25)): Ingen gateway funnet"
            continue
        }
        try {
            $ping     = Test-Connection -ComputerName $mål.Adresse -Count 2 -ErrorAction Stop
            $snitt    = [math]::Round(($ping | Measure-Object ResponseTime -Average).Average, 0)
            $advarsel = if ($snitt -gt 100) { " << Høy latens!" } else { "" }
            $rapport += "$($mål.Navn.PadRight(25)): OK ($snitt ms) -> $($mål.Adresse)$advarsel"
        } catch {
            $rapport += "$($mål.Navn.PadRight(25)): FEILET -> $($mål.Adresse)"
        }
    }

    $rapport += ""
    $rapport += "--- DNS-oppslag test ---"
    foreach ($d in @("google.com", "microsoft.com", "vg.no")) {
        try {
            $res = Resolve-DnsName $d -ErrorAction Stop | Select-Object -First 1
            $rapport += "$($d.PadRight(25)): OK -> $($res.IPAddress)"
        } catch {
            $rapport += "$($d.PadRight(25)): FEILET"
        }
    }

    $rapport += ""
    $rapport += "--- Aktive nettverkstilkoblinger (ESTABLISHED) ---"
    $rapport += "{0,-25} {1,-25} {2,-10} {3}" -f "Lokal adresse", "Ekstern adresse", "Status", "Prosess"
    $rapport += "-" * 85
    Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | Select-Object -First 20 | ForEach-Object {
        $prosess = (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).Name
        $rapport += "{0,-25} {1,-25} {2,-10} {3}" -f "$($_.LocalAddress):$($_.LocalPort)", "$($_.RemoteAddress):$($_.RemotePort)", $_.State, $prosess
    }

    $rapport += ""
    $rapport += "--- WiFi informasjon ---"
    $wifi = netsh wlan show interfaces 2>$null
    if ($wifi) { $wifi | ForEach-Object { $rapport += $_ } }
    else { $rapport += "Ingen aktiv WiFi-tilkobling funnet" }

} catch {
    $rapport += "FEIL ved innhenting av nettverksinformasjon: $($_.Exception.Message)"
}

# ============================================================
# 10. WINDOWS UPDATE
# ============================================================
Write-Host "  [10/11] Samler Windows Update status..." -ForegroundColor Yellow

$rapport += Seksjon "10. WINDOWS UPDATE STATUS"

try {
    $rapport += "--- Siste 10 installerte oppdateringer ---"
    $rapport += "{0,-15} {1,-20} {2}" -f "Dato", "KB-nummer", "Beskrivelse"
    $rapport += "-" * 70
    Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 | ForEach-Object {
        $dato = if ($_.InstalledOn) { $_.InstalledOn.ToString("dd.MM.yyyy") } else { "Ukjent" }
        $rapport += "{0,-15} {1,-20} {2}" -f $dato, $_.HotFixID, $_.Description
    }

    $rapport += ""
    $rapport += "--- Ventende oppdateringer ---"
    try {
        $session    = New-Object -ComObject Microsoft.Update.Session
        $søker      = $session.CreateUpdateSearcher()
        $resultat   = $søker.Search("IsInstalled=0 and IsHidden=0")
        if ($resultat.Updates.Count -gt 0) {
            $rapport += "ADVARSEL: $($resultat.Updates.Count) oppdateringer venter!"
            foreach ($u in $resultat.Updates) { $rapport += "  - $($u.Title)" }
        } else {
            $rapport += "Ingen ventende oppdateringer - Windows er oppdatert!"
        }
    } catch {
        $rapport += "Kunne ikke sjekke automatisk - sjekk manuelt via Innstillinger -> Windows Update"
    }

} catch {
    $rapport += "FEIL ved innhenting av Windows Update status: $($_.Exception.Message)"
}

# ============================================================
# 11. AUTOSTART + INSTALLERTE PROGRAMMER
# ============================================================
Write-Host "  [11/11] Samler autostart og installerte programmer..." -ForegroundColor Yellow

$rapport += Seksjon "11. AUTOSTART-PROGRAMMER"

try {
    $rapport += "--- Registry autostart ---"
    $rapport += "{0,-50} {1}" -f "Navn", "Plassering"
    $rapport += "-" * 80

    $hkcu = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
    if ($hkcu) {
        $hkcu.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | ForEach-Object {
            $rapport += "{0,-50} {1}" -f $_.Name, "HKCU\Run"
        }
    }

    $hklm = Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
    if ($hklm) {
        $hklm.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | ForEach-Object {
            $rapport += "{0,-50} {1}" -f $_.Name, "HKLM\Run"
        }
    }

    foreach ($mappe in @("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup", "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup")) {
        if (Test-Path $mappe) {
            Get-ChildItem $mappe -ErrorAction SilentlyContinue | ForEach-Object {
                $rapport += "{0,-50} {1}" -f $_.Name, "Startup-mappe"
            }
        }
    }

    $rapport += ""
    $rapport += "--- Aktive planlagte oppgaver (ikke Microsoft) ---"
    $rapport += "{0,-50} {1,-20} {2}" -f "Oppgave", "Status", "Siste kjøring"
    $rapport += "-" * 90
    Get-ScheduledTask -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Ready" -and $_.TaskPath -notlike "\Microsoft*" } |
        Select-Object -First 20 | ForEach-Object {
            $info      = $_ | Get-ScheduledTaskInfo -ErrorAction SilentlyContinue
            $sistKjørt = if ($info.LastRunTime -and $info.LastRunTime.Year -gt 2000) { $info.LastRunTime.ToString("dd.MM.yyyy HH:mm") } else { "Aldri" }
            $rapport   += "{0,-50} {1,-20} {2}" -f $_.TaskName, $_.State, $sistKjørt
        }

} catch {
    $rapport += "FEIL ved innhenting av autostart: $($_.Exception.Message)"
}

$rapport += Seksjon "12. INSTALLERTE PROGRAMMER"

try {
    $programmer = Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* -ErrorAction SilentlyContinue |
                  Where-Object { $_.DisplayName } |
                  Select-Object DisplayName, DisplayVersion, Publisher |
                  Sort-Object DisplayName

    $rapport += "{0,-50} {1,-20} {2}" -f "Program", "Versjon", "Utgiver"
    $rapport += "-" * 90
    foreach ($p in $programmer) {
        $rapport += "{0,-50} {1,-20} {2}" -f $p.DisplayName, $p.DisplayVersion, $p.Publisher
    }
} catch {
    $rapport += "FEIL ved innhenting av programmer: $($_.Exception.Message)"
}

$rapport += Seksjon "13. EVENT LOG - FEIL OG ADVARSLER (siste 24 timer)"

try {
    $kritiske = Get-EventLog -LogName System -EntryType Error, Warning -After (Get-Date).AddHours(-24) -ErrorAction SilentlyContinue | Select-Object -First 30
    if ($kritiske) {
        $rapport += "{0,-20} {1,-10} {2,-20} {3}" -f "Tidspunkt", "Type", "Kilde", "Melding"
        $rapport += "-" * 90
        foreach ($e in $kritiske) {
            $melding = ($e.Message -replace "`r`n"," " -replace "`n"," ")
            if ($melding.Length -gt 80) { $melding = $melding.Substring(0,80) + "..." }
            $rapport += "{0,-20} {1,-10} {2,-20} {3}" -f $e.TimeGenerated.ToString("dd.MM.yyyy HH:mm"), $e.EntryType, $e.Source, $melding
        }
    } else {
        $rapport += "Ingen feil eller advarsler siste 24 timer!"
    }
} catch {
    $rapport += "FEIL ved innhenting av Event Log: $($_.Exception.Message)"
}

# ============================================================
# AVSLUTT OG LAGRE
# ============================================================
$sluttTid = Get-Date
$tidBrukt = $sluttTid - $startTid
$tidTekst = "{0} min {1} sek" -f [int]$tidBrukt.TotalMinutes, $tidBrukt.Seconds

$rapport += ""
$rapport += "============================================================"
$rapport += "  RAPPORT FERDIG"
$rapport += "  Startet  : $($startTid.ToString('dd.MM.yyyy HH:mm:ss'))"
$rapport += "  Ferdig   : $($sluttTid.ToString('dd.MM.yyyy HH:mm:ss'))"
$rapport += "  Tid brukt: $tidTekst"
$rapport += "  PC_Diagnostikk.ps1 v2.1"
$rapport += "============================================================"

$rapport | Out-File -FilePath $rapportFil -Encoding UTF8

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   FERDIG! (v2.1)" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Rapport lagret til:" -ForegroundColor Yellow
Write-Host "  $rapportFil" -ForegroundColor Cyan
Write-Host ""
Start-Sleep -Seconds 1
notepad $rapportFil
