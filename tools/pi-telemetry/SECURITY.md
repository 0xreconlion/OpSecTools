# Security Policy

## Scope

Pi Telemetry is designed for **local-only, trusted environments**. The default configuration binds to `127.0.0.1` and is not accessible from the network.

### What Pi Telemetry does not protect against

- **Untrusted networks** – If you enable `PI_TELEMETRY_BIND=0.0.0.0`, the dashboard becomes accessible to anyone on your network without authentication.
- **Network sniffing** – The dashboard does not use HTTPS. Do not use this over untrusted or unencrypted networks.
- **Privilege escalation** – Running the dashboard as `root` is not necessary and not recommended.

### What Pi Telemetry does protect

- **Default isolation** – Binds to localhost only; no remote exposure by default.
- **Information disclosure** – Uses proper HTML escaping to prevent XSS when displaying system information.
- **Request security** – Sends cache-control headers and enforces secure response headers (X-Frame-Options, X-Content-Type-Options).
- **LLM privacy boundary** – The LLM view is metadata-only and does not read prompt/session transcript files.

## Reporting a vulnerability

If you discover a security vulnerability in Pi Telemetry, please do not open a public GitHub issue. Instead:

1. **Report privately** through GitHub Security Advisories:
   <https://github.com/0xreconlion/OpSecTools/security/advisories/new>
   - Include a description of the vulnerability
   - Describe the potential impact
   - Suggest a fix if possible
2. **Wait** for a response within 7 days
3. **Allow time** for us to develop and test a patch (typically 14–30 days)
4. **Coordinate** disclosure if you plan to publish the issue elsewhere

## Known limitations

### Information exposure

The `/api/telemetry` endpoint returns system information including:

- Hostname and platform details
- CPU frequency, core count, and usage
- Memory and disk usage
- Network interface names and traffic rates
- Top process names and resource usage
- Thermal throttle status
- Optional metadata-only local LLM telemetry if enabled

**This is by design for a local monitoring dashboard**, but users should be aware that anyone with access to the endpoint can observe this information.

### Local LLM telemetry

When enabled, the LLM view reads Codex CLI metadata from `~/.codex/state_5.sqlite` by default. The collector is intentionally limited to safe operational fields such as model/provider, token totals, shortened thread IDs, timestamps, CLI version, and workspace basename.

The collector must not read or expose:

- Prompt text
- Session JSONL transcript contents
- Thread titles, previews, or first-user-message fields
- Full workspace paths
- API keys, tokens, or environment variables

Users can disable this collector with `PI_TELEMETRY_LLM=off` or `--no-llm-telemetry`.

### Subprocess calls

Pi Telemetry calls `vcgencmd get_throttled` to read Raspberry Pi thermal throttle status. This subprocess call:

- Is safe (no user input is passed)
- Has a 0.5-second timeout
- Is cached for 10 seconds to avoid repeated calls
- Falls back gracefully if `vcgencmd` is unavailable

### Thread safety

Pi Telemetry uses `ThreadingHTTPServer`, which spawns a thread per request. The telemetry state machine uses locks to ensure safe access to shared state (network statistics). The implementation has been reviewed for thread-safety issues.

## Dependencies

Pi Telemetry has one runtime dependency:

- **psutil** (≥5.9) – For system metrics collection

Psutil is a well-maintained, widely-used library with a strong security track record. Check [psutil's security advisories](https://github.com/giampaolo/psutil/security/advisories) for any issues.

## Security best practices for users

1. **Keep your Pi updated** – Run `sudo apt update && sudo apt upgrade` regularly
2. **Do not expose to the internet** – Never enable `PI_TELEMETRY_BIND=0.0.0.0` on systems with internet access
3. **Use on trusted networks only** – Only enable LAN access on your home/office network
4. **Run as non-root** – Never run the dashboard with `sudo`
5. **Use HTTPS if you expose LAN access** – Consider running behind a reverse proxy (nginx, Caddy) with HTTPS
6. **Monitor access** – If you do expose the endpoint, log and monitor access

## Versioning and patching

- **Major version bump** (e.g., 1.x → 2.0) – Breaking changes, significant feature additions
- **Minor version bump** (e.g., 1.0 → 1.1) – New features, non-breaking changes
- **Patch version bump** (e.g., 1.0.0 → 1.0.1) – Bug fixes, security patches

Security patches will be released as soon as possible and announced in the CHANGELOG.

## Vulnerability history

None reported yet. This is early software—use at your own risk and report issues responsibly.

---

**Last updated:** 2026-06-13

If you have questions about this policy, please open a discussion on GitHub.
