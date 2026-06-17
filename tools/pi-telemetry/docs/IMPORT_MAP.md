# Import Map

Use this layout when adding the generated files:

```text
OpSecTools/
  LICENSE
  README.md
  tools/
    pi-telemetry/
      pyproject.toml
      install.sh
      README.md
      SECURITY.md
      CHANGELOG.md
      OPEN_SOURCE_ROADMAP.md
      src/
        pi_telemetry/
          __init__.py
          dashboard.py
      tests/
```

## Notes

- Put `dashboard.py` at `src/pi_telemetry/dashboard.py`.
- Put `__init__.py` at `src/pi_telemetry/__init__.py`.
- Keep pi-telemetry docs and packaging files in `tools/pi-telemetry/`.
- Before tagging v1.1.1, verify the `LICENSE` copyright holder is real and
  intentional.
- If the generated `pyproject.toml` assumes a flat package layout, adjust it to
  discover packages under `src`.

For setuptools, that usually means:

```toml
[tool.setuptools.packages.find]
where = ["src"]
```

and the console script should point at the package module:

```toml
[project.scripts]
pi-telemetry = "pi_telemetry.launcher:main"
```
