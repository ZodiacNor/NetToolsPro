Skipper Toolkit v1.0
====================

Dette er en samlet PowerShell-verktøykasse bygget ut fra skriptene dine:
- PC_Diagnostikk
- SFC_Scan
- DISM_Repair
- WindowsDebloater / Tjenester_debloatskript

Hva toolkitet gjør
------------------
1. Lager diagnostikkrapport
2. Kjører SFC /scannow
3. Kjører DISM CheckHealth / ScanHealth / RestoreHealth
4. Har SAFE debloat-profil
5. Har AGGRESSIVE debloat-profil
6. Tar backup av tjenesteoppsett før endringer
7. Kan gjenopprette tjenester fra backup i dagens loggmappe
8. Har Dry-run modus for trygg testing

Viktige forskjeller fra de opprinnelige debloat-skriptene
---------------------------------------------------------
SAFE-profil:
- Lar DPS, WdiServiceHost, WdiSystemHost og WerSvc være i fred
- Lar WSL/Hyper-V/HNS være i fred
- Bedre egnet for gaming, koding, feilsøking og etisk hacking

AGGRESSIVE-profil:
- Kan slå av WSL, Hyper-V, HNS, WinRM og flere feilsøkingstjenester
- Brukes bare når du vet nøyaktig hvorfor du vil ha et mer slankt oppsett

Kjøring
-------
1. Åpne PowerShell som Administrator
2. Kjør:
   powershell -ExecutionPolicy Bypass -File .\SkipperToolkit.ps1

Anbefalt rekkefølge ved problem-PC
----------------------------------
1. Kjør PC-diagnostikk
2. Kjør DISM
3. Kjør SFC
4. Reboot
5. Vurder SAFE debloat hvis målet er opprydding og mindre bakgrunnsstøy

Loggfiler
---------
Toolkitet lager rapporter på skrivebordet i:
Desktop\SkipperToolkit_Logs\<tidsstempel>

Filer som lages:
- Diagnostikkrapporter
- SFC-rapporter
- DISM-rapporter
- Debloat-rapporter
- Backup av tjenester i JSON og CSV

Merknad
-------
Jeg har med vilje ikke lagt inn automatisk sletting av apper, registry-rensing eller skjulte tweaks.
Dette verktøyet skal være ryddig, lesbart og reverserbart.
