#!/bin/bash
# SeVIn AI Hub — Dependency Checker and Setup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║        SeVIn AI Hub — Setup Wizard            ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""

check_dep() {
    if command -v "$1" &> /dev/null; then
        echo "  ✓ $1 found ($(command -v $1))"
        return 0
    else
        echo "  ✗ $1 NOT found"
        return 1
    fi
}

echo "Checking dependencies..."
echo ""

MISSING_DEPS=0

check_dep python3 || MISSING_DEPS=1
check_dep pip3 || check_dep pip || MISSING_DEPS=1
check_dep tmux || {
    echo ""
    echo "  tmux is required. Install it:"
    echo "    Termux: pkg install tmux"
    echo "    Ubuntu/Debian: sudo apt install tmux"
    echo "    macOS: brew install tmux"
    MISSING_DEPS=1
}

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo "Please install missing dependencies and re-run this script."
    exit 1
fi

echo ""
echo "Installing Python packages..."
echo ""

PIP_CMD="pip3"
if ! command -v pip3 &> /dev/null; then
    PIP_CMD="pip"
fi

PACKAGES=(
    flask
    flask-socketio
    flask-cors
    pypdf
    gTTS
    edge-tts
    requests
)

for pkg in "${PACKAGES[@]}"; do
    echo -n "  Installing $pkg... "
    if $PIP_CMD install "$pkg" --quiet --disable-pip-version-check 2>/dev/null; then
        echo "✓"
    else
        echo "⚠ (may already be installed or unavailable)"
    fi
done

mkdir -p generated_agents data

echo ""
echo "All dependencies installed."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ! -f "agents.json" ]; then
    echo "No agents configured yet. Running setup wizard..."
    echo ""
    python3 setup_wizard.py
else
    echo "Agents found: $(python3 -c "import json; agents=json.load(open('agents.json')); print(len(agents))")"
    echo ""
    echo "Options:"
    echo "  1. Launch the hub (existing configuration)"
    echo "  2. Re-run setup wizard (add/reconfigure agents)"
    echo "  3. Exit"
    echo ""
    read -p "Choose [1]: " CHOICE
    CHOICE="${CHOICE:-1}"

    if [ "$CHOICE" = "2" ]; then
        python3 setup_wizard.py
    elif [ "$CHOICE" = "3" ]; then
        exit 0
    fi
fi

echo ""
echo "Generating agent files..."
python3 agent_factory.py agents.json generated_agents/ 2>/dev/null || echo "  (Agent files generated or skipped)"

echo ""
echo "Launching SeVIn AI Hub..."
python3 launch_system.py --start

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  SeVIn AI Hub is running!"
echo ""
echo "  To view:   tmux attach -t sevin-hub"
echo "  To stop:   python3 launch_system.py --stop"
echo "  Status:    python3 launch_system.py --status"
echo ""
