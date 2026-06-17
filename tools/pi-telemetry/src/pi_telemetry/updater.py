from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Protocol
from urllib.error import URLError
from urllib.request import urlopen

PACKAGE_NAME = "pi-telemetry"
PYPI_RELEASE_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
GITHUB_RELEASE_URL = "https://github.com/0xreconlion/OpSecTools/releases/latest"

UPDATE_NOTICE_ENV = "PI_TELEMETRY_UPDATE_NOTICE_JSON"
INSTALL_ROOT_ENV = "PI_TELEMETRY_INSTALL_ROOT"
RELEASE_FEED_URL_ENV = "PI_TELEMETRY_RELEASE_FEED_URL"
UPDATE_MODE_ENV = "PI_TELEMETRY_UPDATE_MODE"

DEFAULT_UPDATE_MODE = "prompt"
AUTO_UPDATE_MODE = "auto"
PROMPT_UPDATE_MODE = "prompt"
DISABLED_UPDATE_MODE = "off"


@dataclass(frozen=True)
class UpdateContext:
    current_version: str
    install_root: Path | None
    feed_url: str | None
    python_executable: str = sys.executable


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


class UpdateSource(Protocol):
    name: str

    def build(self, context: UpdateContext) -> UpdateNotice | None: ...


def _default_notice(context: UpdateContext) -> UpdateNotice:
    channel = determine_update_channel(context.install_root)
    return UpdateNotice(
        available=False,
        checked=False,
        channel=channel,
        kind="package" if channel in {"git", "pypi", "feed"} else "revision",
        current_version=context.current_version,
        latest_version=context.current_version,
        release_url=GITHUB_RELEASE_URL if channel == "git" else PYPI_RELEASE_URL,
        update_command="",
        install_command=None,
        install_root=str(context.install_root) if context.install_root else None,
        summary="No update information available.",
        auto_update_ready=False,
        source="none",
    )


def _version_parts(value: str) -> tuple[int, ...]:
    parts = [int(chunk) for chunk in re.findall(r"\d+", value)]
    return tuple(parts or [0])


def is_newer_version(latest: str, current: str) -> bool:
    return _version_parts(latest) > _version_parts(current)


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


def _release_feed_url() -> str | None:
    raw = os.environ.get(RELEASE_FEED_URL_ENV)
    if not raw:
        return None
    return raw.strip() or None


def latest_release_feed(
    feed_url: str | None = None, timeout: float = 1.5
) -> dict[str, object] | None:
    feed_url = feed_url or _release_feed_url()
    if not feed_url:
        return None
    try:
        payload = _read_json_url(feed_url, timeout)
    except (OSError, ValueError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    version = payload.get("version") or payload.get("latest_version")
    if not version:
        return None

    release_url = payload.get("release_url") or feed_url
    summary = payload.get("summary") or payload.get("notes")
    channel = payload.get("channel") or "feed"
    install_command = payload.get("install_command")

    return {
        "version": str(version),
        "release_url": str(release_url),
        "summary": str(summary) if summary else None,
        "channel": str(channel),
        "install_command": str(install_command) if install_command else None,
    }


def _iter_git_tag_versions(output: str) -> Iterable[str]:
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if "refs/tags/" not in line:
            continue
        tag = line.rsplit("refs/tags/", 1)[-1]
        if tag.endswith("^{}"):
            tag = tag[:-3]
        tag = tag.lstrip("v")
        if re.fullmatch(r"\d+(?:\.\d+){0,3}", tag):
            yield tag


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


def detect_install_root() -> Path | None:
    raw = os.environ.get(INSTALL_ROOT_ENV)
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    return candidate if candidate.exists() else None


def determine_update_channel(install_root: Path | None) -> str:
    if install_root and (install_root / ".git").exists():
        return "git"
    return "pypi"


def git_worktree_status(repo_root: Path) -> dict[str, object]:
    status = {
        "is_git": False,
        "is_dirty": False,
        "exact_tag": None,
        "branch": None,
        "commit": None,
    }
    if not repo_root or not (repo_root / ".git").exists():
        return status

    status["is_git"] = True
    try:
        exact = subprocess.run(
            ["git", "-C", str(repo_root), "describe", "--tags", "--exact-match", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=1.5,
        )
        branch = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=1.5,
        )
        commit = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=1.5,
        )
        dirty = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
            timeout=1.5,
        )
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return status

    status["exact_tag"] = (
        exact.stdout.strip() if exact.returncode == 0 and exact.stdout.strip() else None
    )
    status["branch"] = (
        branch.stdout.strip() if branch.returncode == 0 and branch.stdout.strip() else None
    )
    status["commit"] = (
        commit.stdout.strip() if commit.returncode == 0 and commit.stdout.strip() else None
    )
    status["is_dirty"] = bool(dirty.stdout.strip()) if dirty.returncode == 0 else False
    return status


class ReleaseFeedSource:
    name = "release-feed"

    def build(self, context: UpdateContext) -> UpdateNotice | None:
        if not context.feed_url:
            return None

        feed = latest_release_feed(feed_url=context.feed_url)
        if not feed or not is_newer_version(str(feed["version"]), context.current_version):
            return None

        version = str(feed["version"])
        install_command = str(feed["install_command"]) if feed.get("install_command") else None
        return UpdateNotice(
            available=True,
            checked=True,
            channel=str(feed["channel"]),
            kind="package",
            current_version=context.current_version,
            latest_version=version,
            release_url=str(feed["release_url"]),
            update_command=(
                install_command
                or f'"{context.python_executable}" -m pip install --upgrade {PACKAGE_NAME}'
            ),
            install_command=install_command,
            install_root=str(context.install_root) if context.install_root else None,
            summary=(
                str(feed["summary"])
                if feed.get("summary")
                else f"Version {version} is available. You are running {context.current_version}."
            ),
            auto_update_ready=bool(install_command),
            source=self.name,
        )


class GitTagSource:
    name = "git-tag"

    def build(self, context: UpdateContext) -> UpdateNotice | None:
        if not context.install_root or not (context.install_root / ".git").exists():
            return None

        latest_version = latest_git_version(context.install_root)
        if not latest_version or not is_newer_version(latest_version, context.current_version):
            return None

        return UpdateNotice(
            available=True,
            checked=True,
            channel="git",
            kind="package",
            current_version=context.current_version,
            latest_version=latest_version,
            release_url=GITHUB_RELEASE_URL,
            update_command=(
                f'git -C "{context.install_root}" pull --ff-only && '
                f'"{context.python_executable}" -m pip install "{context.install_root}"'
            ),
            install_command=None,
            install_root=str(context.install_root),
            summary=(
                f"Version {latest_version} is available. You are running {context.current_version}."
            ),
            auto_update_ready=True,
            source=self.name,
        )


class PyPIReleaseSource:
    name = "pypi"

    def build(self, context: UpdateContext) -> UpdateNotice | None:
        latest_version = latest_pypi_version()
        if not latest_version or not is_newer_version(latest_version, context.current_version):
            return None

        return UpdateNotice(
            available=True,
            checked=True,
            channel="pypi",
            kind="package",
            current_version=context.current_version,
            latest_version=latest_version,
            release_url=f"https://pypi.org/project/{PACKAGE_NAME}/{latest_version}/",
            update_command=f'"{context.python_executable}" -m pip install --upgrade {PACKAGE_NAME}',
            install_command=None,
            install_root=str(context.install_root) if context.install_root else None,
            summary=(
                f"Version {latest_version} is available. You are running {context.current_version}."
            ),
            auto_update_ready=True,
            source=self.name,
        )


class WorkingTreeSource:
    name = "working-tree"

    def build(self, context: UpdateContext) -> UpdateNotice | None:
        if not context.install_root or not (context.install_root / ".git").exists():
            return None

        worktree = git_worktree_status(context.install_root)
        if not worktree["is_git"]:
            return None

        exact_tag = worktree["exact_tag"]
        branch = worktree["branch"] or "detached HEAD"
        commit = worktree["commit"] or "unknown"
        dirty = "dirty" if worktree["is_dirty"] else "clean"
        unreleased = bool(worktree["is_dirty"] or exact_tag != f"v{context.current_version}")
        if not unreleased:
            return None

        return UpdateNotice(
            available=True,
            checked=True,
            channel="working-tree",
            kind="revision",
            current_version=context.current_version,
            latest_version=context.current_version,
            release_url=GITHUB_RELEASE_URL,
            update_command=(
                f'git -C "{context.install_root}" status --short && '
                f'git -C "{context.install_root}" tag v{context.current_version} && '
                f'"{context.python_executable}" -m pip install "{context.install_root}"'
            ),
            install_command=None,
            install_root=str(context.install_root),
            summary=(
                f"Working tree build detected on {branch} ({commit}, {dirty}). "
                f"Tag or publish this revision to make it discoverable."
            ),
            auto_update_ready=False,
            source=self.name,
        )


class UpdatePipeline:
    def __init__(
        self,
        context: UpdateContext,
        sources: Iterable[UpdateSource] | None = None,
    ) -> None:
        self.context = context
        self.sources = list(
            sources
            or (
                ReleaseFeedSource(),
                GitTagSource(),
                PyPIReleaseSource(),
                WorkingTreeSource(),
            )
        )

    def build_notice(self) -> UpdateNotice:
        for source in self.sources:
            notice = source.build(self.context)
            if notice is not None:
                return notice
        return _default_notice(self.context)

    def apply(self, notice: UpdateNotice) -> dict[str, object]:
        if not notice.auto_update_ready:
            return {
                "ok": False,
                "channel": notice.channel,
                "error": "automatic update is not available for this notice",
                "step": "noop",
            }

        if notice.install_command:
            return self._apply_shell_update(notice.install_command, notice.channel)

        if notice.channel == "git" and self.context.install_root is not None:
            return self._apply_git_update()

        return self._apply_pypi_update()

    def _apply_shell_update(self, command_text: str, channel: str) -> dict[str, object]:
        try:
            command = shlex.split(command_text)
        except ValueError as exc:
            return {"ok": False, "channel": channel, "error": str(exc), "step": "parse command"}
        if not command:
            return {
                "ok": False,
                "channel": channel,
                "error": "empty install command",
                "step": "parse command",
            }

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            return {"ok": False, "channel": channel, "error": str(exc), "step": "install command"}

        if result.returncode != 0:
            return {
                "ok": False,
                "channel": channel,
                "error": (result.stderr or result.stdout or "install command failed").strip(),
                "step": "install command",
            }

        return {
            "ok": True,
            "channel": channel,
            "step": "install command",
            "output": (result.stdout or "").strip(),
        }

    def _apply_git_update(self) -> dict[str, object]:
        assert self.context.install_root is not None
        command = [
            "git",
            "-C",
            str(self.context.install_root),
            "pull",
            "--ff-only",
        ]
        try:
            git_pull = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            return {"ok": False, "channel": "git", "error": str(exc), "step": "git pull"}

        if git_pull.returncode != 0:
            return {
                "ok": False,
                "channel": "git",
                "error": (git_pull.stderr or git_pull.stdout or "git pull failed").strip(),
                "step": "git pull",
            }

        command = [
            self.context.python_executable,
            "-m",
            "pip",
            "install",
            str(self.context.install_root),
        ]
        try:
            pip_install = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            return {"ok": False, "channel": "git", "error": str(exc), "step": "pip install"}

        if pip_install.returncode != 0:
            return {
                "ok": False,
                "channel": "git",
                "error": (pip_install.stderr or pip_install.stdout or "pip install failed").strip(),
                "step": "pip install",
            }

        return {
            "ok": True,
            "channel": "git",
            "step": "git pull + pip install",
            "output": (pip_install.stdout or "").strip(),
        }

    def _apply_pypi_update(self) -> dict[str, object]:
        command = [
            self.context.python_executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            PACKAGE_NAME,
        ]
        try:
            pip_upgrade = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            return {"ok": False, "channel": "pypi", "error": str(exc), "step": "pip install"}

        if pip_upgrade.returncode != 0:
            return {
                "ok": False,
                "channel": "pypi",
                "error": (pip_upgrade.stderr or pip_upgrade.stdout or "pip install failed").strip(),
                "step": "pip install",
            }

        return {
            "ok": True,
            "channel": "pypi",
            "step": "pip install --upgrade",
            "output": (pip_upgrade.stdout or "").strip(),
        }


def build_update_notice(
    current_version: str, install_root: Path | None = None
) -> dict[str, object]:
    context = UpdateContext(
        current_version=current_version,
        install_root=install_root or detect_install_root(),
        feed_url=_release_feed_url(),
    )
    return UpdatePipeline(context).build_notice().as_dict()


def normalize_update_mode(value: str | None) -> str:
    mode = (value or DEFAULT_UPDATE_MODE).strip().lower()
    if mode in {AUTO_UPDATE_MODE, PROMPT_UPDATE_MODE, DISABLED_UPDATE_MODE}:
        return mode
    return DEFAULT_UPDATE_MODE


def apply_update(
    update_notice: dict[str, object], install_root: Path | None = None
) -> dict[str, object]:
    context = UpdateContext(
        current_version=str(update_notice.get("current_version") or ""),
        install_root=install_root or detect_install_root(),
        feed_url=_release_feed_url(),
    )
    notice = UpdateNotice(
        available=bool(update_notice.get("available")),
        checked=bool(update_notice.get("checked")),
        channel=str(update_notice.get("channel") or "pypi"),
        kind=str(update_notice.get("kind") or "package"),
        current_version=str(update_notice.get("current_version") or ""),
        latest_version=str(update_notice.get("latest_version") or ""),
        release_url=str(update_notice.get("release_url") or ""),
        update_command=str(update_notice.get("update_command") or ""),
        install_command=(
            str(update_notice.get("install_command"))
            if update_notice.get("install_command")
            else None
        ),
        install_root=(
            str(update_notice.get("install_root")) if update_notice.get("install_root") else None
        ),
        summary=str(update_notice.get("summary") or ""),
        auto_update_ready=bool(update_notice.get("auto_update_ready", True)),
        source=str(update_notice.get("source") or "unknown"),
    )
    return UpdatePipeline(context).apply(notice)
