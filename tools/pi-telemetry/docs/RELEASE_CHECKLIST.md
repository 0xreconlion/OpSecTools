# Release Checklist

## Before First Commit

- [ ] Add generated application files using the import map.
- [ ] Confirm MIT license text and copyright holder.
- [ ] Review README install commands on a clean Raspberry Pi user account.
- [ ] Confirm no local usernames, absolute home paths, credentials, or LAN-only
      assumptions are present.
- [ ] Run formatting and tests locally.

## Before v1.0.0 Tag

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

## GitHub Setup

- [x] Replace `OWNER` in `.github/ISSUE_TEMPLATE/config.yml`.
- [ ] Enable private vulnerability reporting.
- [ ] Enable Discussions if you want community support outside issues.
- [ ] Add repository topics: `raspberry-pi`, `telemetry`, `dashboard`,
      `python`, `linux`.
