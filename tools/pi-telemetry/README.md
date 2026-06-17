# Pi Telemetry

A lightweight, self-contained browser dashboard for real-time Raspberry Pi hardware monitoring.

## Features

- **Lightweight** – Single Python file, minimal dependencies (just `psutil`)
- **Local-first** – Binds to `127.0.0.1` by default; no remote access without explicit opt-in
- **No frameworks** – Pure HTML5 + vanilla JavaScript, no Electron, no build step
- **Real-time metrics** – CPU, temperature, memory, disk, load average, network, and top processes
- **Local LLM view** – Optional metadata-only Codex CLI telemetry for token totals, model mix, and local process pressure
- **Dark mode dashboard** – Responsive design with live charts
- **Desktop app** – Launchable from app menu or desktop shortcut on XFCE, GNOME, KDE

Release note, AAR, and token-cost analysis source:

- [docs/OBS_AAR_TOKEN_COST_ANALYSIS.md](docs/OBS_AAR_TOKEN_COST_ANALYSIS.md)

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

### Dashboard views

The dashboard has two live views:

- **Host** – CPU, temperature, memory, disk, load average, network, Pi health, and top process pressure.
- **LLM** – Metadata-only local LLM telemetry focused on Codex CLI usage, token totals, token delta/rate, model mix, recent thread metadata, Codex process pressure, and host pressure while LLM work is active.

The browser UI adapts to full-screen, snapped, and narrow windows. During manual resize or screen snapping, polling pauses briefly and resumes after the layout settles so the live feed does not fight the browser while frames are being adjusted.

### Updates

When a newer release is available, the launcher checks for it at startup and the dashboard shows a banner with the exact update command. The prompt is non-blocking by default: you can copy the command, open the release notes, or hide that version in the browser.

Supported update paths:

- `pip` installs: `python -m pip install --upgrade pi-telemetry`
- source checkouts with a recorded repo root: `git pull --ff-only` followed by reinstall from that checkout
- optional release feeds for beta/stable channels via JSON
- working-tree prompts when the app is running from an unreleased git checkout

The updater is source-driven: new update channels are added by registering another source, not by rewriting the launcher flow.
Feed notices stay prompt-only unless the feed includes an explicit install command. That keeps staged releases safe while still allowing auto-update mode for trusted feeds.

Automatic update before launch is opt-in:

```bash
PI_TELEMETRY_UPDATE_MODE=auto pi-telemetry
```

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

When enabled, the response also includes `llm` metadata from local Codex CLI state:

- Thread count, token totals, and token delta/rate
- Model/provider aggregate counts
- Recent thread IDs shortened for display
- Workspace basename only, not the full path
- Matching local process CPU/RSS pressure

Prompt text, session JSONL content, thread titles, previews, and full project paths are not read or exposed.

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
| `PI_TELEMETRY_LLM` | `true` | Enable metadata-only local LLM telemetry (`0`, `false`, `no`, `off`, or `disabled` turn it off) |
| `PI_TELEMETRY_CODEX_STATE` | `~/.codex/state_5.sqlite` | Override the Codex CLI state database path |
| `PI_TELEMETRY_CODEX_PROCESS` | `codex` | Process name/cmdline marker used for local LLM process pressure |
| `PI_TELEMETRY_UPDATE_MODE` | `prompt` | Update behavior at startup (`prompt`, `auto`, or `off`) |
| `PI_TELEMETRY_INSTALL_ROOT` | unset | Source checkout root used for git-backed updates when available |
| `PI_TELEMETRY_RELEASE_FEED_URL` | unset | Optional JSON feed for beta/stable release notices |

The Python entrypoint also accepts matching command-line flags:

```bash
python -m pi_telemetry.dashboard \
  --no-llm-telemetry \
  --codex-state-path ~/.codex/state_5.sqlite \
  --codex-process-marker codex
```

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
- Metadata-only local LLM telemetry when enabled

**This information is only accessible from `localhost` by default.** If you enable LAN access with `PI_TELEMETRY_BIND=0.0.0.0`, anyone on your network can see this telemetry.

### LLM telemetry privacy

The LLM view reads Codex CLI metadata from `~/.codex/state_5.sqlite` by default. It does not read Codex session JSONL files and does not query prompt text, thread titles, previews, or full workspace paths. The dashboard displays only aggregate metadata and workspace basenames.

Disable LLM telemetry completely with:

```bash
PI_TELEMETRY_LLM=off pi-telemetry
```

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

### LLM view shows unavailable

The Codex CLI state database may not exist, may be in a different location, or LLM telemetry may be disabled. Check:

```bash
ls ~/.codex/state_5.sqlite
PI_TELEMETRY_CODEX_STATE=/path/to/state_5.sqlite pi-telemetry
```

For non-Codex local hosts, set a different process marker:

```bash
PI_TELEMETRY_CODEX_PROCESS=ollama pi-telemetry
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
  - `CodexTelemetryState` – Reads metadata-only Codex CLI state for the LLM view
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
