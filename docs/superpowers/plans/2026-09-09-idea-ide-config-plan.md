# IntelliJ IDEA Config in Dotfiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize IntelliJ IDEA settings, keymap/shortcuts, color scheme, code style, and templates in `dotfiles/ide/idea`, symlinked live into IntelliJ's config directory, so a work Mac and a personal Mac converge via git — mirroring the existing `ide/vscode` setup.

**Architecture:** Two symlink strategies in one pair of scripts (`apply`/`export`), driven by a single source-of-truth list in `lib.sh`: whole-directory symlinks for areas where everything inside is inherently a deliberate customization (`keymaps/`, `colors/`, `templates/`, `fileTemplates/`, `codestyles/`), and curated individual-file symlinks for a fixed allowlist of `options/*.xml` files. `plugins.txt` is a reference-only snapshot, never consumed by `apply`. `idea_config_dir()` auto-resolves the newest `IntelliJIdea<version>` directory so upgrades need no edits.

**Tech Stack:** Bash (`set -euo pipefail`), GNU Make, no external dependencies. Tests are plain Bash scripts using fake `$HOME` fixtures — no test framework.

**Spec:** `docs/superpowers/specs/2026-09-09-idea-ide-config-design.md`

## Global Constraints

- macOS only — no OS-branching in `idea_config_dir()` (unlike `vscode_user_dir()`); both target machines are Macs.
- Never write plugin-install/uninstall logic anywhere in `apply`. Plugin management is fully manual, by design.
- `IDEA_OPTION_FILES` (in `lib.sh`) is the single source of truth for which `options/*.xml` files are tracked — both `apply` and `export` iterate the same array. Adding to it is a manual, reviewed, one-line edit — never automatic.
- `idea_config_dir()` always resolves the newest `IntelliJIdea<version>` directory by sorting version-string directory names — never a hardcoded version.
- `plugins.txt` is regenerated **unconditionally** on every `export` run (reference snapshot only) — `apply` must never read it.
- These files must never appear in `IDEA_OPTION_FILES` or otherwise be tracked: `ide.general.xml`, `github.xml`, `gitlab.xml`, `nodejs.xml`, `path.macros.xml`, `jdk.table.xml`, `proxy.settings.xml`, `databaseDrivers.xml`, `databaseSettings.xml`, `remote-servers.xml`.
- Every script backs up a pre-existing real file/directory (`<path>.bak-<timestamp>`) before replacing it with a symlink — never destroys data silently.

---

### Task 1: `lib.sh` + test fixtures + version-dir resolution

**Files:**
- Create: `ide/idea/lib.sh`
- Create: `ide/idea/tests/fixtures.sh`
- Test: `ide/idea/tests/test_lib.sh`

**Interfaces:**
- Consumes: nothing (first task).
- Produces (for later tasks to source):
  - `lib.sh`: `IDEA_OPTION_FILES` (bash array of filenames), `IDEA_WHOLE_DIRS` (bash array of directory names: `keymaps colors templates fileTemplates codestyles`), `idea_config_dir()` (no args; prints the newest `IntelliJIdea<version>` dir path to stdout and returns 0, or prints an error to stderr and returns 1 if none exists).
  - `tests/fixtures.sh`: `setup_fake_idea_env()` (sets and exports `TMP_TEST_DIR`, `FAKE_HOME`, `FAKE_OLD_CONFIG_DIR`, `FAKE_CONFIG_DIR`; overrides `HOME`), `teardown_fake_idea_env()` (removes `TMP_TEST_DIR`), `stage_fake_repo_dir(real_repo_dir)` (copies `export`/`apply`/`lib.sh` into a scratch dir, sets `FAKE_REPO_DIR`).

- [ ] **Step 1: Write the failing test for `idea_config_dir()` version resolution**

Create `ide/idea/tests/test_lib.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/fixtures.sh"

real_repo_dir="$dir/.."
setup_fake_idea_env
trap teardown_fake_idea_env EXIT
source "$real_repo_dir/lib.sh"

# 1. resolves the newest version dir when multiple exist
result="$(idea_config_dir)"
if [ "$result" != "$FAKE_CONFIG_DIR" ]; then
    echo "FAIL: expected newest config dir '$FAKE_CONFIG_DIR', got '$result'"
    exit 1
fi

# 2. errors clearly when no config dir exists at all
teardown_fake_idea_env
tmp="$(mktemp -d)"
export TMP_TEST_DIR="$tmp"
export HOME="$tmp/home"
mkdir -p "$HOME"
if idea_config_dir >/dev/null 2>&1; then
    echo "FAIL: idea_config_dir should have failed with no config dir present"
    exit 1
fi
rm -rf "$tmp"

echo "PASS: test_lib.sh"
```

- [ ] **Step 2: Write the fixtures file the test depends on**

Create `ide/idea/tests/fixtures.sh`:

```bash
#!/usr/bin/env bash
# Shared test fixture helpers for idea export/apply tests. Sourced, not
# executed.

# Creates a temp fake $HOME with a fake IntelliJIdea2026.2 config directory
# (plus an older IntelliJIdea2026.1 to exercise newest-wins resolution).
# Exported: FAKE_HOME, FAKE_CONFIG_DIR, FAKE_OLD_CONFIG_DIR, TMP_TEST_DIR.
# Overrides HOME.
setup_fake_idea_env() {
    local tmp
    tmp="$(mktemp -d)"
    export TMP_TEST_DIR="$tmp"
    export FAKE_HOME="$tmp/home"
    export FAKE_OLD_CONFIG_DIR="$FAKE_HOME/Library/Application Support/JetBrains/IntelliJIdea2026.1"
    export FAKE_CONFIG_DIR="$FAKE_HOME/Library/Application Support/JetBrains/IntelliJIdea2026.2"
    mkdir -p "$FAKE_OLD_CONFIG_DIR/options" "$FAKE_CONFIG_DIR/options" "$FAKE_CONFIG_DIR/plugins"
    export HOME="$FAKE_HOME"
}

teardown_fake_idea_env() {
    rm -rf "$TMP_TEST_DIR"
}

# Copies the real export/apply/lib.sh into a scratch dir so tests never
# write into the real ide/idea/ files. Sets FAKE_REPO_DIR.
stage_fake_repo_dir() {
    local real_repo_dir="$1"
    local staged="$TMP_TEST_DIR/repo"
    mkdir -p "$staged"
    for f in export apply lib.sh; do
        if [ -f "$real_repo_dir/$f" ]; then
            cp "$real_repo_dir/$f" "$staged/"
            chmod +x "$staged/$f" 2>/dev/null || true
        fi
    done
    export FAKE_REPO_DIR="$staged"
}
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `bash ide/idea/tests/test_lib.sh`
Expected: FAIL — `lib.sh: No such file or directory` (it doesn't exist yet).

- [ ] **Step 4: Write `lib.sh`**

Create `ide/idea/lib.sh`:

```bash
#!/usr/bin/env bash
# Shared helpers for the idea export/apply scripts. Sourced, not executed.

# The curated allowlist of options/*.xml files considered safe and portable
# to sync (see docs/superpowers/specs/2026-09-09-idea-ide-config-design.md
# for the excluded-file rationale). Single source of truth for both export
# (bootstrap) and apply (symlink) — add to this list, never hardcode a
# second copy elsewhere.
IDEA_OPTION_FILES=(
    colors.scheme.xml console-font.xml editor-font.xml terminal-font.xml
    ui.lnf.xml find.xml findUsages.xml diff.xml debugger.xml
    filetypes.xml overrideFileTypes.xml csvSettings.xml git_toolbox_blame.xml
    javaRuleManager.xml scala.xml scala_config.xml spellchecker-dictionary.xml
    textmate.xml advancedSettings.xml avro_idl.xml
)

# The whole-directory areas where everything inside is inherently a
# deliberate customization — symlinked as directories, not curated
# file-by-file (see design spec, "Sync mechanism: two-tier symlinks").
IDEA_WHOLE_DIRS=(keymaps colors templates fileTemplates codestyles)

# Prints the absolute path to the newest IntelliJIdea<version> config
# directory under ~/Library/Application Support/JetBrains/. Exits non-zero
# if none exists yet (fresh machine, IDE never launched).
idea_config_dir() {
    local found
    found="$(ls -d "$HOME/Library/Application Support/JetBrains/IntelliJIdea"* 2>/dev/null | sort -V | tail -1)"
    if [ -z "$found" ]; then
        echo "idea: no IntelliJIdea config directory found under ~/Library/Application Support/JetBrains/" >&2
        echo "  Launch IntelliJ IDEA at least once so it creates its config directory, then re-run." >&2
        return 1
    fi
    echo "$found"
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `bash ide/idea/tests/test_lib.sh`
Expected: `PASS: test_lib.sh`

- [ ] **Step 6: Commit**

```bash
cd ide/idea
chmod +x tests/test_lib.sh
git add lib.sh tests/fixtures.sh tests/test_lib.sh
git commit -m "Add idea lib.sh with version-dir resolution and shared test fixtures

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `apply` script

**Files:**
- Create: `ide/idea/apply`
- Test: `ide/idea/tests/test_apply.sh`

**Interfaces:**
- Consumes: `lib.sh`'s `IDEA_OPTION_FILES`, `IDEA_WHOLE_DIRS`, `idea_config_dir()` (Task 1). `tests/fixtures.sh`'s `setup_fake_idea_env()`, `teardown_fake_idea_env()`, `stage_fake_repo_dir()` (Task 1).
- Produces: executable `apply` script. Backup naming convention `<path>.bak-<timestamp>` (via `date +%Y%m%d%H%M%S`), reused verbatim by `export`'s tests/docs in later tasks.

- [ ] **Step 1: Write the failing test**

Create `ide/idea/tests/test_apply.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/fixtures.sh"

real_repo_dir="$dir/.."
setup_fake_idea_env
trap teardown_fake_idea_env EXIT
stage_fake_repo_dir "$real_repo_dir"

# minimal repo content to apply: one whole-dir with content, one curated
# options file
mkdir -p "$FAKE_REPO_DIR/keymaps" "$FAKE_REPO_DIR/colors" "$FAKE_REPO_DIR/templates" "$FAKE_REPO_DIR/fileTemplates" "$FAKE_REPO_DIR/codestyles" "$FAKE_REPO_DIR/options"
echo '<keymap name="Mine" />' > "$FAKE_REPO_DIR/keymaps/Mine.xml"
echo '<application><component name="Test" /></application>' > "$FAKE_REPO_DIR/options/find.xml"

# pre-existing real (non-symlinked) keymaps/ dir and find.xml — must be
# backed up, not destroyed
mkdir -p "$FAKE_CONFIG_DIR/keymaps"
echo '<keymap name="Old" />' > "$FAKE_CONFIG_DIR/keymaps/Old.xml"
echo '<application><component name="Old" /></application>' > "$FAKE_CONFIG_DIR/options/find.xml"

"$FAKE_REPO_DIR/apply"

# 1. keymaps/ is now a symlink pointing at the repo copy
if [ "$(readlink "$FAKE_CONFIG_DIR/keymaps")" != "$FAKE_REPO_DIR/keymaps" ]; then
    echo "FAIL: keymaps/ was not symlinked to the repo copy"
    exit 1
fi

# 2. the pre-existing real keymaps/ dir was backed up before symlinking
backup_dir="$(find "$FAKE_CONFIG_DIR" -maxdepth 1 -name 'keymaps.bak-*' | head -1)"
if [ -z "$backup_dir" ] || [ ! -f "$backup_dir/Old.xml" ]; then
    echo "FAIL: pre-existing keymaps/ was not backed up before symlinking"
    exit 1
fi

# 3. find.xml is now a symlink pointing at the repo copy
if [ "$(readlink "$FAKE_CONFIG_DIR/options/find.xml")" != "$FAKE_REPO_DIR/options/find.xml" ]; then
    echo "FAIL: options/find.xml was not symlinked to the repo copy"
    exit 1
fi

# 4. the pre-existing real find.xml was backed up before symlinking
backup_file="$(find "$FAKE_CONFIG_DIR/options" -maxdepth 1 -name 'find.xml.bak-*' | head -1)"
if [ -z "$backup_file" ] || ! grep -q 'name="Old"' "$backup_file"; then
    echo "FAIL: pre-existing options/find.xml was not backed up before symlinking"
    exit 1
fi

# 5. other whole-dirs (colors, templates, fileTemplates, codestyles) also symlinked
for name in colors templates fileTemplates codestyles; do
    if [ "$(readlink "$FAKE_CONFIG_DIR/$name")" != "$FAKE_REPO_DIR/$name" ]; then
        echo "FAIL: $name/ was not symlinked"
        exit 1
    fi
done

# 6. running apply again is a no-op (doesn't re-backup an already-correct symlink)
before_backups="$(find "$FAKE_CONFIG_DIR" -maxdepth 1 -name 'keymaps.bak-*' | wc -l | tr -d ' ')"
"$FAKE_REPO_DIR/apply"
after_backups="$(find "$FAKE_CONFIG_DIR" -maxdepth 1 -name 'keymaps.bak-*' | wc -l | tr -d ' ')"
if [ "$before_backups" != "$after_backups" ]; then
    echo "FAIL: second apply run created an unnecessary backup of an already-correct symlink"
    exit 1
fi

# 7. a missing individual repo file (e.g. debugger.xml not committed yet)
# must not abort the whole run — other curated files still get linked.
# Uses a second fresh env so this doesn't interact with the state above.
teardown_fake_idea_env
setup_fake_idea_env
stage_fake_repo_dir "$real_repo_dir"
mkdir -p "$FAKE_REPO_DIR/keymaps" "$FAKE_REPO_DIR/colors" "$FAKE_REPO_DIR/templates" "$FAKE_REPO_DIR/fileTemplates" "$FAKE_REPO_DIR/codestyles" "$FAKE_REPO_DIR/options"
echo '<application><component name="Test" /></application>' > "$FAKE_REPO_DIR/options/find.xml"
# deliberately no debugger.xml in the fake repo dir

"$FAKE_REPO_DIR/apply"

if [ "$(readlink "$FAKE_CONFIG_DIR/options/find.xml")" != "$FAKE_REPO_DIR/options/find.xml" ]; then
    echo "FAIL: a missing debugger.xml aborted the run before find.xml was linked"
    exit 1
fi

# 8. apply never touches plugins/ — no install/uninstall/reconcile side
# effects (locks in the "document only" plugin decision)
mkdir -p "$FAKE_CONFIG_DIR/plugins/some-plugin"
plugins_before="$(find "$FAKE_CONFIG_DIR/plugins" -mindepth 1 -maxdepth 1 | sort)"
"$FAKE_REPO_DIR/apply"
plugins_after="$(find "$FAKE_CONFIG_DIR/plugins" -mindepth 1 -maxdepth 1 | sort)"
if [ "$plugins_before" != "$plugins_after" ]; then
    echo "FAIL: apply modified $FAKE_CONFIG_DIR/plugins — it must never touch plugins"
    exit 1
fi

echo "PASS: test_apply.sh"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `chmod +x ide/idea/tests/test_apply.sh && bash ide/idea/tests/test_apply.sh`
Expected: FAIL — `ide/idea/apply: No such file or directory` (the staged copy has nothing to copy from).

- [ ] **Step 3: Write minimal implementation**

Create `ide/idea/apply`:

```bash
#!/usr/bin/env bash
# Symlinks the whole-directory areas (keymaps/colors/templates/
# fileTemplates/codestyles) and curated options/*.xml files into IntelliJ
# IDEA's config directory (backing up any pre-existing real file/dir
# first). No plugin handling — plugins are managed manually; see the
# design spec.
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_dir/lib.sh"

config_dir="$(idea_config_dir)" || exit 1

link() {
    local repo_path="$1" live_path="$2"
    if [ ! -e "$repo_path" ]; then
        echo "idea-apply: $repo_path does not exist, skipping" >&2
        return 1
    fi
    if [ -L "$live_path" ] && [ "$(readlink "$live_path")" = "$repo_path" ]; then
        return 0  # already correct, nothing to do
    fi
    if [ -e "$live_path" ]; then
        local backup="${live_path}.bak-$(date +%Y%m%d%H%M%S)"
        mv "$live_path" "$backup"
        echo "idea-apply: backed up existing $live_path -> $backup"
    fi
    ln -s "$repo_path" "$live_path"
    echo "idea-apply: linked $live_path -> $repo_path"
}

# --- whole-directory areas ---
for name in "${IDEA_WHOLE_DIRS[@]}"; do
    mkdir -p "$repo_dir/$name"
    link "$repo_dir/$name" "$config_dir/$name" || true
done

# --- curated options/*.xml files ---
mkdir -p "$config_dir/options"
for name in "${IDEA_OPTION_FILES[@]}"; do
    link "$repo_dir/options/$name" "$config_dir/options/$name" || true
done

echo "idea-apply: done."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `chmod +x ide/idea/apply && bash ide/idea/tests/test_apply.sh`
Expected: `PASS: test_apply.sh`

- [ ] **Step 5: Commit**

```bash
cd ide/idea
git add apply tests/test_apply.sh
git commit -m "Add idea apply script for whole-dir and curated options symlinking

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `export` script

**Files:**
- Create: `ide/idea/export`
- Test: `ide/idea/tests/test_export.sh`

**Interfaces:**
- Consumes: `lib.sh`'s `IDEA_OPTION_FILES`, `IDEA_WHOLE_DIRS`, `idea_config_dir()` (Task 1). `tests/fixtures.sh` helpers (Task 1).
- Produces: executable `export` script, `plugins.txt` format (one plugin directory basename per line, `LC_ALL=C sort`ed, no header).

- [ ] **Step 1: Write the failing test**

Create `ide/idea/tests/test_export.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/fixtures.sh"

real_repo_dir="$dir/.."
setup_fake_idea_env
trap teardown_fake_idea_env EXIT
stage_fake_repo_dir "$real_repo_dir"

# seed a live (non-symlinked) keymaps/ dir and find.xml to exercise the
# bootstrap path
mkdir -p "$FAKE_CONFIG_DIR/keymaps"
echo '<keymap name="Live" />' > "$FAKE_CONFIG_DIR/keymaps/Live.xml"
echo '<application><component name="Live" /></application>' > "$FAKE_CONFIG_DIR/options/find.xml"

# seed two fake installed plugins
mkdir -p "$FAKE_CONFIG_DIR/plugins/zzz-plugin" "$FAKE_CONFIG_DIR/plugins/aaa-plugin"

"$FAKE_REPO_DIR/export"

# 1. keymaps/ got bootstrapped from the live (non-symlinked) dir
if [ ! -f "$FAKE_REPO_DIR/keymaps/Live.xml" ]; then
    echo "FAIL: keymaps/ was not bootstrapped from the live directory"
    exit 1
fi

# 2. find.xml got bootstrapped from the live (non-symlinked) file
if ! grep -q 'name="Live"' "$FAKE_REPO_DIR/options/find.xml"; then
    echo "FAIL: options/find.xml was not bootstrapped from the live file"
    exit 1
fi

# 3. plugins.txt lists both fake plugins, sorted
expected=$'aaa-plugin\nzzz-plugin'
actual="$(cat "$FAKE_REPO_DIR/plugins.txt")"
if [ "$actual" != "$expected" ]; then
    echo "FAIL: plugins.txt does not match fake plugin dirs"
    echo "expected: $expected"
    echo "actual:   $actual"
    exit 1
fi

# 4. running export again does not clobber a manually-edited repo copy of a
# bootstrap-once file
echo '<keymap name="EditedByHand" />' > "$FAKE_REPO_DIR/keymaps/Live.xml"
"$FAKE_REPO_DIR/export"
if ! grep -q 'EditedByHand' "$FAKE_REPO_DIR/keymaps/Live.xml"; then
    echo "FAIL: second export run clobbered the manually-edited repo keymaps/Live.xml"
    exit 1
fi

# 5. plugins.txt IS regenerated unconditionally on every run, even if a
# plugin was added since the last export (it's a reference snapshot, not
# bootstrap-once)
mkdir -p "$FAKE_CONFIG_DIR/plugins/new-plugin"
"$FAKE_REPO_DIR/export"
if ! grep -qFx 'new-plugin' "$FAKE_REPO_DIR/plugins.txt"; then
    echo "FAIL: plugins.txt was not regenerated to include a newly installed plugin"
    exit 1
fi

echo "PASS: test_export.sh"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `chmod +x ide/idea/tests/test_export.sh && bash ide/idea/tests/test_export.sh`
Expected: FAIL — `ide/idea/export: No such file or directory`.

- [ ] **Step 3: Write minimal implementation**

Create `ide/idea/export`:

```bash
#!/usr/bin/env bash
# Bootstraps repo copies of the whole-directory areas (keymaps/colors/
# templates/fileTemplates/codestyles) and curated options/*.xml files from
# IntelliJ IDEA's live config directory (only once — never overwrites an
# existing repo copy; only apply, via backup-then-symlink, changes that
# afterward). Also unconditionally regenerates plugins.txt as a reference
# snapshot — never installed/uninstalled by apply.
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_dir/lib.sh"

config_dir="$(idea_config_dir)" || exit 1

# --- whole-directory areas: bootstrap only once, only if not already symlinked ---
bootstrap_dir() {
    local live_path="$1" repo_path="$2"
    if [ -L "$live_path" ]; then
        return 0  # already a symlink managed by apply — nothing to do
    fi
    if [ -d "$live_path" ] && [ -z "$(ls -A "$repo_path" 2>/dev/null)" ]; then
        cp -R "$live_path/." "$repo_path/" 2>/dev/null || true
        echo "idea-export: bootstrapped $repo_path from $live_path (edit the repo copy, then run ./apply)"
    fi
}

for name in "${IDEA_WHOLE_DIRS[@]}"; do
    mkdir -p "$repo_dir/$name"
    bootstrap_dir "$config_dir/$name" "$repo_dir/$name"
done

# --- curated options/*.xml files: bootstrap only once ---
bootstrap_file() {
    local live_path="$1" repo_path="$2"
    if [ -L "$live_path" ]; then
        return 0
    fi
    if [ -f "$live_path" ] && [ ! -e "$repo_path" ]; then
        cp "$live_path" "$repo_path"
        echo "idea-export: bootstrapped $repo_path from $live_path (edit the repo copy, then run ./apply)"
    fi
}

mkdir -p "$repo_dir/options"
for name in "${IDEA_OPTION_FILES[@]}"; do
    bootstrap_file "$config_dir/options/$name" "$repo_dir/options/$name"
done

# --- plugins.txt: always regenerated from the live install (reference only) ---
if [ -d "$config_dir/plugins" ]; then
    find "$config_dir/plugins" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | LC_ALL=C sort > "$repo_dir/plugins.txt"
    echo "idea-export: wrote $(wc -l < "$repo_dir/plugins.txt" | tr -d ' ') plugin names to plugins.txt (reference only — not installed by apply)"
fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `chmod +x ide/idea/export && bash ide/idea/tests/test_export.sh`
Expected: `PASS: test_export.sh`

- [ ] **Step 5: Commit**

```bash
cd ide/idea
git add export tests/test_export.sh
git commit -m "Add idea export script with plugins.txt reference snapshot

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `Makefile` + `README.md`

**Files:**
- Create: `ide/idea/Makefile`
- Create: `ide/idea/README.md`

**Interfaces:**
- Consumes: `apply`, `export`, `tests/test_*.sh` (Tasks 1–3).
- Produces: `make help|apply|export|test` targets (no `prune` target — unlike `vscode`'s Makefile, there's no reconcile-a-list step here since plugins aren't managed).

- [ ] **Step 1: Create the Makefile**

Create `ide/idea/Makefile`:

```makefile
# Convenience wrappers around ./export and ./apply. Run from ide/idea/.
# `make` with no target prints this help rather than mutating anything.
.PHONY: help apply export test

help:
	@echo "make apply   - symlink keymaps/colors/templates/fileTemplates/codestyles dirs + curated options/*.xml"
	@echo "make export  - snapshot current settings/keymap/colors/etc + plugins.txt (reference only) into this dir"
	@echo "make test    - run the test suite in tests/"

apply:
	./apply

export:
	./export

test:
	@for t in tests/test_*.sh; do \
		echo "### $$t ###"; \
		bash "$$t" || exit 1; \
	done
```

- [ ] **Step 2: Run `make test` to verify all prior tasks' tests still pass together**

Run: `cd ide/idea && make test`
Expected:
```
### tests/test_apply.sh ###
PASS: test_apply.sh
### tests/test_export.sh ###
PASS: test_export.sh
### tests/test_lib.sh ###
PASS: test_lib.sh
```

- [ ] **Step 3: Verify bare `make` prints help without mutating anything**

Run: `cd ide/idea && make`
Expected: prints the three `make apply`/`make export`/`make test` description lines (the `help` target, since it's listed first in the Makefile) and does not create, modify, or symlink any file.

- [ ] **Step 4: Create the README**

Create `ide/idea/README.md`:

```markdown
# IntelliJ IDEA config

Settings, keymap/shortcuts, color scheme, code style, and templates — not
plugins (managed manually; see below). See
`docs/superpowers/specs/2026-09-09-idea-ide-config-design.md` for the full
rationale (why plugins are out of scope, how the `options/` allowlist was
curated, what was excluded and why).

## First-time setup on a new machine

```bash
make export   # bootstraps settings/keymap/colors/etc into this dir if not
              # already committed here — on a freshly cloned repo this is
              # a no-op except for regenerating plugins.txt
make apply    # symlinks keymaps/colors/templates/fileTemplates/codestyles
              # dirs + curated options/*.xml files into place
```

`make` alone (no target) prints the available commands: `apply`, `export`,
`test`. Plain `./export`/`./apply` still work directly if you'd rather skip
`make`.

## Day-to-day

- **Change a setting, keymap, color scheme, code style, or template:** just
  do it in IntelliJ as normal — the `keymaps/`, `colors/`, `templates/`,
  `fileTemplates/`, `codestyles/` directories and every file listed in
  `IDEA_OPTION_FILES` (`lib.sh`) are live symlinks into this directory, so
  the change already landed here. `git diff`, commit.
- **Track a new settings file:** find the new/changed file under
  IntelliJ's live `options/` directory, review its content for
  machine-specific paths, account identity, or secrets (see the excluded
  list below for what to watch for), add its filename to
  `IDEA_OPTION_FILES` in `lib.sh`, run `make export` to bootstrap it in,
  commit. Other machines pick it up via `git pull && make apply`.
- **Plugins:** manage installation yourself via the Marketplace UI.
  `make export` refreshes `plugins.txt` as a reference snapshot of
  installed plugin folder names — `apply` never installs, uninstalls, or
  reconciles anything from it. Folder names are a memory aid for
  re-searching the Marketplace, not guaranteed Marketplace plugin IDs.

## Excluded from tracking (deliberately, not by oversight)

- **Machine-specific paths:** `nodejs.xml`, `path.macros.xml`,
  `jdk.table.xml`, `proxy.settings.xml`
- **Account-specific:** `github.xml`, `gitlab.xml` — tied to one machine's
  JetBrains/GitHub identity; syncing would break work/personal
  independence.
- **Sensitive/environment-specific:** `databaseDrivers.xml`,
  `databaseSettings.xml`, `remote-servers.xml`
- **Mixed real-setting + auto-managed state:** `ide.general.xml` — holds
  one real preference alongside IntelliJ-managed Registry/experiment
  flags; not worth the risk for one setting today.
- **Pure machine state/telemetry/cache:** everything else under `options/`
  not listed in `IDEA_OPTION_FILES` — recent projects, window
  geometry/layout, usage statistics, trusted paths, feedback/onboarding
  state, caches, and similar.

## Known machine-specific settings

Two IntelliJ versions can coexist under
`~/Library/Application Support/JetBrains/` (e.g. `IntelliJIdea2026.1` and
`IntelliJIdea2026.2`). `apply`/`export` always resolve the newest one
automatically (`idea_config_dir` in `lib.sh`, sorted by version) — nothing
to adjust here after an IntelliJ upgrade.

## Non-goals

- Scripted plugin install/uninstall — rejected; see the design spec for
  why (`idea` CLI limitations, and this is managed manually by choice).
- Other JetBrains products (PyCharm, DataGrip, WebStorm, etc.) — add a
  sibling directory under `ide/` if that ever becomes relevant; not
  implemented now.
- IntelliJ's built-in cloud Settings Sync — not used as the sync
  mechanism; would tie sync to one JetBrains account and fight this
  symlink-based approach.
```

- [ ] **Step 5: Commit**

```bash
cd ide/idea
git add Makefile README.md
git commit -m "Add idea Makefile and README

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Bootstrap real content from this machine and apply

**Files:**
- Modify (populated by `./export`, not hand-written): `ide/idea/options/*.xml` (the 19 files listed in `IDEA_OPTION_FILES`), `ide/idea/keymaps/`, `ide/idea/colors/`, `ide/idea/templates/`, `ide/idea/fileTemplates/`, `ide/idea/codestyles/Default.xml`, `ide/idea/plugins.txt`.

**Interfaces:**
- Consumes: `export`, `apply` (Tasks 2–3), unmodified — run against the real machine instead of a fake fixture.
- Produces: real, live-linked IntelliJ config on this machine; the actual committed content other machines will pick up via `git pull && make apply`.

This task runs the scripts for real against this machine's live IntelliJ config (not a fixture) — the same kind of step already done for `ide/vscode` on this machine. `apply`'s backup-before-link behavior means nothing is destroyed even if something unexpected is already in place.

- [ ] **Step 1: Bootstrap real content into the repo**

Run:
```bash
cd ide/idea
./export
```
Expected: output lines like `idea-export: bootstrapped ide/idea/options/find.xml from ... /options/find.xml (edit the repo copy, then run ./apply)` for each of the 19 curated files that exist live, plus a line reporting how many plugin names were written to `plugins.txt`. The whole-dir areas (`keymaps/`, `colors/`, `templates/`, `fileTemplates/`) will report nothing bootstrapped if they're still empty on this machine — that's expected (see design spec's investigation findings) and not a failure.

- [ ] **Step 2: Review what actually landed before committing**

Run:
```bash
git status
git diff --stat
```
Confirm: only files under `ide/idea/options/`, `ide/idea/codestyles/`, and `ide/idea/plugins.txt` show as new/changed (the empty whole-dirs stay empty — nothing to diff). Confirm none of the excluded filenames from the Global Constraints section appear anywhere under `ide/idea/`.

- [ ] **Step 3: Apply — symlink the live config to the repo copies**

Run:
```bash
./apply
```
Expected: `idea-apply: linked ... -> ...` for each of the 5 whole-dirs and each of the 19 curated options files, with `idea-apply: backed up existing ...` lines for whichever ones already existed as real (non-symlinked) files/dirs before this run.

- [ ] **Step 4: Verify the symlinks are live**

Run:
```bash
readlink "$HOME/Library/Application Support/JetBrains/IntelliJIdea2026.2/options/find.xml"
readlink "$HOME/Library/Application Support/JetBrains/IntelliJIdea2026.2/keymaps"
```
Expected: both print the absolute path to the corresponding file/dir under this repo's `ide/idea/`.

If IntelliJ IDEA is currently running, restart it once so it re-reads config from the new symlinked locations rather than holding stale in-memory state that could get written back over the new symlink target on next save.

- [ ] **Step 5: Commit**

```bash
cd ide/idea
git add options codestyles plugins.txt keymaps colors templates fileTemplates
git commit -m "Bootstrap real IntelliJ IDEA settings into dotfiles

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
