@echo off
set VERSION=1.8.1
title NetTools Pro v%VERSION% - Build Script
echo ============================================
echo   Building NetTools Pro v%VERSION%
echo ============================================
echo.

:: Find Python - try multiple strategies
set PYTHON=

:: Strategy 1: PATH lookup via py launcher (most reliable on Windows)
py -3 --version >nul 2>&1 && set PYTHON=py -3 && goto :found_python

:: Strategy 2: Try common names on PATH
for %%P in (python python3 py) do (
    %%P --version >nul 2>&1 && set PYTHON=%%P && goto :found_python
)

:: Strategy 3: Standard install locations (wildcards catch any Python 3.x version)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" set "PYTHON=%%D\python.exe" && goto :found_python
)
for /d %%D in ("%PROGRAMFILES%\Python3*") do (
    if exist "%%D\python.exe" set "PYTHON=%%D\python.exe" && goto :found_python
)
for /d %%D in ("%PROGRAMFILES(X86)%\Python3*") do (
    if exist "%%D\python.exe" set "PYTHON=%%D\python.exe" && goto :found_python
)

:: Strategy 4: Legacy LOCALAPPDATA paths (kept for backwards compat)
if exist "%LOCALAPPDATA%\Python\bin\python3.exe" (
    set "PYTHON=%LOCALAPPDATA%\Python\bin\python3.exe"
    goto :found_python
)

:: No Python found - show helpful error
echo.
echo ============================================
echo   [ERROR] Python 3.10+ was not found
echo ============================================
echo.
echo Please install Python from:
echo   https://www.python.org/downloads/
echo.
echo IMPORTANT: During installation, check the box:
echo   [x] Add python.exe to PATH
echo.
echo After installation, close this window and
echo re-run build.bat
echo ============================================
pause
exit /b 1

:found_python
echo Using Python: %PYTHON%
%PYTHON% --version

echo [1/5] Upgrading pip...
:: Retry up to 3 times - pip.exe can be file-locked during self-upgrade on Windows
set PIP_ATTEMPT=0
:pip_upgrade_retry
set /a PIP_ATTEMPT+=1
%PYTHON% -m pip install --upgrade pip --quiet
if errorlevel 1 (
    if %PIP_ATTEMPT% lss 3 (
        echo       Attempt %PIP_ATTEMPT%/3 failed, retrying in 2 seconds...
        timeout /t 2 /nobreak >nul
        goto :pip_upgrade_retry
    )
    echo       [WARN] pip upgrade failed after 3 attempts - continuing with existing pip
)
echo       Done.

echo.
echo [2/5] Installing / upgrading dependencies...
%PYTHON% -m pip install -r requirements.txt pyinstaller --upgrade --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause & exit /b 1
)
echo       Done.

echo.
echo [3/5] Cleaning previous build artifacts...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist
if exist "NetTools Pro.spec" del /q "NetTools Pro.spec"
echo       Done.

echo.
echo [4/5] Building portable executable with PyInstaller...
%PYTHON% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "NetTools Pro" ^
    --hidden-import customtkinter ^
    --hidden-import psutil ^
    --hidden-import dns ^
    --hidden-import dns.resolver ^
    --hidden-import dns.rdatatype ^
    --hidden-import dns.rdataclass ^
    --hidden-import cv2 ^
    --hidden-import pystray ^
    --collect-all customtkinter ^
    --collect-all dns ^
    --collect-all PIL ^
    --collect-all psutil ^
    --collect-all cv2 ^
    --version-file version_info.txt ^
    nettools.py

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed. See output above.
    pause & exit /b 1
)

echo.
echo [5/5] Build complete!
echo.
echo ============================================
echo   Output: dist\NetTools Pro.exe
echo   This single file is fully portable.
echo   Copy it anywhere and run - no install needed.
echo ============================================
echo.

if exist "dist\NetTools Pro.exe" (
    echo Size:
    for %%F in ("dist\NetTools Pro.exe") do echo   %%~zF bytes  ^(%%~zF / 1048576 MB approx^)
)

echo.
set /p OPEN="Open dist folder now? [Y/N]: "
if /i "%OPEN%"=="Y" explorer dist

pause
