# ============================================================
#  DISM_Repair.ps1
#  Deployment Image Servicing and Management
#  Sjekker og reparerer Windows komponentbibliotek
#  Rapport lagres til skrivebordet
#
#  BRUK: Kjør som Administrator i PowerShell
#  powershell -ExecutionPolicy Bypass -File DISM_Repair.ps1
#
#  OBS: Dette kan ta 15-45 minutter og krever internettilkobling
#  Kjøres gjerne FØR SFC_Scan.ps1 ved systemproblemer
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
$rapportFil  = "$env:USERPROFILE\Desktop\DISM_Rapport_$tidsstempel.txt"

Clear-Host
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   DISM - Windows Image Reparasjon" -ForegroundColor Cyan
Write-Host "   Sjekker og reparerer Windows-bildet" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dette scriptet kjører 3 steg:" -ForegroundColor White
Write-Host "   Steg 1: CheckHealth  - Rask sjekk (1-2 min)" -ForegroundColor Gray
Write-Host "   Steg 2: ScanHealth   - Grundig sjekk (5-15 min)" -ForegroundColor Gray
Write-Host "   Steg 3: RestoreHealth - Reparasjon (15-45 min, krever nett)" -ForegroundColor Gray
Write-Host ""
Write-Host "  OBS: PC-en må ha internettilgang for Steg 3!" -ForegroundColor Yellow
Write-Host "  La terminalen stå i fred til den er ferdig." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Trykk ENTER for å starte, eller lukk vinduet for å avbryte." -ForegroundColor Gray
Read-Host

# Rapport header
$rapport = @()
$rapport += "============================================================"
$rapport += "  DISM REPARASJONSRAPPORT"
$rapport += "  Startet: $(Get-Date -Format 'dd.MM.yyyy HH:mm:ss')"
$rapport += "  Maskin:  $env:COMPUTERNAME"
$rapport += "  Bruker:  $env:USERNAME"
$rapport += "============================================================"
$rapport += ""

# ============================================================
# HJELPEFUNKSJON - Kjør DISM med live output
# ============================================================
function Kjør-DISM {
    param(
        [string]$Argument,
        [string]$Beskrivelse
    )

    Write-Host ""
    Write-Host "  [$Beskrivelse]" -ForegroundColor Cyan
    Write-Host "  Kommando: dism.exe $Argument" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [          ] 0%" -ForegroundColor Cyan -NoNewline

    $output   = @()
    $stegTid  = Get-Date

    $prosessInfo = New-Object System.Diagnostics.ProcessStartInfo
    $prosessInfo.FileName               = "dism.exe"
    $prosessInfo.Arguments              = $Argument
    $prosessInfo.RedirectStandardOutput = $true
    $prosessInfo.RedirectStandardError  = $true
    $prosessInfo.UseShellExecute        = $false
    $prosessInfo.CreateNoWindow         = $true

    $prosess = New-Object System.Diagnostics.Process
    $prosess.StartInfo = $prosessInfo
    $prosess.Start() | Out-Null

    while (-not $prosess.StandardOutput.EndOfStream) {
        $linje = $prosess.StandardOutput.ReadLine()
        if ($linje) {
            $output += $linje

            # Finn prosentandel
            if ($linje -match "(\d+)[,\.]?\d*\s*%") {
                $prosent = [int]$Matches[1]
                $fylt    = [math]::Floor($prosent / 10)
                $tom     = 10 - $fylt
                $bar     = "[" + ("#" * $fylt) + (" " * $tom) + "]"
                Write-Host "`r  $bar $prosent%   " -ForegroundColor Cyan -NoNewline
            }
        }
    }

    $prosess.WaitForExit()
    $exitKode  = $prosess.ExitCode
    $stegSlutt = Get-Date
    $stegTid   = $stegSlutt - $stegTid
    $tidTekst  = "{0} min {1} sek" -f [int]$stegTid.TotalMinutes, $stegTid.Seconds

    Write-Host "`r  [##########] 100% - FERDIG!   " -ForegroundColor Green
    Write-Host "  Tid brukt: $tidTekst" -ForegroundColor Gray

    return @{
        Output   = $output
        ExitKode = $exitKode
        TidBrukt = $tidTekst
    }
}

# ============================================================
# STEG 1: CheckHealth
# ============================================================
Write-Host ""
Write-Host "  ============================================" -ForegroundColor White
Write-Host "  STEG 1 av 3: CheckHealth" -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor White

$steg1 = Kjør-DISM -Argument "/Online /Cleanup-Image /CheckHealth" -Beskrivelse "Sjekker image-helse"

$rapport += "============================================================"
$rapport += "  STEG 1: CheckHealth"
$rapport += "  Tid brukt : $($steg1.TidBrukt)"
$rapport += "  Exit kode : $($steg1.ExitKode)"
$rapport += "============================================================"
$rapport += ""
$steg1.Output | ForEach-Object { $rapport += $_ }
$rapport += ""

if ($steg1.ExitKode -eq 0) {
    Write-Host "  Resultat: OK" -ForegroundColor Green
} else {
    Write-Host "  Resultat: Feil oppdaget - fortsetter med ScanHealth" -ForegroundColor Yellow
}

# ============================================================
# STEG 2: ScanHealth
# ============================================================
Write-Host ""
Write-Host "  ============================================" -ForegroundColor White
Write-Host "  STEG 2 av 3: ScanHealth" -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor White

$steg2 = Kjør-DISM -Argument "/Online /Cleanup-Image /ScanHealth" -Beskrivelse "Skanner image grundig"

$rapport += "============================================================"
$rapport += "  STEG 2: ScanHealth"
$rapport += "  Tid brukt : $($steg2.TidBrukt)"
$rapport += "  Exit kode : $($steg2.ExitKode)"
$rapport += "============================================================"
$rapport += ""
$steg2.Output | ForEach-Object { $rapport += $_ }
$rapport += ""

if ($steg2.ExitKode -eq 0) {
    Write-Host "  Resultat: OK" -ForegroundColor Green
} else {
    Write-Host "  Resultat: Feil oppdaget - fortsetter med RestoreHealth" -ForegroundColor Yellow
}

# ============================================================
# STEG 3: RestoreHealth
# ============================================================
Write-Host ""
Write-Host "  ============================================" -ForegroundColor White
Write-Host "  STEG 3 av 3: RestoreHealth" -ForegroundColor White
Write-Host "  OBS: Dette steget krever internettilgang!" -ForegroundColor Yellow
Write-Host "  ============================================" -ForegroundColor White

$steg3 = Kjør-DISM -Argument "/Online /Cleanup-Image /RestoreHealth" -Beskrivelse "Reparerer Windows-bildet"

$rapport += "============================================================"
$rapport += "  STEG 3: RestoreHealth"
$rapport += "  Tid brukt : $($steg3.TidBrukt)"
$rapport += "  Exit kode : $($steg3.ExitKode)"
$rapport += "============================================================"
$rapport += ""
$steg3.Output | ForEach-Object { $rapport += $_ }
$rapport += ""

# ============================================================
# TOTALRESULTAT
# ============================================================
$sluttTid = Get-Date
$totalTid = $sluttTid - $startTid
$totalTidTekst = "{0} min {1} sek" -f [int]$totalTid.TotalMinutes, $totalTid.Seconds

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   ALLE STEG FULLFØRT!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# Tolk sluttresultat
if ($steg3.ExitKode -eq 0) {
    Write-Host "  RESULTAT: Windows-bildet er OK / reparert!" -ForegroundColor Green
    Write-Host "  Anbefaling: Kjør SFC_Scan.ps1 for å verifisere systemfiler." -ForegroundColor Cyan
    $totalResultat = "SUKSESS - Windows-bildet OK / reparert"
} elseif ($steg3.ExitKode -eq 87) {
    Write-Host "  RESULTAT: Ugyldig parameter - sjekk rapporten." -ForegroundColor Yellow
    $totalResultat = "ADVARSEL - Ugyldig parameter (kode 87)"
} elseif ($steg3.ExitKode -eq 1392) {
    Write-Host "  RESULTAT: Filen eller katalogen er ødelagt." -ForegroundColor Red
    Write-Host "  Anbefaling: Vurder reinstallering av Windows." -ForegroundColor Red
    $totalResultat = "FEIL - Ødelagt fil/katalog (kode 1392)"
} else {
    Write-Host "  RESULTAT: Exit kode $($steg3.ExitKode) - sjekk rapporten." -ForegroundColor Yellow
    $totalResultat = "UKJENT - Exit kode $($steg3.ExitKode)"
}

Write-Host ""
Write-Host "  Total tid brukt: $totalTidTekst" -ForegroundColor Gray

# Oppsummering i rapport
$rapport += "============================================================"
$rapport += "  OPPSUMMERING"
$rapport += "============================================================"
$rapport += ""
$rapport += "Totalresultat  : $totalResultat"
$rapport += "Total tid      : $totalTidTekst"
$rapport += "Startet        : $($startTid.ToString('dd.MM.yyyy HH:mm:ss'))"
$rapport += "Ferdig         : $($sluttTid.ToString('dd.MM.yyyy HH:mm:ss'))"
$rapport += ""
$rapport += "Steg 1 CheckHealth  : Exit $($steg1.ExitKode) - $($steg1.TidBrukt)"
$rapport += "Steg 2 ScanHealth   : Exit $($steg2.ExitKode) - $($steg2.TidBrukt)"
$rapport += "Steg 3 RestoreHealth: Exit $($steg3.ExitKode) - $($steg3.TidBrukt)"
$rapport += ""

# Hent DISM logg
$dismLogg = "C:\Windows\Logs\DISM\dism.log"
if (Test-Path $dismLogg) {
    $rapport += "============================================================"
    $rapport += "  DISM.LOG - SISTE 50 LINJER"
    $rapport += "============================================================"
    $rapport += ""
    Get-Content $dismLogg -Tail 50 | ForEach-Object { $rapport += $_ }
}

$rapport += ""
$rapport += "============================================================"
$rapport += "  RAPPORT FERDIG - $($sluttTid.ToString('dd.MM.yyyy HH:mm:ss'))"
$rapport += "============================================================"

# Lagre rapport
$rapport | Out-File -FilePath $rapportFil -Encoding UTF8

Write-Host ""
Write-Host "  Rapport lagret til:" -ForegroundColor Yellow
Write-Host "  $rapportFil" -ForegroundColor Cyan
Write-Host ""

Start-Sleep -Seconds 1
notepad $rapportFil
