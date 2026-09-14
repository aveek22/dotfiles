# Dev Disk Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `scripts/disk-cleanup`, a Python 3 (stdlib-only) script that reports and interactively prunes dev-tool build/package caches (Docker, Poetry, pip, npm, Maven, Gradle, sbt/Ivy, Coursier, Terraform, Homebrew/apt, Trash) on both macOS and Ubuntu, wired to a `cleanup` alias.

**Architecture:** All logic lives in one importable module, `scripts/disk_cleanup.py`, built from small pure functions (size math, a directory-wipe target factory, selection parsing) plus an OS-aware target-discovery function and a `main()` CLI orchestrator. `scripts/disk-cleanup` is a thin executable shim that imports and calls `main()`. A `unittest` suite covers every pure function; the CLI/interactive loop and the three command-driven targets (`docker`, `brew`, `apt`) are verified manually since they depend on tools/daemons that may not exist on the machine running the tests.

**Tech Stack:** Python 3 standard library only (`os`, `shutil`, `subprocess`, `platform`, `pathlib`, `argparse`, `dataclasses`, `enum`, `unittest`). No third-party dependencies.

**Spec:** `docs/superpowers/specs/2026-09-12-dev-disk-cleanup-design.md`

## Global Constraints

- No third-party Python dependencies — stdlib only.
- Script must run unmodified on macOS and Ubuntu; anything OS/tool-specific must be gated by presence checks, never assumed.
- Safety invariant (from spec): a `destructive`-tier target only ever runs if the user explicitly names it (interactive number, or `--only=<key>`). Plain `--yes` with no `--only` must never run a destructive target.
- Maven/Gradle/Ivy caches: only wipe the pure-download subdirectory (`~/.m2/repository`, `~/.gradle/caches`, `~/.ivy2/cache`) — never `~/.m2/settings.xml`, `~/.gradle/wrapper`, `~/.gradle/daemon`, or `~/.ivy2/local`.
- Follow existing repo convention: standalone executables live in `scripts/`, aliased in `home/.alias` (see `scripts/kube`).

---

## Task 1: Core size/filesystem utilities

**Files:**
- Create: `scripts/disk_cleanup.py`
- Create: `scripts/test_disk_cleanup.py`

**Interfaces:**
- Produces: `dir_size(path: pathlib.Path) -> int`, `human_size(num_bytes: int) -> str`, `wipe_dir_contents(path: pathlib.Path) -> int`, `current_os() -> str` (returns `"mac"`, `"linux"`, or `"other"`). Later tasks import all four from `disk_cleanup`.

- [ ] **Step 1: Write the failing tests**

Create `scripts/test_disk_cleanup.py`:

```python
import platform
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import disk_cleanup as dc


class DirSizeTests(unittest.TestCase):
    def test_missing_path_is_zero(self):
        self.assertEqual(dc.dir_size(Path("/no/such/path/at/all")), 0)

    def test_sums_nested_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_bytes(b"x" * 100)
            sub = root / "sub"
            sub.mkdir()
            (sub / "b.txt").write_bytes(b"y" * 50)
            self.assertEqual(dc.dir_size(root), 150)

    def test_ignores_symlinked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real.txt"
            real.write_bytes(b"z" * 40)
            (root / "link.txt").symlink_to(real)
            # real.txt (40 bytes) counted once; the symlink itself isn't a
            # regular file's size, so total stays 40.
            self.assertEqual(dc.dir_size(root), 40)


class HumanSizeTests(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(dc.human_size(500), "500B")

    def test_kilobytes(self):
        self.assertEqual(dc.human_size(2048), "2.0K")

    def test_gigabytes(self):
        self.assertEqual(dc.human_size(4_800_000_000), "4.5G")


class WipeDirContentsTests(unittest.TestCase):
    def test_missing_path_returns_zero(self):
        self.assertEqual(dc.wipe_dir_contents(Path("/no/such/path")), 0)

    def test_removes_children_keeps_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trash"
            root.mkdir()
            (root / "file.txt").write_bytes(b"a" * 10)
            child_dir = root / "childdir"
            child_dir.mkdir()
            (child_dir / "nested.txt").write_bytes(b"b" * 5)

            freed = dc.wipe_dir_contents(root)

            self.assertEqual(freed, 15)
            self.assertTrue(root.exists())
            self.assertEqual(list(root.iterdir()), [])


class CurrentOsTests(unittest.TestCase):
    def test_darwin_maps_to_mac(self):
        with mock.patch.object(platform, "system", return_value="Darwin"):
            self.assertEqual(dc.current_os(), "mac")

    def test_linux_maps_to_linux(self):
        with mock.patch.object(platform, "system", return_value="Linux"):
            self.assertEqual(dc.current_os(), "linux")

    def test_other_maps_to_other(self):
        with mock.patch.object(platform, "system", return_value="Windows"):
            self.assertEqual(dc.current_os(), "other")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest scripts/test_disk_cleanup.py -v`
Expected: `ModuleNotFoundError: No module named 'disk_cleanup'` (the module doesn't exist yet).

- [ ] **Step 3: Write the minimal implementation**

Create `scripts/disk_cleanup.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest scripts/test_disk_cleanup.py -v`
Expected: `OK` — 11 tests passed (3 DirSizeTests, 3 HumanSizeTests, 2 WipeDirContentsTests, 3 CurrentOsTests).

- [ ] **Step 5: Commit**

```bash
git add scripts/disk_cleanup.py scripts/test_disk_cleanup.py
git commit -m "disk-cleanup: add core size/filesystem utilities"
```

---

## Task 2: Data model and directory-wipe target factory

**Files:**
- Modify: `scripts/disk_cleanup.py`
- Modify: `scripts/test_disk_cleanup.py`

**Interfaces:**
- Consumes: `dir_size`, `human_size` from Task 1 (same module, no import needed).
- Produces: `Tier` (enum with `SAFE`, `DESTRUCTIVE`), `Target` (dataclass: `key: str`, `label: str`, `tier: Tier`, `size_fn: Callable[[], int]`, `prune_fn: Callable[[], str]`, `present_fn: Callable[[], bool]`, `extra_report_fn: Optional[Callable[[], str]] = None`), `InfoItem` (dataclass: `label: str`, `size_fn: Callable[[], int]`, `present_fn: Callable[[], bool]`), `make_dir_wipe_target(key: str, label: str, tier: Tier, path_fn: Callable[[], Path]) -> Target`. Later tasks build `Target`/`InfoItem` instances and call `make_dir_wipe_target`.

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_disk_cleanup.py` (above the `if __name__ == "__main__":` line):

```python
class MakeDirWipeTargetTests(unittest.TestCase):
    def test_absent_path_is_not_present_and_size_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"
            target = dc.make_dir_wipe_target(
                "poetry", "Poetry cache", dc.Tier.SAFE, lambda: missing
            )
            self.assertFalse(target.present_fn())
            self.assertEqual(target.size_fn(), 0)

    def test_present_path_reports_size_and_prunes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            cache.mkdir()
            (cache / "file.bin").write_bytes(b"x" * 200)
            target = dc.make_dir_wipe_target(
                "poetry", "Poetry cache", dc.Tier.SAFE, lambda: cache
            )

            self.assertTrue(target.present_fn())
            self.assertEqual(target.size_fn(), 200)

            message = target.prune_fn()

            self.assertFalse(cache.exists())
            self.assertIn("200B", message)
            self.assertEqual(target.key, "poetry")
            self.assertEqual(target.tier, dc.Tier.SAFE)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest scripts/test_disk_cleanup.py -v`
Expected: `AttributeError: module 'disk_cleanup' has no attribute 'Tier'` (or `make_dir_wipe_target`).

- [ ] **Step 3: Write the minimal implementation**

Add to `scripts/disk_cleanup.py` (after the `current_os` function; add `from dataclasses import dataclass`, `from enum import Enum`, and `from typing import Callable, Optional` to the existing import block at the top):

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest scripts/test_disk_cleanup.py -v`
Expected: `OK` — 13 tests passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/disk_cleanup.py scripts/test_disk_cleanup.py
git commit -m "disk-cleanup: add Target/InfoItem model and dir-wipe factory"
```

---

## Task 3: Selection parsing and key filtering

**Files:**
- Modify: `scripts/disk_cleanup.py`
- Modify: `scripts/test_disk_cleanup.py`

**Interfaces:**
- Consumes: `Target`, `Tier` from Task 2.
- Produces: `parse_selection(raw: str, targets: list) -> list`, `filter_by_keys(keys: list, targets: list) -> list`. Task 5's `main()` calls both.

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_disk_cleanup.py`:

```python
def _make_target(key, tier=dc.Tier.SAFE):
    return dc.Target(
        key=key,
        label=key,
        tier=tier,
        size_fn=lambda: 0,
        prune_fn=lambda: "",
        present_fn=lambda: True,
    )


class ParseSelectionTests(unittest.TestCase):
    def setUp(self):
        self.targets = [
            _make_target("poetry"),
            _make_target("npm"),
            _make_target("docker-volumes", tier=dc.Tier.DESTRUCTIVE),
        ]

    def test_digit_indices_select_in_order(self):
        result = dc.parse_selection("1,3", self.targets)
        self.assertEqual([t.key for t in result], ["poetry", "docker-volumes"])

    def test_all_selects_every_target(self):
        result = dc.parse_selection("a", self.targets)
        self.assertEqual(result, self.targets)

    def test_all_word_also_works(self):
        result = dc.parse_selection("all", self.targets)
        self.assertEqual(result, self.targets)

    def test_quit_raises_system_exit(self):
        with self.assertRaises(SystemExit) as ctx:
            dc.parse_selection("q", self.targets)
        self.assertEqual(ctx.exception.code, 0)

    def test_invalid_and_out_of_range_tokens_are_ignored(self):
        result = dc.parse_selection("0,2,9,abc", self.targets)
        self.assertEqual([t.key for t in result], ["npm"])

    def test_whitespace_and_case_are_tolerated(self):
        result = dc.parse_selection(" 1 , 2 ", self.targets)
        self.assertEqual([t.key for t in result], ["poetry", "npm"])


class FilterByKeysTests(unittest.TestCase):
    def test_keeps_order_and_drops_unmatched(self):
        targets = [_make_target("poetry"), _make_target("npm"), _make_target("maven")]
        result = dc.filter_by_keys(["maven", "poetry"], targets)
        self.assertEqual([t.key for t in result], ["poetry", "maven"])

    def test_unknown_key_yields_empty(self):
        targets = [_make_target("poetry")]
        self.assertEqual(dc.filter_by_keys(["nope"], targets), [])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest scripts/test_disk_cleanup.py -v`
Expected: `AttributeError: module 'disk_cleanup' has no attribute 'parse_selection'`.

- [ ] **Step 3: Write the minimal implementation**

Add to `scripts/disk_cleanup.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest scripts/test_disk_cleanup.py -v`
Expected: `OK` — 21 tests passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/disk_cleanup.py scripts/test_disk_cleanup.py
git commit -m "disk-cleanup: add selection parsing and key filtering"
```

---

## Task 4: Per-OS target and info-item discovery

**Files:**
- Modify: `scripts/disk_cleanup.py`
- Modify: `scripts/test_disk_cleanup.py`

**Interfaces:**
- Consumes: `Tier`, `Target`, `InfoItem`, `make_dir_wipe_target`, `dir_size` from Tasks 1–2.
- Produces: `build_targets(os_name: str, home: Path) -> list`, `build_info_items(home: Path) -> list`. Task 5's `main()` calls both to build what the report/prompt operates on.

- [ ] **Step 1: Write the failing tests**

Add to `scripts/test_disk_cleanup.py`:

```python
class BuildTargetsTests(unittest.TestCase):
    def test_mac_includes_brew_not_apt(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets = dc.build_targets("mac", Path(tmp))
            keys = [t.key for t in targets]
            self.assertIn("brew", keys)
            self.assertNotIn("apt", keys)

    def test_linux_includes_apt_not_brew(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets = dc.build_targets("linux", Path(tmp))
            keys = [t.key for t in targets]
            self.assertIn("apt", keys)
            self.assertNotIn("brew", keys)

    def test_common_dir_wipe_keys_present_on_both_os(self):
        with tempfile.TemporaryDirectory() as tmp:
            common_keys = {
                "poetry", "pip", "npm", "maven", "gradle",
                "ivy2", "sbt-boot", "coursier", "terraform",
            }
            for os_name in ("mac", "linux"):
                keys = {t.key for t in dc.build_targets(os_name, Path(tmp))}
                self.assertTrue(common_keys.issubset(keys), os_name)

    def test_docker_and_trash_tiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets = {t.key: t for t in dc.build_targets("mac", Path(tmp))}
            self.assertEqual(targets["docker-safe"].tier, dc.Tier.SAFE)
            self.assertEqual(targets["docker-volumes"].tier, dc.Tier.DESTRUCTIVE)
            self.assertEqual(targets["trash"].tier, dc.Tier.DESTRUCTIVE)

    def test_maven_target_never_touches_settings_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            m2 = home / ".m2"
            m2.mkdir()
            (m2 / "settings.xml").write_text("<settings/>")
            repo = m2 / "repository"
            repo.mkdir()
            (repo / "some.jar").write_bytes(b"x" * 10)

            targets = {t.key: t for t in dc.build_targets("mac", home)}
            targets["maven"].prune_fn()

            self.assertTrue((m2 / "settings.xml").exists())
            self.assertFalse(repo.exists())

    def test_trash_wipes_contents_keeps_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            real_trash = home / ".Trash"
            real_trash.mkdir()
            (real_trash / "deleted.txt").write_bytes(b"x" * 5)

            targets = {t.key: t for t in dc.build_targets("mac", home)}
            targets["trash"].prune_fn()

            self.assertTrue(real_trash.exists())
            self.assertEqual(list(real_trash.iterdir()), [])


class BuildInfoItemsTests(unittest.TestCase):
    def test_reports_pyenv_and_sdkman_sizes_without_pruning(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            versions = home / ".pyenv" / "versions" / "3.11.0"
            versions.mkdir(parents=True)
            (versions / "python").write_bytes(b"x" * 30)

            items = dc.build_info_items(home)
            pyenv_item = next(i for i in items if "pyenv" in i.label.lower())

            self.assertTrue(pyenv_item.present_fn())
            self.assertEqual(pyenv_item.size_fn(), 30)
            self.assertFalse(hasattr(pyenv_item, "prune_fn"))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest scripts/test_disk_cleanup.py -v`
Expected: `AttributeError: module 'disk_cleanup' has no attribute 'build_targets'`.

- [ ] **Step 3: Write the minimal implementation**

Add to `scripts/disk_cleanup.py` (add `import subprocess` to the top import block):

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest scripts/test_disk_cleanup.py -v`
Expected: `OK` — 28 tests passed. (Note: `test_docker_and_trash_tiers` and any docker-present tests don't require Docker to actually be installed — they only check `tier`, not `present_fn()`.)

- [ ] **Step 5: Commit**

```bash
git add scripts/disk_cleanup.py scripts/test_disk_cleanup.py
git commit -m "disk-cleanup: add per-OS target and info-item discovery"
```

---

## Task 5: Report rendering, CLI, and executable shim

**Files:**
- Modify: `scripts/disk_cleanup.py`
- Create: `scripts/disk-cleanup`

**Interfaces:**
- Consumes: everything from Tasks 1–4 (`Tier`, `Target`, `InfoItem`, `build_targets`, `build_info_items`, `parse_selection`, `filter_by_keys`, `human_size`, `current_os`).
- Produces: `main() -> None`, the CLI entry point. `scripts/disk-cleanup` imports and calls it.

No new unit tests in this task — `main()` is an I/O-driving orchestrator (argparse, `input()`, `print()`) covered by manual verification in Task 5's Step 4, consistent with the spec's testing strategy.

- [ ] **Step 1: Write `main()` and supporting report/prune helpers**

Add to `scripts/disk_cleanup.py` (add `import argparse` to the top import block):

```python
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
```

- [ ] **Step 2: Create the executable shim**

Create `scripts/disk-cleanup`:

```python
#!/usr/bin/env python3
"""Thin executable entry point -- see disk_cleanup.py for all logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disk_cleanup import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Make the shim executable**

```bash
chmod +x scripts/disk-cleanup
```

- [ ] **Step 4: Manual verification (no automated test for the CLI/IO layer)**

Run each of these on the current machine and confirm the output looks right (this is the integration coverage the spec calls for, in place of mocking `docker`/`brew`/`apt`):

```bash
python3 -m unittest scripts/test_disk_cleanup.py -v   # still all green after this task's edits
./scripts/disk-cleanup --list                          # prints key/tier/label rows, no size computation
./scripts/disk-cleanup --dry-run                        # prints the full sized report, exits without prompting
```

Expected for `--dry-run`: every present target appears with a non-crashing size (mac targets you don't have installed, e.g. sbt-boot if never used, show `0B`), the two info lines appear under "Informational only," and the apt/brew row (whichever applies) prints without error even if the daemon/tool has nothing to clean.

Then, on a machine where it's safe to actually delete something (e.g. a Poetry or pip cache you don't mind rebuilding):

```bash
./scripts/disk-cleanup          # interactive: accept the default safe-tier preselection, confirm, watch it prune
```

Expected: the previously-reported cache directory is gone (or, for Docker/Homebrew/apt, their own tool output appears confirming what was reclaimed).

- [ ] **Step 5: Commit**

```bash
git add scripts/disk_cleanup.py scripts/disk-cleanup
git commit -m "disk-cleanup: add report rendering, CLI, and executable entry point"
```

---

## Task 6: Wire up the alias and update repo documentation

**Files:**
- Modify: `home/.alias`
- Modify: `CLAUDE.md`

**Interfaces:** None — this task only wires the finished script into the shell and documents it; no new functions.

- [ ] **Step 1: Add the alias**

In `home/.alias`, add this line near the existing `kube` alias (`home/.alias:92`, `alias kube="~/dotfiles/scripts/kube"`):

```bash
alias cleanup="~/dotfiles/scripts/disk-cleanup"
```

- [ ] **Step 2: Verify the alias resolves**

```bash
source ~/.alias 2>/dev/null || true   # or: source ~/.zshrc
type cleanup
```

Expected: `cleanup is an alias for ~/dotfiles/scripts/disk-cleanup`.

- [ ] **Step 3: Update the CLAUDE.md file map**

In `CLAUDE.md`, add a row to the "File map" table (after the `scripts/kube` row):

```markdown
| `scripts/disk-cleanup` | Interactive disk-space cleanup for dev-tool caches (Docker, Poetry, pip, npm, Maven, Gradle, sbt/Ivy, Coursier, Terraform, Homebrew/apt, Trash) — logic in `scripts/disk_cleanup.py`, aliased as `cleanup` |
```

- [ ] **Step 4: Commit**

```bash
git add home/.alias CLAUDE.md
git commit -m "disk-cleanup: add cleanup alias and document in CLAUDE.md"
```
