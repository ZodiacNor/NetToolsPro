@echo off
setlocal

set "VERSION=1.8.1"
title NetTools Pro v%VERSION% - Windows Build

cd /d "%~dp0"

echo ============================================
echo   Building NetTools Pro v%VERSION%
echo ============================================
echo.

echo [1/6] Locating Python 3.10+...
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PY_CMD=python"
    ) else (
        echo [ERROR] Python 3.10+ was not found.
        echo Install Python from https://www.python.org/ and enable "Add Python to PATH".
        pause
        exit /b 1
    )
)

%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
    echo [ERROR] Python 3.10+ is required.
    echo Install Python 3.10 or newer from https://www.python.org/.
    pause
    exit /b 1
)
echo       Using: %PY_CMD%
echo       Done.
echo.

echo [2/6] Preparing virtual environment...
if not exist ".venv\Scripts\python.exe" (
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv.
        pause
        exit /b 1
    )
)
set "VENV_PY=.venv\Scripts\python.exe"
echo       Done.
echo.

echo [3/6] Installing / upgrading dependencies...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] pip upgrade failed.
    pause
    exit /b 1
)

"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency install failed.
    pause
    exit /b 1
)

"%VENV_PY%" -m pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] PyInstaller install failed.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [4/6] Checking Python syntax...
"%VENV_PY%" -m py_compile nettools.py
if errorlevel 1 (
    echo [ERROR] Python syntax check failed.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [5/6] Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo       Done.
echo.

echo [6/6] Building Windows executable with PyInstaller...
"%VENV_PY%" -m PyInstaller --clean -y "NetTools Pro.spec"
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed. See output above.
    pause
    exit /b 1
)

if not exist "dist\NetTools Pro.exe" (
    echo [ERROR] Build completed but dist\NetTools Pro.exe was not found.
    pause
    exit /b 1
)

if not exist release mkdir release
copy /Y "dist\NetTools Pro.exe" "release\NetToolsPro-windows-x64.exe" >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy Windows release asset.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build complete:
echo   dist\NetTools Pro.exe
echo   release\NetToolsPro-windows-x64.exe
echo ============================================
echo.

for %%F in ("dist\NetTools Pro.exe") do echo dist size: %%~zF bytes
for %%F in ("release\NetToolsPro-windows-x64.exe") do echo release size: %%~zF bytes

echo.
set /p OPEN="Open dist folder now? [Y/N]: "
if /i "%OPEN%"=="Y" explorer dist

pause
