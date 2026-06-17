# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for future releases

- XDG config file support (`~/.config/pi-telemetry/config.toml`)
- Optional systemd user service
- Prometheus metrics endpoint
- Historical data storage (SQLite)
- Custom refresh rate configuration
- Module separation (collector/server/UI)
- HTTPS support with self-signed certs
- Simple authentication (username/password)
- ARM64 and ARM32 binary releases

---

## [1.1.1] – 2026-06-16

### Added

- Working-tree update prompt for unreleased git checkouts.
- Optional JSON release-feed support for beta or staged releases.
- Source-driven update pipeline to make new package channels easy to add.
- Release-feed notices can carry an explicit install command for auto-update mode.
- Single-source OBS/AAR/token-cost analysis document for release notes and review.

### Changed

- Update banner now distinguishes stable, git, feed, and working-tree update sources.
- Feed notices are prompt-only unless an explicit install command is supplied.
- Release-note links now use a generic label for non-PyPI feed channels.

### Fixed

- Version and revision history now reflect the current 1.1.1 release state.

---

## [1.1.0] – 2026-06-16

### Added

- Host/LLM dashboard view selector.
- Metadata-only Codex CLI telemetry for local LLM monitoring.
- LLM metrics for token totals, token delta/rate, model mix, recent thread metadata, process pressure, and host pressure.
- Runtime controls for disabling LLM telemetry and overriding Codex state/process matching.
- Manual acceptance testing checklist for Host/LLM dashboard verification.
- Startup update prompt with release notes and copyable update command.
- Launcher bootstrap that can apply opt-in automatic updates before the dashboard starts.

### Changed

- Dashboard polling now pauses during browser resize and resumes after layout settles.
- HTML responses use nonce-based CSP for embedded style/script blocks.
- Package entrypoint now routes through the launcher so update checks run consistently for pip and source installs.

### Security

- LLM telemetry intentionally excludes prompt text, session JSONL contents, thread titles/previews, full workspace paths, and secrets.
- Aborted browser fetches no longer print broken-pipe tracebacks from the local HTTP server.

---

## [1.0.0] – 2026-06-13

### Added

- Initial public release of pi-telemetry
- Real-time Raspberry Pi hardware telemetry dashboard
- Self-contained single-file Python application
- Embedded HTML5 + vanilla JavaScript UI with dark mode
- Live metrics for CPU, memory, disk, temperature, network, and processes
- JSON API endpoint (`/api/telemetry`) for programmatic access
- Health check endpoint (`/health`)
- Desktop app launcher for XFCE, GNOME, KDE
- Desktop shortcut support
- Responsive design with live charts
- XDG-compliant installation script
- Comprehensive README with security notes
- MIT License

### Security

- Localhost-only binding by default (`127.0.0.1:8788`)
- Proper HTML escaping to prevent XSS
- Cache-control and security response headers
- Thread-safe telemetry state management
- Subprocess call caching (vcgencmd every 10 seconds)
- Responsible disclosure security policy (SECURITY.md)

### Technical Details

- Python 3.9+ with no heavy frameworks
- Minimal dependencies (psutil only)
- ThreadingHTTPServer for concurrent requests
- Smart temperature reading fallback chain
- Per-interface network statistics
- Process snapshot sorted by CPU usage
- Chromium app-mode launcher with isolated profile

### Known Limitations

- No authentication mechanism (local-only use recommended)
- No HTTPS support (use reverse proxy for LAN access)
- Temperature reading may be unavailable on non-Raspberry Pi systems
- vcgencmd throttle status unavailable on non-Raspberry Pi systems

---

## Version Format

We use [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH`
- `MAJOR` – Breaking changes
- `MINOR` – New features (backward-compatible)
- `PATCH` – Bug fixes and security patches

---

## Security Advisories

None reported. This is early software. Please report vulnerabilities responsibly via the process outlined in [SECURITY.md](SECURITY.md).

---

For more information, see [README.md](README.md).
