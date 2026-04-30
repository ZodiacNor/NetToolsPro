@echo off
setlocal

set VERSION=1.8.1
title NetTools Pro v%VERSION% - Windows Build

cd /d "%~dp0"

echo ============================================
echo   Building NetTools Pro v%VERSION%
echo ============================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Creating Windows virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv. Install Python 3.10+ and try again.
        pause
        exit /b 1
    )
)

echo [1/5] Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate .venv.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [2/5] Installing / upgrading dependencies...
py -m pip install --upgrade pip --quiet
py -m pip install -r requirements.txt pyinstaller --upgrade --quiet
if errorlevel 1 (
    echo [ERROR] Dependency install failed.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [3/5] Checking Python syntax...
py -m py_compile nettools.py
if errorlevel 1 (
    echo [ERROR] Python syntax check failed.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [4/5] Building NetToolsPro.exe with PyInstaller...
pyinstaller --clean -y NetToolsPro.exe.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed. See output above.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [5/5] Build complete!
echo.
echo ============================================
echo   Output: dist\NetToolsPro.exe
echo   This single file is fully portable.
echo ============================================
echo.

if exist "dist\NetToolsPro.exe" (
    for %%F in ("dist\NetToolsPro.exe") do echo Size: %%~zF bytes
) else (
    echo [ERROR] dist\NetToolsPro.exe was not found.
    pause
    exit /b 1
)

echo.
set /p OPEN="Open dist folder now? [Y/N]: "
if /i "%OPEN%"=="Y" explorer dist

pause
