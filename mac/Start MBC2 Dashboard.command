#!/bin/bash

# MBC2 Dashboard — Mac Launcher
cd "$(dirname "$0")"

echo ""
echo "  ============================================"
echo "   MBC2 DASHBOARD - mic-LABO Motor Boot Camp 2"
echo "  ============================================"
echo ""

# Locate server.py (packaged layout: app/ beside this launcher)
if [ -f "app/server.py" ]; then
    SERVER="app/server.py"
elif [ -f "../server.py" ]; then
    SERVER="../server.py"
else
    echo "  ERROR: cannot find server.py."
    echo "  Expected: app/server.py beside this launcher."
    read -p "  Press Enter to close..."
    exit 1
fi

# Try Python 3
if command -v python3 &>/dev/null; then
    VER=$(python3 --version 2>&1)
    if [[ $VER == Python\ 3* ]]; then
        echo "  Starting MBC2 Dashboard..."
        echo ""
        python3 "$SERVER"
        exit 0
    fi
fi

# Try python alias
if command -v python &>/dev/null; then
    VER=$(python --version 2>&1)
    if [[ $VER == Python\ 3* ]]; then
        echo "  Starting MBC2 Dashboard..."
        python "$SERVER"
        exit 0
    fi
fi

# No Python 3 found
echo "  Python 3 is not installed on this Mac."
echo ""
echo "  To install Python 3, choose one of:"
echo ""
echo "  Option 1 (Recommended):"
echo "    Go to https://www.python.org/downloads/"
echo "    Download and run the macOS installer."
echo ""
echo "  Option 2 (Homebrew):"
echo "    Open Terminal and run: brew install python3"
echo ""
echo "  Option 3 (Xcode Command Line Tools):"
echo "    Open Terminal and run: xcode-select --install"
echo ""
read -p "  Press Enter to close..."
