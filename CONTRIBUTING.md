# Contributing

Thanks for helping improve OpSecTools. This repository should stay practical,
portable, and safe to run on Linux systems.

## Development Setup

```bash
cd tools/pi-telemetry
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Local Checks

Run these before opening a pull request:

```bash
cd tools/pi-telemetry
black --check src tests
python -m pytest
python -m compileall src tests
```

If type checking is enabled in the project config, also run:

```bash
cd tools/pi-telemetry
mypy src
```

## Pull Requests

- Keep changes narrowly scoped.
- Include tests for behavior changes.
- Update README, SECURITY, or CHANGELOG when user-facing behavior changes.
- Do not add telemetry collection that sends data off-device without explicit,
  documented opt-in behavior.
- Avoid hardcoded usernames, home directories, hostnames, or network addresses.

## Security

Do not report vulnerabilities through public GitHub issues. Follow
`SECURITY.md` once it is added to the repository.
