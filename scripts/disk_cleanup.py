#!/usr/bin/env python3
"""Report on and interactively prune dev-tool caches (Docker, Poetry, pip,
npm, Maven, Gradle, sbt/Ivy, Coursier, Terraform, Homebrew/apt, Trash) on
macOS and Ubuntu.

See docs/superpowers/specs/2026-09-12-dev-disk-cleanup-design.md for the
full design and the safety invariant this script follows.
"""
import argparse
import os
import platform
import shutil
import subprocess
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


_DIR_WIPE_SPECS = {
    "mac": [
        ("poetry", "Poetry cache + virtualenvs", "Library/Caches/pypoetry"),
        ("pip", "pip cache", "Library/Caches/pip"),
        ("npm", "npm cache", ".npm"),
        ("maven", "Maven repository cache", ".m2/repository"),
        ("gradle", "Gradle caches", ".gradle/caches"),
        ("ivy2", "sbt/Ivy dependency cache", ".ivy2/cache"),
        ("sbt-boot", "sbt launcher/boot cache", ".sbt/boot"),
        ("coursier", "Coursier cache", "Library/Caches/Coursier"),
        ("terraform", "Terraform provider plugin cache", ".terraform.d/plugin-cache"),
    ],
    "linux": [
        ("poetry", "Poetry cache + virtualenvs", ".cache/pypoetry"),
        ("pip", "pip cache", ".cache/pip"),
        ("npm", "npm cache", ".npm"),
        ("maven", "Maven repository cache", ".m2/repository"),
        ("gradle", "Gradle caches", ".gradle/caches"),
        ("ivy2", "sbt/Ivy dependency cache", ".ivy2/cache"),
        ("sbt-boot", "sbt launcher/boot cache", ".sbt/boot"),
        ("coursier", "Coursier cache", ".cache/coursier"),
        ("terraform", "Terraform provider plugin cache", ".terraform.d/plugin-cache"),
    ],
}


def _run(cmd: list) -> str:
    """Run `cmd`, returning combined stdout+stderr (stripped). Never raises
    on a non-zero exit -- callers only care about the human-readable
    output, not the return code."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return (result.stdout + result.stderr).strip()


def _docker_daemon_running() -> bool:
    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    return result.returncode == 0


def _apt_autoremove_preview() -> str:
    return _run(["apt-get", "autoremove", "--dry-run"])


def build_targets(os_name: str, home: Path) -> list:
    """Build the full list of prunable Targets for this machine. Anything
    not applicable to `os_name`, or whose underlying tool isn't installed,
    still appears in the list but with `present_fn()` returning False --
    callers filter on that before displaying/selecting."""
    targets = []

    for key, label, rel_path in _DIR_WIPE_SPECS.get(os_name, []):
        targets.append(
            make_dir_wipe_target(
                key, label, Tier.SAFE, (lambda h=home, r=rel_path: h / r)
            )
        )

    def docker_present() -> bool:
        return shutil.which("docker") is not None and _docker_daemon_running()

    targets.append(
        Target(
            key="docker-safe",
            label="Docker: stopped containers, unused images, build cache",
            tier=Tier.SAFE,
            size_fn=lambda: 0,  # docker reports its own reclaimed size after pruning
            prune_fn=lambda: _run(["docker", "system", "prune", "-af"]),
            present_fn=docker_present,
        )
    )
    targets.append(
        Target(
            key="docker-volumes",
            label="Docker: unused volumes",
            tier=Tier.DESTRUCTIVE,
            size_fn=lambda: 0,
            prune_fn=lambda: _run(["docker", "volume", "prune", "-f"]),
            present_fn=docker_present,
        )
    )

    trash_path = home / ".Trash" if os_name == "mac" else home / ".local" / "share" / "Trash"
    targets.append(
        Target(
            key="trash",
            label="Trash contents",
            tier=Tier.DESTRUCTIVE,
            size_fn=lambda: dir_size(trash_path),
            prune_fn=lambda: f"emptied {trash_path} ({human_size(wipe_dir_contents(trash_path))})",
            present_fn=lambda: trash_path.exists(),
        )
    )

    if os_name == "mac":
        brew_cache = home / "Library" / "Caches" / "Homebrew"
        targets.append(
            Target(
                key="brew",
                label="Homebrew old versions + cache",
                tier=Tier.SAFE,
                size_fn=lambda: dir_size(brew_cache),
                prune_fn=lambda: _run(["brew", "cleanup", "-s"]),
                present_fn=lambda: shutil.which("brew") is not None,
            )
        )
    elif os_name == "linux":
        apt_cache = Path("/var/cache/apt/archives")
        targets.append(
            Target(
                key="apt",
                label="apt package cache + unneeded auto-installed packages",
                tier=Tier.SAFE,
                size_fn=lambda: dir_size(apt_cache),
                prune_fn=lambda: _run(["sudo", "apt-get", "clean"])
                + "\n"
                + _run(["sudo", "apt-get", "autoremove", "-y"]),
                present_fn=lambda: shutil.which("apt-get") is not None,
                extra_report_fn=_apt_autoremove_preview,
            )
        )

    return targets


def build_info_items(home: Path) -> list:
    """Build the report-only info items: pyenv/sdkman installed-version
    sizes. Never selectable, never pruned by this script."""
    pyenv_versions = home / ".pyenv" / "versions"
    sdkman_candidates = home / ".sdkman" / "candidates"
    return [
        InfoItem(
            label="pyenv installed Python versions (not pruned here)",
            size_fn=lambda: dir_size(pyenv_versions),
            present_fn=lambda: pyenv_versions.exists(),
        ),
        InfoItem(
            label="sdkman installed candidates (not pruned here)",
            size_fn=lambda: dir_size(sdkman_candidates),
            present_fn=lambda: sdkman_candidates.exists(),
        ),
    ]


_HELP_EPILOGUE = """\
Safety note: destructive-tier targets (Docker volumes, Trash contents) are
never run by --yes alone -- you must name them explicitly, either as a
number at the interactive prompt or via --only=<key>.

Caveat: Maven/Gradle/sbt/Ivy caches are pure download caches EXCEPT for
artifacts installed locally with no upstream source (e.g. Maven's
`install:install-file`). Those live only in ~/.m2/repository and are lost
if it's wiped -- this script cannot detect that case automatically.
"""


def _print_report(targets: list, info_items: list) -> None:
    present = [t for t in targets if t.present_fn()]
    print(f"{'#':>2}  {'target':<50} {'size':>8}  tier")
    for index, target in enumerate(present, start=1):
        size = human_size(target.size_fn())
        tag = "⚠ destructive" if target.tier is Tier.DESTRUCTIVE else "safe"
        print(f"{index:>2}  {target.label:<50} {size:>8}  {tag}")
        if target.extra_report_fn is not None:
            detail = target.extra_report_fn()
            if detail:
                print(f"      {detail}")

    present_info = [i for i in info_items if i.present_fn()]
    if present_info:
        print("\nInformational only (not prunable here):")
        for item in present_info:
            print(f"    {item.label}: {human_size(item.size_fn())}")


def _run_selected(selected: list) -> None:
    # Directory-wipe targets embed the freed amount in their own returned
    # message; command-driven targets (docker/brew/apt) print the tool's
    # own report instead. Either way there's nothing to sum here -- just
    # surface each target's message as it runs.
    for target in selected:
        print(f"\n--- {target.label} ---")
        print(target.prune_fn() or "(done)")
    print("\nDone. See per-target output above for space freed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="disk-cleanup",
        description="Report on and interactively prune dev-tool caches.",
        epilog=_HELP_EPILOGUE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the size report and exit."
    )
    parser.add_argument(
        "--list", action="store_true", help="Print target keys/labels/tiers and exit."
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip the prompt and prune every present safe-tier target.",
    )
    parser.add_argument(
        "--only", default=None,
        help="Comma-separated target keys to prune (naming a destructive key is its explicit opt-in).",
    )
    args = parser.parse_args()

    os_name = current_os()
    home = Path.home()
    targets = [t for t in build_targets(os_name, home) if t.present_fn()]
    info_items = build_info_items(home)

    if args.list:
        for target in targets:
            tag = "destructive" if target.tier is Tier.DESTRUCTIVE else "safe"
            print(f"{target.key}\t{tag}\t{target.label}")
        return

    _print_report(targets, info_items)

    if args.dry_run:
        return

    if args.only:
        keys = [k.strip() for k in args.only.split(",") if k.strip()]
        selected = filter_by_keys(keys, targets)
    elif args.yes:
        selected = [t for t in targets if t.tier is Tier.SAFE]
    else:
        preselected = [t for t in targets if t.tier is Tier.SAFE]
        indices = ",".join(str(targets.index(t) + 1) for t in preselected)
        prompt = (
            f'\nSelected: {indices}. Press Enter to confirm, type new '
            'comma-separated numbers to change (e.g. "1,3,9"), "a" for all '
            '(including ⚠ destructive), or "q" to quit: '
        )
        raw = input(prompt)
        selected = preselected if raw.strip() == "" else parse_selection(raw, targets)

        if not selected:
            print("Nothing selected, exiting.")
            return

        total = human_size(sum(t.size_fn() for t in selected))
        confirm = input(f"\nWill prune {len(selected)} target(s), ~{total}. Proceed? [y/N] ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("Aborted, nothing changed.")
            return

    if not selected:
        print("Nothing selected, exiting.")
        return

    _run_selected(selected)


if __name__ == "__main__":
    main()
