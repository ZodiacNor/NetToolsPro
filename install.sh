#!/usr/bin/env bash
# NetTools Pro — Linux bootstrap installer
# Tested on: Ubuntu 22.04+, Debian 12+
# Usage: bash install.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

# ── OS check ──────────────────────────────────────────────────────────────────

if ! command -v apt-get &>/dev/null; then
    echo "ERROR: This script requires apt (Ubuntu/Debian). Aborting." >&2
    exit 1
fi

echo "============================================"
echo "  NetTools Pro — Linux Bootstrap"
echo "============================================"
echo ""

# ── System packages ───────────────────────────────────────────────────────────

echo "[1/4] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-tk \
    python3-pil.imagetk \
    traceroute \
    net-tools \
    iproute2 \
    xdg-utils \
    netdiscover \
    nmap
echo "      Done."
echo ""

# ── Virtual environment ───────────────────────────────────────────────────────

echo "[2/4] Creating virtual environment in $VENV_DIR ..."
python3 -m venv "$VENV_DIR"
echo "      Done."
echo ""

# ── pip upgrade ───────────────────────────────────────────────────────────────

echo "[3/4] Upgrading pip..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
echo "      Done."
echo ""

# ── Python dependencies ───────────────────────────────────────────────────────

if [ ! -f "$REQUIREMENTS" ]; then
    echo "ERROR: $REQUIREMENTS not found. Run this script from the project root." >&2
    exit 1
fi

echo "[4/4] Installing Python dependencies from requirements.txt..."
"$VENV_DIR/bin/pip" install -r "$REQUIREMENTS" --quiet
echo "      Done."
echo ""

# ── Done ──────────────────────────────────────────────────────────────────────

echo "============================================"
echo "  Bootstrap complete!"
echo "============================================"
echo ""
echo "Start NetTools Pro:"
echo ""
echo "  source .venv/bin/activate"
echo "  python3 nettools.py"
echo ""
echo "Or without activating the environment:"
echo ""
echo "  .venv/bin/python3 nettools.py"
echo ""
