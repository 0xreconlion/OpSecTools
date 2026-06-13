# Pi Telemetry

A lightweight, self-contained browser dashboard for real-time Raspberry Pi hardware monitoring.

## Features

- **Lightweight** – Single Python file, minimal dependencies (just `psutil`)
- **Local-first** – Binds to `127.0.0.1` by default; no remote access without explicit opt-in
- **No frameworks** – Pure HTML5 + vanilla JavaScript, no Electron, no build step
- **Real-time metrics** – CPU, temperature, memory, disk, load average, network, and top processes
- **Dark mode dashboard** – Responsive design with live charts
- **Desktop app** – Launchable from app menu or desktop shortcut on XFCE, GNOME, KDE

## Install

### From source

```bash
git clone https://github.com/0xreconlion/OpSecTools.git
cd OpSecTools/tools/pi-telemetry
./install.sh
```

The installer will:
- Create a `pi-telemetry` launcher in `~/.local/bin/`
- Register a desktop app entry in `~/.local/share/applications/`
- Copy the SVG icon to `~/.local/icons/`
- Create a desktop shortcut (if `~/Desktop` exists)

### Via pip (once on PyPI)

```bash
pip install --user pi-telemetry
pi-telemetry
```

From this monorepo directly:

```bash
pip install --user "git+https://github.com/0xreconlion/OpSecTools.git#subdirectory=tools/pi-telemetry"
pi-telemetry
```

## Usage

### Launch from app menu

Look for "Pi Telemetry" in your desktop environment's application menu (XFCE, GNOME, KDE).

### Launch from command line

```bash
pi-telemetry
```

This starts the Python server on `127.0.0.1:8788` and opens it in Chromium (or your default browser).

### Custom port

```bash
PI_TELEMETRY_PORT=9000 pi-telemetry
```

### LAN access (experimental, not secure for untrusted networks)

To access from another device on your local network:

```bash
PI_TELEMETRY_BIND=0.0.0.0 pi-telemetry
```

Then visit `http://<your-pi-ip>:8788/` from another device. **Do not expose this to the internet.**

### JSON API

The dashboard exposes a JSON telemetry endpoint:

```bash
curl http://127.0.0.1:8788/api/telemetry | jq .
```

Response includes: CPU, memory, disk, temperature, network stats, process list, and throttle status.

### Health check

```bash
curl http://127.0.0.1:8788/health
# {"ok": true}
```

### Stop the dashboard

```bash
pkill -f pi_telemetry
```

Or close the Chromium window.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PI_TELEMETRY_PORT` | `8788` | HTTP server port |
| `PI_TELEMETRY_BIND` | `127.0.0.1` | HTTP server bind address (localhost only by default) |
| `PI_TELEMETRY_URL` | `http://127.0.0.1:${PORT}` | Override the URL opened in the browser |

## Security

### Local-only by default

Pi Telemetry binds to `127.0.0.1` and is inaccessible from other machines by default.

### Information exposed

The `/api/telemetry` endpoint returns:

- System hostname, platform, and boot time
- CPU usage (per-core and total), frequency, and core count
- Memory and swap usage (GB and percent)
- Disk usage for root partition
- System temperature (if available)
- Network interface names and traffic rates
- Top 8 processes by CPU usage (name, PID, and usage percent)
- Throttle status (if `vcgencmd` is available)

**This information is only accessible from `localhost` by default.** If you enable LAN access with `PI_TELEMETRY_BIND=0.0.0.0`, anyone on your network can see this telemetry.

### No authentication

There is no authentication mechanism. Use this tool on trusted networks only.

### Chromium isolation

The launcher opens the dashboard in a dedicated Chromium profile (`/tmp/pi-telemetry-chrome-profile`) to isolate it from your browser session and prevent cookie/session bleed.

## Requirements

- **Raspberry Pi** 3A+, 3B+, 4, or 5 (or any Linux machine with psutil)
- **Python 3.9+**
- **psutil 5.9+** (installed automatically)
- **Chromium, Firefox, or default browser** (for the UI; the dashboard works in any browser)

### Tested on

- Raspberry Pi OS (Bullseye, Bookworm)
- Debian 11, 12
- Ubuntu 20.04 LTS+

## Troubleshooting

### "psutil not found"

Install it:

```bash
pip install --user psutil
# or
sudo apt install python3-psutil
```

### Dashboard shows "offline"

The Python server may have crashed. Check the logs:

```bash
tail /tmp/pi-telemetry-launch.log
```

### Chromium not found

On Raspberry Pi OS, Chromium is usually installed. If not:

```bash
sudo apt install chromium-browser
```

Alternatively, set `PI_TELEMETRY_URL` and open the URL manually:

```bash
PI_TELEMETRY_URL="http://127.0.0.1:8788" pi-telemetry
```

### High CPU usage on dashboard

The default refresh rate is 1 second. Reduce it by stopping the server and editing `dashboard.py` if needed (search for `setInterval(tick, 1000)`).

### Temperature shows `None`

Temperature reading depends on your Pi model and kernel version. The dashboard tries multiple paths:
- `/sys/class/thermal/thermal_zone0/temp` (preferred)
- `/sys/class/hwmon/hwmon0/temp1_input` (fallback)
- `psutil.sensors_temperatures()` (final fallback)

If none work, the temperature field will show unavailable.

### Throttle status always says "unavailable"

`vcgencmd` may not be installed on your system. This is normal on non-Raspberry Pi hardware. The dashboard will continue to work without it.

## Development

### Local development

```bash
git clone https://github.com/0xreconlion/OpSecTools.git
cd OpSecTools/tools/pi-telemetry

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run directly
python -m pi_telemetry.dashboard

# Run tests
pytest
```

### Code style

We use Black for formatting:

```bash
black src tests
```

Type checking with mypy:

```bash
mypy src
```

### Testing

```bash
pytest tests/
```

## Architecture

Pi Telemetry is intentionally single-file and zero-framework:

- **`src/pi_telemetry/dashboard.py`** – Single Python module with embedded HTML/CSS/JS
  - `TelemetryState` – Collects system metrics (thread-safe, single instance)
  - `DashboardHandler` – Serves HTML dashboard and JSON API
  - `ThrottleCache` – Caches `vcgencmd` calls to avoid subprocess spam
  - Embedded HTML – Self-contained UI with no external dependencies

This design prioritizes portability, ease of installation, and minimal resource usage over modularity. If you need a more modular architecture, consider this a reference implementation.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes and test them
4. Run `black` and `mypy` for style/type checking
5. Commit with clear messages
6. Open a pull request

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## Security

If you discover a security vulnerability, please see [SECURITY.md](SECURITY.md) for responsible disclosure.

---

Made for Raspberry Pi tinkerers. Enjoy.
