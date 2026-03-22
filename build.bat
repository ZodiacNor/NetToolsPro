@echo off
title NetTools Pro - Build Script
echo ============================================
echo   NetTools Pro - PyInstaller Build Script
echo ============================================
echo.

:: Find Python - try multiple locations
set PYTHON=
for %%P in (python python3 py) do (
    %%P --version >nul 2>&1 && set PYTHON=%%P && goto :found_python
)
:: Try common install paths
if exist "%LOCALAPPDATA%\Python\bin\python3.exe" set PYTHON=%LOCALAPPDATA%\Python\bin\python3.exe && goto :found_python
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe && goto :found_python
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe && goto :found_python
echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
pause & exit /b 1
:found_python
echo Using Python: %PYTHON%
%PYTHON% --version

echo [1/5] Upgrading pip...
%PYTHON% -m pip install --upgrade pip --quiet
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
