#!/usr/bin/env bash
# Build with Windows CPython in a project-owned Wine prefix.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
cd -- "$project_dir"
export WINEPREFIX="$project_dir/build/windows-wine"
export WINEARCH=win64 WINEDEBUG=-all
export WINEDLLOVERRIDES='winemenubuilder.exe,mscoree,mshtml=d'
export XDG_CONFIG_HOME="$project_dir/build/windows-xdg/config"
export XDG_CACHE_HOME="$project_dir/build/windows-xdg/cache"
export XDG_DATA_HOME="$project_dir/build/windows-xdg/data"
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
mkdir -p "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME"
if [[ ! -f "$WINEPREFIX/drive_c/Python313/python.exe" ]]; then
    echo 'ERROR: Prepare project build/windows-wine with Windows CPython at C:\Python313 first.'
    exit 1
fi
if [[ ! -e "$WINEPREFIX/dosdevices/n:" && ! -L "$WINEPREFIX/dosdevices/n:" ]]; then
    ln -s "$project_dir" "$WINEPREFIX/dosdevices/n:"
fi
if [[ "$(readlink -f "$WINEPREFIX/dosdevices/n:")" != "$project_dir" ]]; then
    echo 'ERROR: Wine drive N: points elsewhere.'
    exit 1
fi
case "${1:-build}" in
    setup) NETTOOLS_PYTHON='C:\Python313\python.exe' wine cmd /d /c 'N:\build.bat --setup' ;;
    test) wine 'N:\.venv-windows\Scripts\python.exe' -B -m unittest discover -s tests -q ;;
    gui) wine 'N:\.venv-windows\Scripts\python.exe' -B tests/gui_workspace.py --full ;;
    build) wine cmd /d /c 'N:\build.bat' ;;
    *) echo 'Usage: bash build-windows-wine.sh [setup|test|gui|build]'; exit 2 ;;
esac
