#!/usr/bin/env python3
"""Report on and interactively prune dev-tool caches (Docker, Poetry, pip,
npm, Maven, Gradle, sbt/Ivy, Coursier, Terraform, Homebrew/apt, Trash) on
macOS and Ubuntu.

See docs/superpowers/specs/2026-09-12-dev-disk-cleanup-design.md for the
full design and the safety invariant this script follows.
"""
import os
import platform
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


def dir_size(path: Path) -> int:
    """Recursively sum the size in bytes of every regular file under
    `path`. Returns 0 if `path` doesn't exist. Symlinks are not followed
    and don't add to the total (only their real targets, if also present
    under `path`, are counted)."""
    if not path.exists():
        return 0
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda e: None):
        for name in files:
            file_path = Path(root) / name
            try:
                if not file_path.is_symlink():
                    total += file_path.stat().st_size
            except OSError:
                pass
    return total


def human_size(num_bytes: int) -> str:
    """Format a byte count as a short human-readable string, e.g. '4.5G'."""
    value = float(num_bytes)
    for unit in ("B", "K", "M", "G", "T"):
        if value < 1024 or unit == "T":
            return f"{value:.0f}B" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}T"  # unreachable, satisfies linters


def wipe_dir_contents(path: Path) -> int:
    """Delete every child of `path` (files and subdirectories) but keep
    `path` itself. Returns the number of bytes freed. Returns 0 if `path`
    doesn't exist."""
    if not path.exists():
        return 0
    freed = dir_size(path)
    for child in path.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink(missing_ok=True)
        else:
            shutil.rmtree(child, ignore_errors=True)
    return freed


def current_os() -> str:
    """Return 'mac', 'linux', or 'other' based on the running platform."""
    system = platform.system()
    if system == "Darwin":
        return "mac"
    if system == "Linux":
        return "linux"
    return "other"


class Tier(Enum):
    SAFE = "safe"
    DESTRUCTIVE = "destructive"


@dataclass
class Target:
    """A prunable cleanup target. `size_fn`/`prune_fn`/`present_fn` are
    zero-argument callables so discovery (Task 4) can bind each target to
    a specific path/command without the caller needing to know how."""

    key: str
    label: str
    tier: Tier
    size_fn: Callable[[], int]
    prune_fn: Callable[[], str]
    present_fn: Callable[[], bool]
    extra_report_fn: Optional[Callable[[], str]] = None


@dataclass
class InfoItem:
    """A report-only item (pyenv/sdkman version installs). Never selectable,
    never pruned by this script."""

    label: str
    size_fn: Callable[[], int]
    present_fn: Callable[[], bool]


def make_dir_wipe_target(
    key: str, label: str, tier: Tier, path_fn: Callable[[], Path]
) -> Target:
    """Build a Target whose prune action is deleting an entire directory
    tree outright. Used for pure download/build caches that the owning
    tool recreates lazily on next use (Poetry, pip, npm, Maven, Gradle,
    sbt/Ivy, Coursier, Terraform)."""

    def present() -> bool:
        return path_fn().exists()

    def size() -> int:
        return dir_size(path_fn())

    def prune() -> str:
        path = path_fn()
        freed = dir_size(path)
        shutil.rmtree(path, ignore_errors=True)
        return f"removed {path} ({human_size(freed)})"

    return Target(
        key=key, label=label, tier=tier, size_fn=size, prune_fn=prune, present_fn=present
    )


def parse_selection(raw: str, targets: list) -> list:
    """Parse a non-empty selection string against an ordered target list.

    '(a|all)' selects every target, safe and destructive alike.
    '(q|quit)' exits the process immediately (SystemExit(0)).
    Otherwise `raw` is treated as comma-separated 1-based indices into
    `targets`; invalid or out-of-range tokens are silently skipped.
    Callers are responsible for handling an *empty* raw string themselves
    (this function assumes there's something to parse).
    """
    cleaned = raw.strip().lower()
    if cleaned in ("q", "quit"):
        raise SystemExit(0)
    if cleaned in ("a", "all"):
        return list(targets)

    selected = []
    for part in cleaned.split(","):
        part = part.strip()
        if not part.isdigit():
            continue
        index = int(part) - 1
        if 0 <= index < len(targets):
            selected.append(targets[index])
    return selected


def filter_by_keys(keys: list, targets: list) -> list:
    """Return the subset of `targets` whose `.key` is in `keys`, preserving
    `targets`' original order."""
    key_set = set(keys)
    return [target for target in targets if target.key in key_set]
