#!/usr/bin/env bash
# NetTools Pro — Linux bootstrap installer
# Tested on: Ubuntu 22.04+, Debian 12+, Fedora 39+
# Usage: bash install.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

echo "============================================"
echo "  NetTools Pro — Linux Bootstrap"
echo "============================================"
echo ""

# ── Detect distro ─────────────────────────────────────────────────────────────

if command -v dnf &>/dev/null; then
    PKG_MANAGER="dnf"
elif command -v apt &>/dev/null; then
    PKG_MANAGER="apt"
else
    echo "ERROR: No supported package manager found (dnf or apt). Aborting." >&2
    exit 1
fi

echo "[INFO] Detected package manager: $PKG_MANAGER"
echo ""

# ── System packages ───────────────────────────────────────────────────────────

echo "[1/4] Installing system packages..."

if [ "$PKG_MANAGER" = "dnf" ]; then
    sudo dnf install -y \
        python3-tkinter \
        traceroute \
        net-tools \
        arp-scan \
        iproute \
        xdg-utils \
        nmap \
        lshw \
        dmidecode

elif [ "$PKG_MANAGER" = "apt" ]; then
    sudo apt update -qq
    sudo apt install -y \
        python3-pip \
        python3-venv \
        python3-tk \
        python3-pil.imagetk \
        traceroute \
        net-tools \
        arp-scan \
        iproute2 \
        xdg-utils \
        nmap \
        lshw \
        dmidecode
fi

echo "      Done."
echo ""

# ── Virtual environment ───────────────────────────────────────────────────────

echo "[2/4] Creating virtual environment in $VENV_DIR ..."
if [ -d "$VENV_DIR" ]; then
    EXISTING_VER=$("$VENV_DIR/bin/python3" --version 2>/dev/null || echo "unknown")
    SYSTEM_VER=$(python3 --version)
    if [ "$EXISTING_VER" != "$SYSTEM_VER" ]; then
        echo "      Existing venv ($EXISTING_VER) does not match system ($SYSTEM_VER)."
        echo "      Removing and recreating it..."
        rm -rf "$VENV_DIR"
    else
        echo "      Existing venv OK ($EXISTING_VER). Keeping it."
    fi
fi
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
    echo "ERROR: $REQUIREMENTS not found. Run the script from the project folder." >&2
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
