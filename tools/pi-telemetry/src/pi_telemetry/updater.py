from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PACKAGE_NAME = "pi-telemetry"
PYPI_RELEASE_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
GITHUB_RELEASE_URL = "https://github.com/0xreconlion/OpSecTools/releases/latest"

INSTALL_ROOT_ENV = "PI_TELEMETRY_INSTALL_ROOT"
UPDATE_NOTICE_ENV = "PI_TELEMETRY_UPDATE_NOTICE_JSON"


@dataclass(frozen=True)
class UpdateNotice:
    available: bool
    checked: bool
    channel: str
    kind: str
    current_version: str
    latest_version: str
    release_url: str
    update_command: str
    install_command: str | None
    install_root: str | None
    summary: str
    auto_update_ready: bool
    source: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _version_parts(value: str) -> tuple[int, ...]:
    parts = [int(chunk) for chunk in re.findall(r"\d+", value)]
    return tuple(parts or [0])


def is_newer_version(latest: str, current: str) -> bool:
    return _version_parts(latest) > _version_parts(current)


def detect_install_root() -> Path | None:
    raw = os.environ.get(INSTALL_ROOT_ENV)
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    return candidate if candidate.exists() else None


def _read_json_url(url: str, timeout: float) -> dict[str, object]:
    with urlopen(url, timeout=timeout) as response:  # noqa: S310
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("unexpected JSON payload")
    return data


def latest_pypi_version(timeout: float = 1.5) -> str | None:
    try:
        payload = _read_json_url(PYPI_RELEASE_URL, timeout)
    except (OSError, ValueError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    version = info.get("version")
    return str(version) if version else None


def _iter_git_tag_versions(output: str) -> list[str]:
    versions: list[str] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or "refs/tags/" not in line:
            continue
        tag = line.rsplit("refs/tags/", 1)[-1]
        if tag.endswith("^{}"):
            tag = tag[:-3]
        tag = tag.lstrip("v")
        if re.fullmatch(r"\d+(?:\.\d+){0,3}", tag):
            versions.append(tag)
    return versions


def latest_git_version(repo_root: Path, timeout: float = 1.5) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "ls-remote", "--tags", "--refs", "origin"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return None
    if result.returncode != 0:
        return None
    versions = sorted(_iter_git_tag_versions(result.stdout), key=_version_parts)
    return versions[-1] if versions else None


def _notice(
    *,
    available: bool,
    checked: bool,
    channel: str,
    kind: str,
    current_version: str,
    latest_version: str,
    release_url: str,
    update_command: str,
    install_root: Path | None,
    summary: str,
    source: str,
) -> dict[str, object]:
    return UpdateNotice(
        available=available,
        checked=checked,
        channel=channel,
        kind=kind,
        current_version=current_version,
        latest_version=latest_version,
        release_url=release_url,
        update_command=update_command,
        install_command=None,
        install_root=str(install_root) if install_root else None,
        summary=summary,
        auto_update_ready=False,
        source=source,
    ).as_dict()


def build_update_notice(
    current_version: str, install_root: Path | None = None
) -> dict[str, object]:
    install_root = install_root or detect_install_root()
    if install_root and (install_root / ".git").exists():
        latest_version = latest_git_version(install_root)
        if latest_version and is_newer_version(latest_version, current_version):
            return _notice(
                available=True,
                checked=True,
                channel="git",
                kind="revision",
                current_version=current_version,
                latest_version=latest_version,
                release_url=GITHUB_RELEASE_URL,
                update_command=(
                    f'git -C "{install_root}" pull --ff-only && '
                    f'"{sys.executable}" -m pip install -e "{install_root}"'
                ),
                install_root=install_root,
                summary=(
                    f"Version {latest_version} is available. You are running {current_version}."
                ),
                source="git",
            )
        return _notice(
            available=False,
            checked=True,
            channel="git",
            kind="revision",
            current_version=current_version,
            latest_version=current_version,
            release_url=GITHUB_RELEASE_URL,
            update_command=(
                f'git -C "{install_root}" pull --ff-only && '
                f'"{sys.executable}" -m pip install -e "{install_root}"'
            ),
            install_root=install_root,
            summary="No newer git tag is available.",
            source="git",
        )

    latest_version = latest_pypi_version()
    if latest_version and is_newer_version(latest_version, current_version):
        return _notice(
            available=True,
            checked=True,
            channel="pypi",
            kind="package",
            current_version=current_version,
            latest_version=latest_version,
            release_url=f"https://pypi.org/project/{PACKAGE_NAME}/{latest_version}/",
            update_command=f'"{sys.executable}" -m pip install --upgrade {PACKAGE_NAME}',
            install_root=install_root,
            summary=(f"Version {latest_version} is available. You are running {current_version}."),
            source="pypi",
        )

    return _notice(
        available=False,
        checked=bool(latest_version),
        channel="pypi",
        kind="package",
        current_version=current_version,
        latest_version=current_version,
        release_url=PYPI_RELEASE_URL,
        update_command=f'"{sys.executable}" -m pip install --upgrade {PACKAGE_NAME}',
        install_root=install_root,
        summary="You are on the latest available release.",
        source="pypi",
    )
