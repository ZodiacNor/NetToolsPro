# ============================================================
#  SFC_Scan.ps1
#  System File Checker - Sjekker og reparerer Windows systemfiler
#  Rapport lagres til skrivebordet
#
#  BRUK: Kjør som Administrator i PowerShell
#  powershell -ExecutionPolicy Bypass -File SFC_Scan.ps1
#
#  OBS: Dette kan ta 5-20 minutter avhengig av systemet
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
$rapportFil  = "$env:USERPROFILE\Desktop\SFC_Rapport_$tidsstempel.txt"

Clear-Host
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   SFC - System File Checker" -ForegroundColor Cyan
Write-Host "   Sjekker og reparerer Windows systemfiler" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  OBS: Dette kan ta 5-20 minutter!" -ForegroundColor Yellow
Write-Host "  La terminalen stå i fred til den er ferdig." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Trykk ENTER for å starte, eller lukk vinduet for å avbryte." -ForegroundColor Gray
Read-Host

# Statusbar animasjon i bakgrunn
$rapport = @()
$rapport += "============================================================"
$rapport += "  SFC SCAN RAPPORT"
$rapport += "  Startet: $(Get-Date -Format 'dd.MM.yyyy HH:mm:ss')"
$rapport += "  Maskin:  $env:COMPUTERNAME"
$rapport += "  Bruker:  $env:USERNAME"
$rapport += "============================================================"
$rapport += ""

Write-Host ""
Write-Host "  Status: Starter SFC scan..." -ForegroundColor Green
Write-Host ""
Write-Host "  [        ] 0%" -ForegroundColor Cyan -NoNewline

# SFC kjøres og output fanges
$sfcOutput = @()
$prosent   = 0

# Start SFC prosess
$prosessInfo = New-Object System.Diagnostics.ProcessStartInfo
$prosessInfo.FileName  = "sfc.exe"
$prosessInfo.Arguments = "/scannow"
$prosessInfo.RedirectStandardOutput = $true
$prosessInfo.RedirectStandardError  = $true
$prosessInfo.UseShellExecute        = $false
$prosessInfo.CreateNoWindow         = $true

$prosess = New-Object System.Diagnostics.Process
$prosess.StartInfo = $prosessInfo
$prosess.Start() | Out-Null

# Les output linje for linje og vis fremdrift
$statusLinjer = @()
while (-not $prosess.StandardOutput.EndOfStream) {
    $linje = $prosess.StandardOutput.ReadLine()
    if ($linje) {
        $sfcOutput += $linje
        $statusLinjer += $linje

        # Finn prosentandel i output
        if ($linje -match "(\d+)\s*%") {
            $prosent = [int]$Matches[1]
            $fylt    = [math]::Floor($prosent / 10)
            $tom     = 10 - $fylt
            $bar     = "[" + ("#" * $fylt) + (" " * $tom) + "]"

            # Oppdater statuslinje
            Write-Host "`r  $bar $prosent%" -ForegroundColor Cyan -NoNewline
        }
    }
}

$prosess.WaitForExit()
$exitKode = $prosess.ExitCode

# Fullfør statusbar
Write-Host "`r  [##########] 100% - FERDIG!  " -ForegroundColor Green
Write-Host ""

# Beregn tid brukt
$sluttTid  = Get-Date
$tidBrukt  = $sluttTid - $startTid
$tidTekst  = "{0} min {1} sek" -f [int]$tidBrukt.TotalMinutes, $tidBrukt.Seconds

# Tolk resultatet
Write-Host ""
if ($sfcOutput -match "did not find any integrity violations" -or $sfcOutput -match "fant ingen integritetsproblemer") {
    $resultat = "INGEN FEIL FUNNET"
    $farge    = "Green"
    Write-Host "  RESULTAT: Ingen feil funnet - systemfilene er OK!" -ForegroundColor Green
} elseif ($sfcOutput -match "successfully repaired" -or $sfcOutput -match "ble reparert") {
    $resultat = "FEIL FUNNET OG REPARERT"
    $farge    = "Yellow"
    Write-Host "  RESULTAT: Feil ble funnet og reparert!" -ForegroundColor Yellow
    Write-Host "  Anbefaling: Start PC på nytt og kjør SFC en gang til for å bekrefte." -ForegroundColor Yellow
} elseif ($sfcOutput -match "unable to fix" -or $sfcOutput -match "kunne ikke reparere") {
    $resultat = "FEIL FUNNET - KUNNE IKKE REPARERES"
    $farge    = "Red"
    Write-Host "  RESULTAT: Feil funnet men kunne ikke repareres!" -ForegroundColor Red
    Write-Host "  Anbefaling: Kjør DISM_Repair.ps1 og deretter SFC på nytt." -ForegroundColor Red
} else {
    $resultat = "UKJENT RESULTAT - SE RAPPORT"
    $farge    = "Yellow"
    Write-Host "  RESULTAT: Ukjent - sjekk rapporten for detaljer." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Tid brukt: $tidTekst" -ForegroundColor Gray

# Bygg rapport
$rapport += "RESULTAT    : $resultat"
$rapport += "Tid brukt   : $tidTekst"
$rapport += "Exit kode   : $exitKode"
$rapport += "Startet     : $($startTid.ToString('dd.MM.yyyy HH:mm:ss'))"
$rapport += "Ferdig      : $($sluttTid.ToString('dd.MM.yyyy HH:mm:ss'))"
$rapport += ""
$rapport += "============================================================"
$rapport += "  FULL SFC OUTPUT"
$rapport += "============================================================"
$rapport += ""

# SFC logger til en Windows CBS logg - hent den også
$rapport += $sfcOutput
$rapport += ""

# Hent CBS.log for mer detaljer
$cbsLogg = "C:\Windows\Logs\CBS\CBS.log"
if (Test-Path $cbsLogg) {
    $rapport += "============================================================"
    $rapport += "  CBS.LOG - SISTE 50 LINJER (detaljert SFC logg)"
    $rapport += "============================================================"
    $rapport += ""
    Get-Content $cbsLogg -Tail 50 | ForEach-Object { $rapport += $_ }
}

$rapport += ""
$rapport += "============================================================"
$rapport += "  RAPPORT FERDIG - $(Get-Date -Format 'dd.MM.yyyy HH:mm:ss')"
$rapport += "============================================================"

# Lagre rapport
$rapport | Out-File -FilePath $rapportFil -Encoding UTF8

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   Rapport lagret til skrivebordet!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  $rapportFil" -ForegroundColor Cyan
Write-Host ""

# Åpne rapport
Start-Sleep -Seconds 1
notepad $rapportFil
