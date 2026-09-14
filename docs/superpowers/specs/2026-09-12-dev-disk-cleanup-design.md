# Dev Disk Cleanup — Design

**Status:** Approved for implementation (2026-09-12)

## Problem

The user works across many tech stacks (Docker, Terraform, Python/Poetry, Java/Maven, Gradle, Scala/sbt) on two MacBooks and one Ubuntu machine. Each stack's build/package caches grow large over time (survey on the primary Mac found: Homebrew cache 10G, `.terraform.d/plugin-cache` 4.6G, Coursier cache 3.4G, pypoetry cache 4G, `.npm` 1.3G, `.gradle` 830M, plus a 66G Docker Desktop data volume only reclaimable via `docker` commands). There is no existing tool in this repo to reclaim this space; the user wants one script, triggered manually every so often, that works unmodified on all three machines.

## Goals

- Single script, `scripts/disk-cleanup`, written in Python 3 (stdlib only — no third-party dependencies), following the existing pattern of standalone executables in `scripts/` (see `scripts/kube`).
- Runs unmodified on macOS and Ubuntu: detects the OS and which tools are actually installed, silently skipping anything absent.
- Reports space used by every target *before* changing anything (dry-run pass), then lets the user choose what to prune via an interactive numbered selection — never prunes anything by silently assuming consent.
- Never destroys real user data without an explicit, deliberate choice. See **Safety invariant** below.

## Non-goals

- Removing installed language/SDK versions (pyenv Python versions, sdkman Java/Scala/sbt candidates). Choosing which old version is safe to remove needs human judgment about which projects still depend on it — this script only *reports* their total size, never deletes them.
- Replacing `brew bundle`, `apt`, or any package manager's normal install/upgrade flow. This script only cleans caches and unreferenced data.

## Target inventory

Two kinds of entries:

1. **Targets** — selectable, prunable. Each has a `tier`: `safe` (recreatable from the network on next use, no real data loss possible) or `destructive` (can delete data that has no other copy).
2. **Info items** — reported for visibility only, never selectable, never pruned.

| Key | Label | Tier | macOS path/command | Ubuntu path/command |
|---|---|---|---|---|
| `docker-safe` | Docker: stopped containers, unused images, build cache | safe | `docker system prune -af` | same |
| `docker-volumes` | Docker: unused volumes | **destructive** | `docker volume prune -f` | same |
| `poetry` | Poetry cache + virtualenvs | safe | `~/Library/Caches/pypoetry` | `~/.cache/pypoetry` |
| `pip` | pip cache | safe | `~/Library/Caches/pip` | `~/.cache/pip` |
| `npm` | npm cache | safe | `~/.npm` | same |
| `maven` | Maven repository cache | safe* | `~/.m2/repository` only (never `~/.m2/settings.xml`) | same |
| `gradle` | Gradle caches | safe | `~/.gradle/caches` only (never `wrapper/`, `daemon/`) | same |
| `ivy2` | sbt/Ivy dependency cache | safe | `~/.ivy2/cache` only (never `~/.ivy2/local` — that's `publishLocal` output) | same |
| `sbt-boot` | sbt launcher/boot cache | safe | `~/.sbt/boot` | same |
| `coursier` | Coursier cache | safe | `~/Library/Caches/Coursier` | `~/.cache/coursier` |
| `terraform` | Terraform provider plugin cache | safe | `~/.terraform.d/plugin-cache` | same |
| `brew` | Homebrew old versions + cache | safe | `brew cleanup -s` (macOS only; absent target on Linux) | n/a |
| `apt` | apt package cache + unneeded auto-installed packages | safe | n/a | `sudo apt-get clean && sudo apt-get autoremove -y` (Ubuntu only) |
| `trash` | Trash / Recycle bin contents | **destructive** | empty contents of `~/.Trash` | empty contents of `~/.local/share/Trash/{files,info}` |

Info items (report-only, never in the selection list):
- pyenv installed Python versions — total size of `~/.pyenv/versions`
- sdkman installed candidates — total size of `~/.sdkman/candidates`

\* Maven/Gradle/Ivy caches are pure download caches *except* for one edge case: artifacts installed locally with no upstream source (e.g. `mvn install:install-file`) live only in `~/.m2/repository` and are lost if it's wiped. The script cannot detect this automatically; the risk is documented once in the script's `--help` text so the user sees it before ever running the tool.

## Safety invariant

> A `destructive`-tier target only ever runs if the user explicitly names it — either by typing its number in the interactive prompt, or by naming its key via `--only=<key>` on the command line. Plain `--yes` with no `--only` runs every `safe`-tier target and **excludes every `destructive`-tier target**, with no exception.

This makes automation (`--yes`, e.g. bound to the `cleanup` alias for a quick habitual run) safe by construction — there is no flag combination that silently deletes volumes or empties the Trash.

## CLI

```
disk-cleanup                 # interactive: dry-run report, then a selection prompt, then confirm, then prune
disk-cleanup --dry-run        # report only, no prompt, exits after printing sizes
disk-cleanup --list           # print target keys/labels/tiers only, no size computation, no prune
disk-cleanup --yes            # skip the prompt, prune every safe-tier present target, no destructive targets
disk-cleanup --only=poetry,npm,docker-volumes   # prune exactly these keys (explicit naming permits destructive keys)
```

`--yes` and `--only` may be combined (`--only` limits the safe-tier default set; naming a destructive key inside `--only` is the explicit opt-in for it, consistent with the interactive path).

## Flow (interactive, default)

1. Detect OS (`platform.system()` → `mac` / `linux`), build the target + info-item list for this machine, skipping anything not present (tool missing, or path/command not applicable to this OS).
2. For every present target, compute current size (a full pass, no mutation) and print a numbered table: `#`, label, size, tier tag (destructive rows marked `⚠`). Print apt's `apt-get autoremove --dry-run` package list directly under the apt row, if apt is a present target, so its removals are visible before any decision. Print the two info items' sizes below the table, clearly marked "informational only, not prunable here."
3. Pre-select every `safe`-tier target (by index). Prompt:
   `Selected: 1,2,3,5,7,8,9,10. Press Enter to confirm, type new comma-separated numbers to change (e.g. "1,3,9"), "a" for all (including ⚠ destructive), or "q" to quit:`
4. Re-parse input if non-empty; empty input keeps the pre-selection. Echo the final selection and its total size, ask one last `Proceed? [y/N]`.
5. Run each selected target's prune action in order, printing what it reports (freed bytes for directory-wipe targets; the underlying tool's own stdout for command-driven targets: `docker`, `brew`, `apt`).
6. Print a final summary: total freed (best-effort sum; command-driven targets whose freed amount isn't easily parsed are listed as "see output above" rather than guessed).

## File layout

- `scripts/disk_cleanup.py` — all logic (importable module: utilities, data model, target discovery, CLI/report/prune orchestration). Kept as one file to match this repo's existing single-file scripts (`scripts/kube`); if it grows unwieldy later, splitting is a follow-up, not part of this change.
- `scripts/disk-cleanup` — thin executable shim (`chmod +x`, `#!/usr/bin/env python3`) that imports `disk_cleanup.main` and calls it. The extensionless name matches the `scripts/kube` convention; the `.py` module sits alongside it so tests can import it directly.
- `scripts/test_disk_cleanup.py` — `unittest` suite covering the pure/testable pieces (size math, the directory-wipe target factory against temp directories, selection parsing, per-OS target-list structure). Command-driven prune actions (`docker`, `brew`, `apt`) and the interactive prompt loop are integration-level and are verified manually (`--dry-run`/`--list` on a real machine) rather than unit-tested, since they depend on tools/daemons that may not be present or running.
- `home/.alias` — add `alias cleanup="~/dotfiles/scripts/disk-cleanup"`.
- `CLAUDE.md` — add a row to the file map table for `scripts/disk-cleanup` and `scripts/disk_cleanup.py`.

## Testing strategy

Pure-logic unit tests only (stdlib `unittest`, no new dependency):
- `dir_size()` / `human_size()` against real temp directories/files.
- `wipe_dir_contents()` (used for Trash — empties contents, keeps the directory itself) against a temp directory.
- The directory-wipe target factory (`present_fn`/`size_fn`/`prune_fn`) against a temp directory standing in for `home`.
- `parse_selection()` — digits, `"a"`/`"all"`, `"q"`/`"quit"`, invalid/out-of-range input.
- `filter_by_keys()`.
- `build_targets()` / `build_info_items()` structural shape per OS — right keys present/absent per OS, correct tiers, without invoking any real `prune_fn`.

No mocking of `docker`/`brew`/`apt`/`pip`/`npm` subprocess calls — these are exercised manually via `--dry-run` and `--list` on the real machines after implementation, per the Manual Verification step in the plan.
