@echo off
setlocal
cd /d "%~dp0"
set "VENV_PY=.venv-windows\Scripts\python.exe"
if /i "%~1"=="--setup" goto setup
if not exist "%VENV_PY%" (
    echo ERROR: Run build.bat --setup first.
    exit /b 1
)
"%VENV_PY%" -B -m unittest discover -s tests -q
if errorlevel 1 exit /b 1
"%VENV_PY%" -m PyInstaller --noconfirm --clean --workpath build\windows-pyinstaller --distpath build\windows-staging NetToolsPro.exe.spec
if errorlevel 1 exit /b 1
if not exist "build\windows-staging\NetToolsPro.exe" exit /b 1
if not exist dist mkdir dist
"%VENV_PY%" -c "from pathlib import Path; import shutil,os; p=Path('dist/NetToolsPro.exe'); b=Path('build/windows-before-replace'); b.mkdir(parents=True,exist_ok=True); shutil.copy2(p,b/'NetToolsPro.exe') if p.exists() else None; shutil.copy2('build/windows-staging/NetToolsPro.exe',str(p)+'.new'); os.replace(str(p)+'.new',p)"
if errorlevel 1 exit /b 1
echo PASS: dist\NetToolsPro.exe is ready. Existing Linux and release files were preserved.
exit /b 0

:setup
if defined NETTOOLS_PYTHON (
    set "PY_CMD="%NETTOOLS_PYTHON%""
) else (
    where py >nul 2>nul
    if errorlevel 1 (set "PY_CMD=python") else (set "PY_CMD=py -3")
)
%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 exit /b 1
if not exist "%VENV_PY%" %PY_CMD% -m venv .venv-windows
if errorlevel 1 exit /b 1
"%VENV_PY%" -m pip install -r requirements-windows-build.txt
if errorlevel 1 exit /b 1
echo PASS: Windows build environment is ready.
exit /b 0
