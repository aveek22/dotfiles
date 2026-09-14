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
from pathlib import Path


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
