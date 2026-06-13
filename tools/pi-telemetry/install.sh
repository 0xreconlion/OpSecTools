#!/usr/bin/env bash
# pi-telemetry installation script
# Installs pi-telemetry for the current user with proper XDG compliance

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# XDG base directory specification
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${DATA_HOME}/pi-telemetry"
VENV_DIR="${APP_DIR}/venv"
ICON_DIR="${DATA_HOME}/icons/hicolor/scalable/apps"
DESKTOP_DIR="${DATA_HOME}/applications"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if we're in the right directory
if [[ ! -f "$SCRIPT_DIR/src/pi_telemetry/dashboard.py" ]]; then
    echo -e "${RED}✗ Error: Could not find src/pi_telemetry/dashboard.py${NC}"
    echo "  Run this script from the pi-telemetry repository root."
    exit 1
fi

if [[ ! -f "$SCRIPT_DIR/pyproject.toml" ]]; then
    echo -e "${RED}✗ Error: Could not find pyproject.toml${NC}"
    echo "  Run this script from the pi-telemetry repository root."
    exit 1
fi

echo -e "${YELLOW}Installing pi-telemetry...${NC}"

# Create directories
mkdir -p "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR" "$APP_DIR"

# Get the real path to the Python executable
PYTHON_BIN="$(which python3 || which python)" || {
    echo -e "${RED}✗ Error: Python 3 not found${NC}"
    exit 1
}

echo "  Using Python: $PYTHON_BIN"

# Install into an isolated user-owned virtual environment.
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "  Creating virtual environment: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR" || {
        echo -e "${RED}✗ Failed to create virtual environment${NC}"
        echo "  Install python3-venv and rerun this script."
        exit 1
    }
fi

VENV_PYTHON="$VENV_DIR/bin/python"
echo "  Installing package into virtual environment..."
"$VENV_PYTHON" -m pip install --upgrade pip >/dev/null
"$VENV_PYTHON" -m pip install "$SCRIPT_DIR" || {
    echo -e "${RED}✗ Failed to install pi-telemetry${NC}"
    exit 1
}

# Create the launcher script
LAUNCHER="$BIN_DIR/pi-telemetry"
cat > "$LAUNCHER" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="__PYTHON_BIN__"

PORT="${PI_TELEMETRY_PORT:-8788}"
URL="${PI_TELEMETRY_URL:-http://127.0.0.1:${PORT}}"

# Run the Python dashboard
python_runner() {
    "$PYTHON_BIN" -m pi_telemetry.dashboard --host "${PI_TELEMETRY_BIND:-127.0.0.1}" --port "$PORT"
}

# Start dashboard in background
python_runner > /tmp/pi-telemetry-launch.log 2>&1 &
DAEMON_PID=$!
cleanup() {
    kill "$DAEMON_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

# Wait for the server to be ready
if command -v curl >/dev/null 2>&1; then
    for i in {1..30}; do
        if curl -fsS "$URL/health" > /dev/null 2>&1; then
            break
        fi
        sleep 0.1
    done
else
    sleep 1
fi

# Try to open in Chromium with dedicated profile
if command -v chromium >/dev/null 2>&1; then
    chromium --new-window --app="$URL" --user-data-dir=/tmp/pi-telemetry-chrome-profile --class=PiTelemetry
elif command -v chromium-browser >/dev/null 2>&1; then
    chromium-browser --new-window --app="$URL" --user-data-dir=/tmp/pi-telemetry-chrome-profile --class=PiTelemetry
elif command -v google-chrome >/dev/null 2>&1; then
    google-chrome --new-window --app="$URL" --user-data-dir=/tmp/pi-telemetry-chrome-profile --class=PiTelemetry
elif command -v firefox >/dev/null 2>&1; then
    firefox "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL"
    echo "Pi Telemetry is running at $URL" >&2
    echo "Press Ctrl+C to stop the server." >&2
    wait $DAEMON_PID
else
    echo "Pi Telemetry is running at $URL" >&2
    echo "Open this URL in your browser." >&2
    wait $DAEMON_PID
fi
EOF

# Insert the virtualenv Python path into the launcher.
sed -i "s|__PYTHON_BIN__|$VENV_PYTHON|g" "$LAUNCHER"
chmod +x "$LAUNCHER"

# Create .desktop file
DESKTOP_FILE="$DESKTOP_DIR/pi-telemetry.desktop"
cat > "$DESKTOP_FILE" << 'DESKTOPEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Pi Telemetry
Comment=Lightweight Raspberry Pi hardware telemetry dashboard
Exec=$BIN_DIR_PLACEHOLDER/pi-telemetry
Icon=pi-telemetry
Terminal=false
StartupNotify=true
Categories=System;Monitor;Utility;
StartupWMClass=PiTelemetry
Keywords=raspberry;pi;telemetry;monitoring;hardware;
DESKTOPEOF

sed -i "s|\$BIN_DIR_PLACEHOLDER|$BIN_DIR|g" "$DESKTOP_FILE"

# Copy icon if it exists
if [[ -f "$SCRIPT_DIR/assets/pi-telemetry.svg" ]]; then
    cp "$SCRIPT_DIR/assets/pi-telemetry.svg" "$ICON_DIR/pi-telemetry.svg"
    echo "  Icon installed"
fi

# Create desktop shortcut (if Desktop directory exists)
if [[ -d "$HOME/Desktop" ]]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/Pi Telemetry.desktop"
    chmod +x "$HOME/Desktop/Pi Telemetry.desktop"
fi

echo -e "${GREEN}✓ Installation complete${NC}"
echo ""
echo "Launcher installed to: $LAUNCHER"
echo "Virtual environment installed to: $VENV_DIR"
echo "Desktop entry installed to: $DESKTOP_FILE"
echo ""
echo "You can now start pi-telemetry by:"
echo "  - Running: pi-telemetry"
echo "  - Clicking the desktop shortcut or app menu entry"
echo "  - Setting PI_TELEMETRY_BIND=0.0.0.0 for LAN access (not secure)"
echo ""
echo "To uninstall, run:"
echo "  rm -rf '$APP_DIR' '$LAUNCHER' '$DESKTOP_FILE' '$ICON_DIR/pi-telemetry.svg' '$HOME/Desktop/Pi Telemetry.desktop'"
