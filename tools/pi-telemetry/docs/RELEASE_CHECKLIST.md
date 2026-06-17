# Release Checklist

## Before First Commit

- [ ] Add generated application files using the import map.
- [ ] Confirm MIT license text and copyright holder.
- [ ] Review README install commands on a clean Raspberry Pi user account.
- [ ] Confirm no local usernames, absolute home paths, credentials, or LAN-only
      assumptions are present.
- [ ] Run formatting and tests locally.

## Before v1.1.1 Tag

- [ ] `cd tools/pi-telemetry`
- [ ] `python -m pip install -e ".[dev]"`
- [ ] `black --check .`
- [ ] `python -m pytest`
- [ ] `python -m build`
- [ ] `pipx run twine check dist/*`
- [ ] Install the built wheel in a fresh virtual environment.
- [ ] Verify `pi-telemetry` command starts and exits cleanly.
- [ ] Verify Chromium kiosk/profile behavior on a Pi.
- [ ] Verify LAN binding is documented and opt-in.
- [ ] Verify Host view updates at desktop, snapped, and narrow/mobile widths.
- [ ] Verify resize pauses the feed briefly and returns to `live`.
- [ ] Verify LLM view with Codex active, Codex idle, and `PI_TELEMETRY_LLM=off`.
- [ ] Confirm LLM API output contains no prompt text, thread titles, session JSONL
      content, API keys, full home paths, or credentials.
- [ ] Verify `PI_TELEMETRY_CODEX_STATE` and `PI_TELEMETRY_CODEX_PROCESS`
      overrides work as documented.
- [ ] Verify the startup update banner appears when a newer release is detected.
- [ ] Verify the shown update command matches the install mode (`pip` or git-backed source checkout).
- [ ] Confirm the combined OBS/AAR/token-cost note is current and linked from the release docs.

## GitHub Setup

- [x] Replace `OWNER` in `.github/ISSUE_TEMPLATE/config.yml`.
- [ ] Enable private vulnerability reporting.
- [ ] Enable Discussions if you want community support outside issues.
- [ ] Add repository topics: `raspberry-pi`, `telemetry`, `dashboard`,
      `python`, `linux`.
