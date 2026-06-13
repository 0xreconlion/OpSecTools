# Pi Telemetry – Open Source Best Practices Roadmap

This document outlines the complete path from "fixed files" to a thriving open-source project.

---

## Phase 1: Repository Setup (1–2 hours)

### 1.1 Initialize the repo

```bash
# Clone the parent repository and enter this tool package
git clone https://github.com/0xreconlion/OpSecTools.git
cd OpSecTools/tools/pi-telemetry

# Create the package directory structure if starting from scratch
mkdir -p src/pi_telemetry assets scripts tests

# Git is initialized at the OpSecTools repository root
git config user.email "your-email@example.com"
git config user.name "ReconLion"

# Copy fixed files
cp /path/to/dashboard.py src/pi_telemetry/dashboard.py
cp /path/to/__init__.py src/pi_telemetry/__init__.py
cp /path/to/pyproject.toml .
cp /path/to/install.sh .
cp /path/to/README.md .
cp /path/to/SECURITY.md .
cp /path/to/CHANGELOG.md .
cp /path/to/LICENSE .
```

### 1.2 Create initial directory structure

```bash
# Placeholder files
touch tests/__init__.py
touch tests/test_dashboard.py
touch assets/.gitkeep
mkdir -p scripts/
touch scripts/ci-lint.sh
touch scripts/ci-test.sh
```

### 1.3 Create .gitignore

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
pip-log.txt
pip-delete-this-directory.txt

# Virtual environments
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Testing
.coverage
.pytest_cache/
htmlcov/

# Runtime
/tmp/
*.log
*.pid
EOF

git add .gitignore
```

### 1.4 Create initial commit

```bash
git add -A
git commit -m "Initial commit: pi-telemetry v1.0.0"
git tag v1.0.0
```

---

## Phase 2: GitHub/Gitea Setup (30 minutes)

### 2.1 Choose your hosting

**Option A: GitHub** (recommended for open-source visibility)
- Create account at github.com
- Create new repository: `https://github.com/0xreconlion/OpSecTools`
- Add as remote: `git remote add origin https://github.com/0xreconlion/OpSecTools.git`

**Option B: Gitea** (self-hosted)
- Set up Gitea on your server
- Create repo: `https://your-domain/gitea/pi-telemetry`
- Add as remote: `git remote add origin https://your-domain/gitea/pi-telemetry.git`

### 2.2 Configure repository settings

**GitHub-specific:**
1. Go to Settings → General
2. Add description: "Lightweight Raspberry Pi hardware telemetry dashboard"
3. Add website: `https://github.com/0xreconlion/OpSecTools`
4. Add topics: `raspberry-pi`, `telemetry`, `dashboard`, `monitoring`, `psutil`, `hardware`
5. Enable "Discussions" (Settings → Features)
6. Set default branch to `main`

**README visibility:**
1. Add a screenshot to `assets/screenshot.png` (250x200 PNG recommended)
2. Update README.md to reference the screenshot correctly

### 2.3 Push to remote

```bash
git branch -M main
git push -u origin main --tags
```

---

## Phase 3: Documentation & Community (2–3 hours)

### 3.1 Enhance README

Add to your README:
- **Quick start video** – Consider a 30-second GIF showing launch → dashboard
- **Feature comparison** – vs. Glances, Conky, etc.
- **Sponsorship** – Add a "Sponsor" button (GitHub Sponsors, Ko-fi, Patreon)
- **Contributing** – Link to CONTRIBUTING.md (create below)

### 3.2 Create CONTRIBUTING.md

```bash
cat > CONTRIBUTING.md << 'EOF'
# Contributing to Pi Telemetry

Thanks for your interest! Here's how to contribute.

## Reporting Issues

- Check [existing issues](../../issues) first
- Include your Pi model, OS version, and Python version
- Provide `pi-telemetry --version` output
- Include error messages from `/tmp/pi-telemetry-launch.log`

## Feature Requests

- Check [discussions](../../discussions) for related ideas
- Start a discussion if unsure
- Be specific: "Add Prometheus metrics endpoint" is better than "add more features"

## Code Contributions

### Setup

```bash
git clone https://github.com/0xreconlion/OpSecTools.git
cd OpSecTools/tools/pi-telemetry
pip install -e ".[dev]"
```

### Before you commit

```bash
# Format with Black
black src tests

# Type check with mypy
mypy src

# Run tests
pytest

# Lint with flake8
flake8 src --max-line-length=100
```

### Commit guidelines

- Use imperative mood: "Add feature" not "Added feature"
- Reference issues: "Fix #42 – add Prometheus metrics"
- Keep commits atomic (one idea per commit)

### Pull request process

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Commit with clear messages
5. Push to your fork
6. Open a PR with a description of what and why

## Code style

- Python 3.9+ syntax
- Type hints where practical
- Docstrings for public functions
- Black formatting (100-char line length)
- mypy type checking

## License

By contributing, you agree to license your work under the MIT License.

---

Questions? Open a discussion or email the maintainer.
EOF

git add CONTRIBUTING.md
git commit -m "docs: add contributing guidelines"
git push
```

### 3.3 Create CODE_OF_CONDUCT.md

```bash
cat > CODE_OF_CONDUCT.md << 'EOF'
# Contributor Covenant Code of Conduct

## Our Pledge

We are committed to providing a welcoming and inspiring community for all.

## Our Standards

Examples of behavior that contributes to a positive environment:
- Using welcoming and inclusive language
- Being respectful of differing opinions
- Accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

Examples of unacceptable behavior:
- Harassment or discrimination
- Hate speech
- Deliberate intimidation
- Unwelcome sexual advances
- Trolling or insulting comments

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported
to the project maintainers. All complaints will be reviewed and investigated promptly
and fairly.

---

This Code of Conduct is based on the [Contributor Covenant v2.1](https://www.contributor-covenant.org/).
EOF

git add CODE_OF_CONDUCT.md
git commit -m "docs: add code of conduct"
git push
```

### 3.4 Create .github/ISSUE_TEMPLATE/

```bash
mkdir -p .github/ISSUE_TEMPLATE/

# Bug report
cat > .github/ISSUE_TEMPLATE/bug_report.md << 'EOF'
---
name: Bug Report
about: Report a bug or issue
title: "[BUG] "
labels: bug
---

## Description

A clear description of the problem.

## Steps to Reproduce

1. Run `...`
2. Click on `...`
3. Observe error: `...`

## Expected behavior

What should happen instead?

## Environment

- Raspberry Pi model: (Pi 4B, Pi 5, etc.)
- OS: (Raspberry Pi OS Bookworm, Debian 12, etc.)
- Python version: (3.9, 3.10, 3.11, 3.12)
- Browser: (Chromium, Firefox, etc.)

## Error logs

```
Paste the error from /tmp/pi-telemetry-launch.log here
```

## Additional context

Any other information that might help diagnose the issue.
EOF

# Feature request
cat > .github/ISSUE_TEMPLATE/feature_request.md << 'EOF'
---
name: Feature Request
about: Suggest an idea for pi-telemetry
title: "[FEAT] "
labels: enhancement
---

## Description

What feature would you like to see?

## Why is this useful?

Why should this be added to pi-telemetry?

## Suggested implementation

Any thoughts on how this could be implemented?

## Alternatives

Are there other tools or approaches you've considered?
EOF

git add .github/ISSUE_TEMPLATE/
git commit -m "ci: add issue templates"
git push
```

---

## Phase 4: CI/CD Setup (2–3 hours)

### 4.1 Create GitHub Actions workflow

```bash
mkdir -p .github/workflows

cat > .github/workflows/test.yml << 'EOF'
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - name: Lint with Black
        run: black --check src tests
      - name: Type check with mypy
        run: mypy src || true
      - name: Run tests
        run: pytest -v
EOF

cat > .github/workflows/lint.yml << 'EOF'
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install flake8
        run: pip install flake8
      - name: Lint with flake8
        run: flake8 src --max-line-length=100 --count --statistics
EOF

git add .github/workflows/
git commit -m "ci: add github actions workflows"
git push
```

### 4.2 Create basic tests

```bash
cat > tests/test_dashboard.py << 'EOF'
"""Basic tests for pi-telemetry dashboard."""

import json
from pi_telemetry.dashboard import bytes_to_gb, format_duration, escapeHtml


def test_bytes_to_gb():
    """Test byte to GB conversion."""
    assert bytes_to_gb(1024**3) == 1.0
    assert bytes_to_gb(1024**3 * 4) == 4.0
    assert bytes_to_gb(0) == 0.0


def test_format_duration():
    """Test duration formatting."""
    assert format_duration(60) == "1m"
    assert format_duration(3600) == "1h 0m"
    assert format_duration(86400) == "1d 0h 0m"
    assert format_duration(90061) == "1d 1h 1m"


def test_api_structure():
    """Verify telemetry API response structure."""
    # This is a placeholder. Real tests would require mocking psutil
    pass
EOF

git add tests/
git commit -m "test: add basic test suite"
git push
```

### 4.3 Add pre-commit hooks (optional)

```bash
pip install pre-commit

cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 24.3.0
    hooks:
      - id: black
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
EOF

pre-commit install

git add .pre-commit-config.yaml
git commit -m "ci: add pre-commit hooks"
git push
```

---

## Phase 5: Release & Distribution (1–2 hours)

### 5.1 Prepare PyPI package

```bash
# Install build tools
pip install build twine

# Build distribution
python -m build

# Check distribution (this will download psutil and verify)
twine check dist/*
```

### 5.2 Register on PyPI

1. Create account at https://pypi.org/account/register/
2. Create an API token in account settings
3. Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi_YOUR_TOKEN_HERE
```

### 5.3 Upload to PyPI

```bash
# Test upload first
twine upload --repository testpypi dist/*

# Real upload
twine upload dist/*

# Verify at https://pypi.org/project/pi-telemetry/
```

### 5.4 Update GitHub releases

1. Go to GitHub Releases
2. Click "Draft a new release"
3. Tag: `v1.0.0`
4. Title: `Pi Telemetry 1.0.0`
5. Description:
   ```
   ## Changes
   
   See CHANGELOG.md for full details.
   
   ## Installation
   
   ```bash
   pip install pi-telemetry
   ```
   
   Or from source:
   
   ```bash
   git clone https://github.com/0xreconlion/OpSecTools.git
   cd OpSecTools/tools/pi-telemetry
   ./install.sh
   ```
   ```
6. Click "Publish release"

---

## Phase 6: Promotion & Community (ongoing)

### 6.1 Announce the release

Post to:
- **Reddit** – r/raspberry_pi, r/linux, r/python
- **Dev platforms** – dev.to, Medium, Hacker News
- **Discord/forums** – Raspberry Pi Discord, Python communities
- **Twitter/Mastodon** – Brief announcement with link

Example post:
> 🍓 Just released pi-telemetry v1.0.0 – a lightweight real-time dashboard for monitoring Raspberry Pi hardware (CPU, temp, memory, disk, network).
>
> - Runs locally, no frameworks
> - Install via pip: `pip install pi-telemetry`
> - MIT licensed
>
> GitHub: https://github.com/0xreconlion/OpSecTools

### 6.2 Ask for feedback

- Encourage users to open issues for bugs/features
- Pin a "Feedback wanted" discussion for early adopters
- Track feature requests in a GitHub project board

### 6.3 Monitor and respond

- Check issues daily (at least weekly)
- Respond to PRs within 7 days
- Thank contributors publicly
- Update changelog for each release

---

## Phase 7: Ongoing Maintenance & Growth

### 7.1 Version management

- **v1.0.x** – Bug fixes and security patches only
- **v1.1.0** – New features (opt-in config file, systemd service, etc.)
- **v2.0.0** – Breaking changes (Python version bump, module reorganization, etc.)

### 7.2 Release cadence

- Patch releases: As needed (1–2 weeks for critical bugs)
- Minor releases: Every 6–8 weeks (collect feature requests)
- Major releases: Once per year (if justified)

### 7.3 Documentation

Keep updated:
- README with current features
- CHANGELOG for each release
- Issue templates with common problems
- Security policy if needed updates

### 7.4 Community engagement

- Answer issues thoroughly
- Welcome first-time contributors
- Review PRs promptly with constructive feedback
- Give credit in CHANGELOG

### 7.5 Potential next steps

- Prometheus metrics endpoint
- Systemd user service
- Docker container
- ARM64/ARM32 pre-built binaries
- Web-based configuration UI
- Historical data storage
- Mobile app API compatibility

---

## Checklist Summary

- [ ] **Phase 1** – Git repo initialized, files committed
- [ ] **Phase 2** – GitHub/Gitea repo created, code pushed
- [ ] **Phase 3** – README polished, CONTRIBUTING.md added, discussions enabled
- [ ] **Phase 4** – CI/CD workflows set up, basic tests passing
- [ ] **Phase 5** – PyPI package built and published
- [ ] **Phase 6** – Release announced on social media
- [ ] **Phase 7** – Ongoing community engagement and maintenance

---

## Additional Resources

- [Open Source Guides](https://opensource.guide/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Collaborative Development](https://docs.github.com/en/get-started)
- [PyPI Documentation](https://packaging.python.org/)

---

**You're now ready to launch pi-telemetry as a professional open-source project!**

Good luck, and thank you for sharing your work with the community. 🚀
