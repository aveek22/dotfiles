# VS Code IDE Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring VS Code settings/keybindings/snippets/extensions into this dotfiles repo under `ide/vscode/`, collapsed to a single unified profile, synced via live symlinks (settings/keybindings/snippets) plus an additive+prune install script (extensions) that works unmodified on macOS and Ubuntu.

**Architecture:** `ide/vscode/lib.sh` resolves the OS-specific VS Code User directory. `ide/vscode/export` regenerates `extensions.txt` from what's actually installed and bootstraps settings/keybindings/snippets into the repo if they aren't symlinked yet. `ide/vscode/apply` symlinks settings/keybindings/snippets into place (backing up any real file first) and reconciles installed extensions against `extensions.txt` (installs what's missing, uninstalls what's not listed).

**Tech Stack:** bash (no test framework beyond plain scripts + assertions — matches this repo's existing `scripts/kube` style), the `code` CLI.

**Spec:** `docs/superpowers/specs/2026-09-08-vscode-ide-config-design.md`

## Global Constraints

- Single VS Code profile (`Default`) only — no FrontEnd/JVM/Python/Rusty/Golang profiles are created or managed by this repo.
- No account/login of any kind is required by any script here.
- macOS User dir: `~/Library/Application Support/Code/User`. Ubuntu (official VS Code, not code-server) User dir: `~/.config/Code/User`. Alpine/code-server is explicitly unsupported.
- `apply` is additive + prune: it installs everything in `extensions.txt` and uninstalls anything installed that isn't listed, printing both lists before acting.
- `settings.json`/`keybindings.json`/`snippets/` are live symlinks once `apply` has run — never copied on every run, only bootstrapped once if the repo copy doesn't exist yet.
- Final unified extension list is exactly 71 entries (see Task 5). Final `settings.json` has exactly one `update.mode` key (top-level), no `atlascode.jira.lastCreateSiteAndProject` block, no `vs-kubernetes` block, no `/tmp` or `/var/folders` entries under `chat.instructionsFilesLocations`, no `black-formatter.path` key, and includes `evenBetterToml.formatter.indentEntries: true`.

---

### Task 1: `lib.sh` — OS-specific VS Code User directory resolution

**Files:**
- Create: `ide/vscode/lib.sh`
- Test: `ide/vscode/tests/test_lib.sh`

**Interfaces:**
- Produces: `vscode_user_dir()` — a shell function, sourced from `lib.sh`, that echoes the absolute path to VS Code's per-user config directory for the current OS (reads `$HOME` and `uname -s`), returns non-zero on an unsupported OS. Used by both `export` (Task 2) and `apply` (Task 3).

- [ ] **Step 1: Write the failing test**

Create `ide/vscode/tests/test_lib.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/../lib.sh"

HOME="/tmp/fake-home-$$"

result="$(uname() { echo Darwin; }; export -f uname; vscode_user_dir)"
expected="/tmp/fake-home-$$/Library/Application Support/Code/User"
if [ "$result" != "$expected" ]; then
    echo "FAIL: macOS path resolution wrong: got '$result' expected '$expected'"
    exit 1
fi

result="$(uname() { echo Linux; }; export -f uname; vscode_user_dir)"
expected="/tmp/fake-home-$$/.config/Code/User"
if [ "$result" != "$expected" ]; then
    echo "FAIL: Linux path resolution wrong: got '$result' expected '$expected'"
    exit 1
fi

if uname() { echo Plan9; }; export -f uname; vscode_user_dir >/dev/null 2>&1; then
    echo "FAIL: unsupported OS should have returned non-zero"
    exit 1
fi

echo "PASS: test_lib.sh"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `mkdir -p ide/vscode && bash ide/vscode/tests/test_lib.sh`
Expected: FAIL — `ide/vscode/lib.sh: No such file or directory` (script doesn't exist yet)

- [ ] **Step 3: Write `lib.sh`**

Create `ide/vscode/lib.sh`:

```bash
#!/usr/bin/env bash
# Shared helpers for the vscode export/apply scripts. Sourced, not executed.

# Prints the absolute path to VS Code's per-user config directory for the
# current OS. Exits non-zero on an unsupported OS (e.g. Alpine/code-server,
# which isn't supported by this setup — see the design spec).
vscode_user_dir() {
    case "$(uname -s)" in
        Darwin)
            echo "$HOME/Library/Application Support/Code/User"
            ;;
        Linux)
            echo "$HOME/.config/Code/User"
            ;;
        *)
            echo "vscode: unsupported OS: $(uname -s)" >&2
            return 1
            ;;
    esac
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash ide/vscode/tests/test_lib.sh`
Expected: `PASS: test_lib.sh`

- [ ] **Step 5: Commit**

```bash
git add ide/vscode/lib.sh ide/vscode/tests/test_lib.sh
git commit -m "Add vscode OS path resolution helper"
```

---

### Task 2: `export` script

**Files:**
- Create: `ide/vscode/export`
- Create: `ide/vscode/tests/fixtures.sh`
- Test: `ide/vscode/tests/test_export.sh`

**Interfaces:**
- Consumes: `vscode_user_dir()` from `ide/vscode/lib.sh` (Task 1).
- Produces: `setup_fake_vscode_env()` and `teardown_fake_vscode_env()` and `stage_fake_repo_dir(real_repo_dir)` in `tests/fixtures.sh` — reused by Task 3's `test_apply.sh`. After `setup_fake_vscode_env`, these env vars are set: `FAKE_HOME`, `FAKE_USER_DIR`, `FAKE_BIN`, `FAKE_BIN_LOG`, `FAKE_EXTENSIONS_FILE`, `HOME` (overridden), `PATH` (overridden), `TMP_TEST_DIR`. After `stage_fake_repo_dir`, `FAKE_REPO_DIR` is set to a scratch copy of the real scripts — tests run against this, never the real `ide/vscode/` files.

- [ ] **Step 1: Write the failing test**

Create `ide/vscode/tests/fixtures.sh`:

```bash
#!/usr/bin/env bash
# Shared test fixture helpers for export/apply tests. Sourced, not executed.

# Creates a temp fake $HOME with a fake VS Code User dir and a fake `code`
# CLI on PATH that logs every invocation and answers --list-extensions /
# --install-extension / --uninstall-extension against a fake installed-list
# file. Exported: FAKE_HOME, FAKE_USER_DIR, FAKE_BIN, FAKE_BIN_LOG,
# FAKE_EXTENSIONS_FILE, TMP_TEST_DIR. Overrides HOME and PATH.
setup_fake_vscode_env() {
    local tmp
    tmp="$(mktemp -d)"
    export TMP_TEST_DIR="$tmp"
    export FAKE_HOME="$tmp/home"
    export FAKE_USER_DIR="$FAKE_HOME/Library/Application Support/Code/User"
    export FAKE_BIN="$tmp/bin"
    export FAKE_BIN_LOG="$tmp/code-calls.log"
    export FAKE_EXTENSIONS_FILE="$tmp/installed-extensions.txt"
    mkdir -p "$FAKE_USER_DIR" "$FAKE_BIN"
    : > "$FAKE_BIN_LOG"
    printf 'a.ext\nb.ext\n' > "$FAKE_EXTENSIONS_FILE"

    cat > "$FAKE_BIN/code" << 'FAKECODE'
#!/usr/bin/env bash
echo "$@" >> "$FAKE_BIN_LOG"
case "$1" in
    --list-extensions)
        cat "$FAKE_EXTENSIONS_FILE"
        ;;
    --install-extension)
        echo "$2" >> "$FAKE_EXTENSIONS_FILE"
        ;;
    --uninstall-extension)
        grep -vFx "$2" "$FAKE_EXTENSIONS_FILE" > "$FAKE_EXTENSIONS_FILE.tmp" || true
        mv "$FAKE_EXTENSIONS_FILE.tmp" "$FAKE_EXTENSIONS_FILE"
        ;;
esac
FAKECODE
    chmod +x "$FAKE_BIN/code"

    export HOME="$FAKE_HOME"
    export PATH="$FAKE_BIN:$PATH"
}

teardown_fake_vscode_env() {
    rm -rf "$TMP_TEST_DIR"
}

# Copies the real export/apply/lib.sh into a scratch dir so tests never
# write into the real ide/vscode/ files. Sets FAKE_REPO_DIR.
stage_fake_repo_dir() {
    local real_repo_dir="$1"
    local staged="$TMP_TEST_DIR/repo"
    mkdir -p "$staged"
    cp "$real_repo_dir/export" "$real_repo_dir/apply" "$real_repo_dir/lib.sh" "$staged/"
    chmod +x "$staged/export" "$staged/apply"
    export FAKE_REPO_DIR="$staged"
}
```

Create `ide/vscode/tests/test_export.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/fixtures.sh"

real_repo_dir="$dir/.."
setup_fake_vscode_env
trap teardown_fake_vscode_env EXIT
stage_fake_repo_dir "$real_repo_dir"

# seed a live (non-symlinked) settings.json to exercise the bootstrap path
echo '{"foo": "bar"}' > "$FAKE_USER_DIR/settings.json"

"$FAKE_REPO_DIR/export"

# 1. extensions.txt reflects the fake install list, sorted
expected_sorted="$(sort "$FAKE_EXTENSIONS_FILE")"
actual="$(cat "$FAKE_REPO_DIR/extensions.txt")"
if [ "$actual" != "$expected_sorted" ]; then
    echo "FAIL: extensions.txt does not match fake install list"
    echo "expected: $expected_sorted"
    echo "actual:   $actual"
    exit 1
fi

# 2. settings.json got bootstrapped from the live (non-symlinked) file
if ! grep -q '"foo": "bar"' "$FAKE_REPO_DIR/settings.json"; then
    echo "FAIL: settings.json was not bootstrapped from the live file"
    exit 1
fi

# 3. running export again does not clobber a manually-edited repo copy
echo '{"foo": "edited-by-hand"}' > "$FAKE_REPO_DIR/settings.json"
"$FAKE_REPO_DIR/export"
if ! grep -q 'edited-by-hand' "$FAKE_REPO_DIR/settings.json"; then
    echo "FAIL: second export run clobbered the manually-edited repo settings.json"
    exit 1
fi

echo "PASS: test_export.sh"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `chmod +x ide/vscode/tests/test_export.sh && bash ide/vscode/tests/test_export.sh`
Expected: FAIL — `ide/vscode/export: No such file or directory` (script doesn't exist yet)

- [ ] **Step 3: Write `export`**

Create `ide/vscode/export`:

```bash
#!/usr/bin/env bash
# Refreshes ide/vscode/extensions.txt from what's actually installed, and
# bootstraps settings.json/keybindings.json/snippets/ into the repo the
# first time (before `apply` has symlinked them). Safe to run repeatedly —
# once a repo copy exists, it is never overwritten by this script again;
# only `apply` (deliberately, via backup-then-symlink) changes that.
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_dir/lib.sh"

if ! command -v code >/dev/null 2>&1; then
    echo "vscode-export: 'code' CLI not found in PATH" >&2
    echo "  Run 'Shell Command: Install code command in PATH' from VS Code's Command Palette." >&2
    exit 1
fi

user_dir="$(vscode_user_dir)"

# --- extensions.txt: always regenerated from the live install ---
code --list-extensions | LC_ALL=C sort > "$repo_dir/extensions.txt"
echo "vscode-export: wrote $(wc -l < "$repo_dir/extensions.txt" | tr -d ' ') extensions to extensions.txt"

# --- settings/keybindings: bootstrap only once, only if not already symlinked ---
bootstrap_file() {
    local live_path="$1" repo_path="$2"
    if [ -L "$live_path" ]; then
        return 0  # already a symlink managed by apply — nothing to do
    fi
    if [ -f "$live_path" ] && [ ! -e "$repo_path" ]; then
        cp "$live_path" "$repo_path"
        echo "vscode-export: bootstrapped $repo_path from $live_path (edit the repo copy, then run ./apply)"
    fi
}

bootstrap_file "$user_dir/settings.json" "$repo_dir/settings.json"
bootstrap_file "$user_dir/keybindings.json" "$repo_dir/keybindings.json"

if [ -d "$user_dir/snippets" ] && [ ! -L "$user_dir/snippets" ] && [ -z "$(ls -A "$repo_dir/snippets" 2>/dev/null)" ]; then
    mkdir -p "$repo_dir/snippets"
    cp -R "$user_dir/snippets/." "$repo_dir/snippets/" 2>/dev/null || true
fi
```

Make it executable: `chmod +x ide/vscode/export`

- [ ] **Step 4: Run test to verify it passes**

Run: `bash ide/vscode/tests/test_export.sh`
Expected: `PASS: test_export.sh`

- [ ] **Step 5: Commit**

```bash
git add ide/vscode/export ide/vscode/tests/fixtures.sh ide/vscode/tests/test_export.sh
git commit -m "Add vscode export script"
```

---

### Task 3: `apply` script

**Files:**
- Create: `ide/vscode/apply`
- Test: `ide/vscode/tests/test_apply.sh`

**Interfaces:**
- Consumes: `vscode_user_dir()` from `lib.sh` (Task 1); `setup_fake_vscode_env`/`teardown_fake_vscode_env`/`stage_fake_repo_dir` from `tests/fixtures.sh` (Task 2).

- [ ] **Step 1: Write the failing test**

Create `ide/vscode/tests/test_apply.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/fixtures.sh"

real_repo_dir="$dir/.."
setup_fake_vscode_env
trap teardown_fake_vscode_env EXIT
stage_fake_repo_dir "$real_repo_dir"

# minimal repo content to apply
echo '{"theme": "test"}' > "$FAKE_REPO_DIR/settings.json"
echo '[]' > "$FAKE_REPO_DIR/keybindings.json"
mkdir -p "$FAKE_REPO_DIR/snippets"
printf 'wanted.ext\n' > "$FAKE_REPO_DIR/extensions.txt"

# pre-existing real (non-symlinked) keybindings.json — must be backed up, not destroyed
echo '{"old": true}' > "$FAKE_USER_DIR/keybindings.json"

# fake "currently installed": has b.ext (should be pruned), missing wanted.ext (should be installed)
printf 'b.ext\n' > "$FAKE_EXTENSIONS_FILE"

"$FAKE_REPO_DIR/apply"

# 1. settings.json is now a symlink pointing at the repo copy
if [ "$(readlink "$FAKE_USER_DIR/settings.json")" != "$FAKE_REPO_DIR/settings.json" ]; then
    echo "FAIL: settings.json was not symlinked to the repo copy"
    exit 1
fi

# 2. pre-existing real keybindings.json was backed up before symlinking
if [ "$(readlink "$FAKE_USER_DIR/keybindings.json")" != "$FAKE_REPO_DIR/keybindings.json" ]; then
    echo "FAIL: keybindings.json was not symlinked"
    exit 1
fi
backup_file="$(find "$FAKE_USER_DIR" -maxdepth 1 -name 'keybindings.json.bak-*' | head -1)"
if [ -z "$backup_file" ] || ! grep -q '"old": true' "$backup_file"; then
    echo "FAIL: pre-existing keybindings.json was not backed up before symlinking"
    exit 1
fi

# 3. snippets/ symlinked too
if [ "$(readlink "$FAKE_USER_DIR/snippets")" != "$FAKE_REPO_DIR/snippets" ]; then
    echo "FAIL: snippets/ was not symlinked"
    exit 1
fi

# 4. extensions reconciled: wanted.ext installed, b.ext pruned
final="$(sort "$FAKE_EXTENSIONS_FILE")"
if [ "$final" != "wanted.ext" ]; then
    echo "FAIL: expected only wanted.ext installed after apply, got: $final"
    exit 1
fi

# 5. running apply again is a no-op on settings.json (doesn't re-backup an already-correct symlink)
before_backups="$(find "$FAKE_USER_DIR" -maxdepth 1 -name 'settings.json.bak-*' | wc -l | tr -d ' ')"
"$FAKE_REPO_DIR/apply"
after_backups="$(find "$FAKE_USER_DIR" -maxdepth 1 -name 'settings.json.bak-*' | wc -l | tr -d ' ')"
if [ "$before_backups" != "$after_backups" ]; then
    echo "FAIL: second apply run created an unnecessary backup of an already-correct symlink"
    exit 1
fi

echo "PASS: test_apply.sh"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `chmod +x ide/vscode/tests/test_apply.sh && bash ide/vscode/tests/test_apply.sh`
Expected: FAIL — `ide/vscode/apply: No such file or directory` (script doesn't exist yet)

- [ ] **Step 3: Write `apply`**

Create `ide/vscode/apply`:

```bash
#!/usr/bin/env bash
# Symlinks settings/keybindings/snippets into VS Code's User directory
# (backing up any pre-existing real file first) and reconciles installed
# extensions with extensions.txt: additive (installs what's missing) +
# prune (uninstalls what's installed but not listed).
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_dir/lib.sh"

if ! command -v code >/dev/null 2>&1; then
    echo "vscode-apply: 'code' CLI not found in PATH" >&2
    echo "  Run 'Shell Command: Install code command in PATH' from VS Code's Command Palette." >&2
    exit 1
fi

user_dir="$(vscode_user_dir)"
mkdir -p "$user_dir"

link() {
    local repo_path="$1" live_path="$2"
    if [ ! -e "$repo_path" ]; then
        echo "vscode-apply: $repo_path does not exist, skipping" >&2
        return 1
    fi
    if [ -L "$live_path" ] && [ "$(readlink "$live_path")" = "$repo_path" ]; then
        return 0  # already correct, nothing to do
    fi
    if [ -e "$live_path" ]; then
        local backup="${live_path}.bak-$(date +%Y%m%d%H%M%S)"
        mv "$live_path" "$backup"
        echo "vscode-apply: backed up existing $live_path -> $backup"
    fi
    ln -s "$repo_path" "$live_path"
    echo "vscode-apply: linked $live_path -> $repo_path"
}

link "$repo_dir/settings.json" "$user_dir/settings.json"
link "$repo_dir/keybindings.json" "$user_dir/keybindings.json"
mkdir -p "$repo_dir/snippets"
link "$repo_dir/snippets" "$user_dir/snippets"

# --- extensions: additive + prune ---
desired="$(LC_ALL=C sort "$repo_dir/extensions.txt")"
current="$(code --list-extensions | LC_ALL=C sort)"

to_install="$(comm -23 <(echo "$desired") <(echo "$current") || true)"
to_remove="$(comm -13 <(echo "$desired") <(echo "$current") || true)"

if [ -n "$to_install" ]; then
    echo "vscode-apply: installing:"
    echo "$to_install" | sed 's/^/  + /'
    echo "$to_install" | xargs -I{} code --install-extension {}
fi

if [ -n "$to_remove" ]; then
    echo "vscode-apply: pruning (not in extensions.txt):"
    echo "$to_remove" | sed 's/^/  - /'
    echo "$to_remove" | xargs -I{} code --uninstall-extension {}
fi

echo "vscode-apply: done."
```

Make it executable: `chmod +x ide/vscode/apply`

- [ ] **Step 4: Run test to verify it passes**

Run: `bash ide/vscode/tests/test_apply.sh`
Expected: `PASS: test_apply.sh`

- [ ] **Step 5: Commit**

```bash
git add ide/vscode/apply ide/vscode/tests/test_apply.sh
git commit -m "Add vscode apply script (additive + prune extensions)"
```

---

### Task 4: Curated `settings.json`, `keybindings.json`, `snippets/`

**Files:**
- Create: `ide/vscode/settings.json`
- Create: `ide/vscode/keybindings.json`
- Create: `ide/vscode/snippets/.gitkeep`

**Interfaces:**
- Produces: the exact file content `apply` (Task 3) will symlink into VS Code's User directory.

- [ ] **Step 1: Write the verification check first**

Run this and confirm it currently fails (the file doesn't exist yet):

```bash
test -f ide/vscode/settings.json && python3 -c "
import json
d = json.load(open('ide/vscode/settings.json'))
assert 'atlascode.jira.lastCreateSiteAndProject' not in d
assert 'vs-kubernetes' not in d
assert 'black-formatter.path' not in d
assert d.get('evenBetterToml.formatter.indentEntries') is True
locs = d['chat.instructionsFilesLocations']
assert not any('/tmp/' in k or '/var/folders/' in k for k in locs)
assert d['workbench.colorTheme'] == 'Catppuccin Mocha'
print('OK')
"
```

Expected: FAIL (`test -f` fails, short-circuits before python3 runs)

- [ ] **Step 2: Create `ide/vscode/settings.json`**

```json
{
  "update.mode": "none",
  "editor.tokenColorCustomizations": {
    "textMateRules": [
      {
        "name": "One Dark italic",
        "scope": [
          "comment",
          "entity.other.attribute-name",
          "keyword",
          "markup.underline.link",
          "storage.modifier",
          "storage.type",
          "string.url",
          "variable.language.super",
          "variable.language.this"
        ],
        "settings": {
          "fontStyle": "italic"
        }
      },
      {
        "name": "One Dark italic reset",
        "scope": [
          "keyword.operator",
          "keyword.other.type",
          "storage.modifier.import",
          "storage.modifier.package",
          "storage.type.built-in",
          "storage.type.function.arrow",
          "storage.type.generic",
          "storage.type.java",
          "storage.type.primitive"
        ],
        "settings": {
          "fontStyle": ""
        }
      }
    ]
  },
  "redhat.telemetry.enabled": false,
  "editor.mouseWheelZoom": true,
  "terminal.integrated.fontSize": 14,
  "editor.fontSize": 14,
  "workbench.tree.indent": 20,
  "editor.fontFamily": "'JetBrains Mono', Menlo, Monaco, 'Courier New', monospace",
  "git.confirmSync": false,
  "files.exclude": {
    ".pytest*": true,
    ".vscode": true,
    "**/__pycache__": true,
    "**/.bloop": true,
    "**/.bsp": true,
    "**/.idea": true,
    "**/.metals": true,
    "**/.pytest_cache": true,
    "**/.vscode": true,
    "*pycache*": true
  },
  "files.autoSave": "afterDelay",
  "git.openRepositoryInParentFolders": "always",
  "files.watcherExclude": {
    "**/.ammonite": true,
    "**/.bloop/**": true,
    "**/.metals/**/*.{java,scala}": true
  },
  "git.autofetch": true,
  "editor.defaultFormatter": "vscode.json-language-features",
  "plantuml.render": "Local",
  "[markdown]": {
    "editor.defaultFormatter": "yzhang.markdown-all-in-one"
  },
  "[plantuml]": {
    "editor.defaultFormatter": "jebbs.plantuml"
  },
  "gitlens.codeLens.enabled": false,
  "[scala]": {
    "editor.defaultFormatter": "scalameta.metals"
  },
  "files.associations": {
    "*.Makefile": "makefile",
    "*.json5": "jsonc"
  },
  "explorer.confirmDragAndDrop": false,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "diffEditor.ignoreTrimWhitespace": false,
  "editor.fontWeight": "400",
  "[terraform]": {
    "editor.defaultFormatter": "hashicorp.terraform"
  },
  "[yaml]": {
    "editor.defaultFormatter": "redhat.vscode-yaml"
  },
  "database-client.autoSync": true,
  "aws.cloudformation.telemetry.enabled": false,
  "chat.instructionsFilesLocations": {
    ".github/instructions": true,
    ".claude/rules": true,
    "~/.copilot/instructions": true,
    "~/.claude/rules": true
  },
  "git.enableSmartCommit": true,
  "gitlens.currentLine.fontSize": 12,
  "gitblame.delayBlame": 50,
  "gitblame.inlineMessageEnabled": true,
  "workbench.iconTheme": "material-icon-theme",
  "[github-actions-workflow]": {
    "editor.defaultFormatter": "redhat.vscode-yaml"
  },
  "todo-tree.ripgrep.ripgrep": "/opt/homebrew/bin/rg",
  "makefile.configureOnOpen": false,
  "snyk.advanced.cliPath": "/Users/adas/Library/Application Support/snyk/vscode-cli/snyk-macos-arm64",
  "snyk.yesWelcomeNotification": false,
  "chat.viewSessions.orientation": "stacked",
  "json.schemaDownload.trustedDomains": {
    "https://developer.microsoft.com/json-schemas/": true,
    "https://docs.renovatebot.com/renovate-schema.json": true,
    "https://json-schema.org/": true,
    "https://json.schemastore.org/": true,
    "https://raw.githubusercontent.com/devcontainers/spec/": true,
    "https://raw.githubusercontent.com/microsoft/vscode/": true,
    "https://schemastore.azurewebsites.net/": true,
    "https://www.schemastore.org/": true
  },
  "yaml.disableSchemaDetection": [
    "**/.github/workflows/*.yml",
    "**/.github/workflows/*.yaml",
    "**/.gitea/workflows/*.yml",
    "**/.gitea/workflows/*.yaml",
    "**/.forgejo/workflows/*.yml",
    "**/.forgejo/workflows/*.yaml"
  ],
  "workbench.colorTheme": "Catppuccin Mocha",
  "evenBetterToml.formatter.indentEntries": true
}
```

Changes from the live file (per the design spec, §4): removed the 13 duplicate nested `"update.mode": "none"` keys (kept only the top-level one); removed the dead `atlascode.jira.lastCreateSiteAndProject` and `vs-kubernetes` blocks; removed the 12 stray `/tmp`/`/var/folders` postman paths from `chat.instructionsFilesLocations`; removed the malformed `black-formatter.path` value (letting the extension use its default resolution instead of guessing at a replacement); folded in Rusty's `evenBetterToml.formatter.indentEntries: true`; fixed the `'Jetbrains Mono'` casing typo to `'JetBrains Mono'`. `files.exclude`'s `.vscode` and `**/.vscode` entries are both kept — they're distinct intentional patterns (top-level vs. any depth), not duplicates.

- [ ] **Step 3: Create `ide/vscode/keybindings.json`**

```json
[]
```

(VS Code's own default content for an empty keybindings file — nothing is currently customized.)

- [ ] **Step 4: Create the snippets placeholder**

```bash
mkdir -p ide/vscode/snippets
touch ide/vscode/snippets/.gitkeep
```

(Empty today — git doesn't track empty directories, so this keeps the directory present and ready for `apply` to symlink. Delete `.gitkeep` once a real snippet file exists.)

- [ ] **Step 5: Run the verification check to confirm it passes**

Run the same command from Step 1.
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add ide/vscode/settings.json ide/vscode/keybindings.json ide/vscode/snippets/.gitkeep
git commit -m "Add curated vscode settings.json and keybindings.json"
```

---

### Task 5: Curated `extensions.txt`

**Files:**
- Create: `ide/vscode/extensions.txt`

**Interfaces:**
- Produces: the exact file `apply` (Task 3) reconciles installed extensions against.

- [ ] **Step 1: Write the verification check first**

```bash
test -f ide/vscode/extensions.txt && [ "$(wc -l < ide/vscode/extensions.txt | tr -d ' ')" = "71" ] && echo OK
```

Expected: FAIL (file doesn't exist yet)

- [ ] **Step 2: Create `ide/vscode/extensions.txt`**

```
aaron-bond.better-comments
alefragnani.project-manager
amazonwebservices.amazon-q-vscode
amazonwebservices.aws-toolkit-vscode
anthropic.claude-code
atlassian.atlascode
bokuweb.vscode-ripgrep
catppuccin.catppuccin-vsc
chrisdias.vscode-opennewinstance
cweijan.dbclient-jdbc
cweijan.vscode-redis-client
dbaeumer.vscode-eslint
eamodio.gitlens
esbenp.prettier-vscode
fill-labs.dependi
github.codespaces
github.remotehub
github.vscode-github-actions
gruntfuggly.todo-tree
hashicorp.terraform
jebbs.plantuml
kenhowardpdx.vscode-gist
lextudio.restructuredtext
mechatroner.rainbow-csv
mhutchie.git-graph
ms-azuretools.vscode-containers
ms-azuretools.vscode-docker
ms-kubernetes-tools.vscode-kubernetes-tools
ms-python.black-formatter
ms-python.debugpy
ms-python.isort
ms-python.pylint
ms-python.python
ms-python.vscode-pylance
ms-python.vscode-python-envs
ms-toolsai.jupyter
ms-toolsai.jupyter-keymap
ms-toolsai.jupyter-renderers
ms-toolsai.vscode-jupyter-cell-tags
ms-toolsai.vscode-jupyter-slideshow
ms-vscode-remote.remote-containers
ms-vscode.makefile-tools
ms-vscode.remote-repositories
ms-vscode.test-adapter-converter
oderwat.indent-rainbow
pkief.material-icon-theme
pomdtr.excalidraw-editor
postman.postman-for-vscode
redhat.fabric8-analytics
redhat.java
redhat.vscode-yaml
rust-lang.rust-analyzer
samuelcolvin.jinjahtml
scala-lang.scala
scala-lang.scala-snippets
scalameta.metals
serayuzgur.crates
streetsidesoftware.avro
tamasfe.even-better-toml
tgriesser.avro-schemas
trond-snekvik.simple-rst
usernamehw.errorlens
vadimcn.vscode-lldb
vscjava.vscode-gradle
vscjava.vscode-java-debug
vscjava.vscode-java-dependency
vscjava.vscode-java-pack
vscjava.vscode-java-test
vscjava.vscode-maven
vue.volar
yzhang.markdown-all-in-one
```

This is the union of the 5 former profiles' extension lists (87 unique), minus the 16 theme-shopping/redundant entries pruned per the design spec (§2): `akamud.vscode-theme-onedark`, `bungcip.better-toml`, `catppuccin.catppuccin-vsc-icons`, `catppuccin.catppuccin-vsc-pack`, `csantiago132.intellij-ish-darcula-theme`, `dracula-theme.theme-dracula`, `enkia.tokyo-night`, `equinusocio.vsc-material-theme`, `equinusocio.vsc-material-theme-icons`, `github.github-vscode-theme`, `hyperdarker.intellij-neo-dark`, `jeraldson.vscode-rusty-onedark`, `mskelton.one-dark-theme`, `nicohlr.pycharm`, `teabyii.ayu`, `zhuangtongfa.material-theme`.

- [ ] **Step 3: Run the verification check to confirm it passes**

Run the same command from Step 1.
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add ide/vscode/extensions.txt
git commit -m "Add curated unified vscode extensions.txt"
```

---

### Task 6: `ide/vscode/README.md`

**Files:**
- Create: `ide/vscode/README.md`

**Interfaces:**
- None (documentation only).

- [ ] **Step 1: Write the verification check first**

```bash
test -f ide/vscode/README.md && grep -q "snyk.advanced.cliPath" ide/vscode/README.md && grep -q "additive" ide/vscode/README.md && echo OK
```

Expected: FAIL (file doesn't exist yet)

- [ ] **Step 2: Create `ide/vscode/README.md`**

```markdown
# VS Code config

Single unified `Default` profile — no per-language profiles. See
`docs/superpowers/specs/2026-09-08-vscode-ide-config-design.md` for the
full rationale (why profiles were dropped, how the extension list was
curated, what was cleaned up).

## First-time setup on a new machine

```bash
./export   # only does anything if settings.json/keybindings.json aren't
            # already committed here — on a freshly cloned repo they will be
./apply    # symlinks settings/keybindings/snippets into place, installs
            # every extension in extensions.txt, uninstalls anything else
```

## Day-to-day

- **Change a setting, keybinding, or theme:** just do it in VS Code as
  normal — `settings.json`/`keybindings.json`/`snippets/` are live symlinks
  into this directory, so the change already landed here. `git diff`,
  commit.
- **Add an extension:** install it, then run `./export` to refresh
  `extensions.txt`, then commit. Other machines pick it up via
  `git pull && ./apply`.
- **Remove an extension:** uninstall it, `./export`, commit. `apply` is
  **additive + prune** — on every machine it runs on, it installs
  everything in `extensions.txt` *and* uninstalls anything installed that
  isn't listed, printing both lists before acting. A one-off extension
  installed locally without adding it to `extensions.txt` will get removed
  the next time `apply` runs there.

## Known machine-specific settings

These two values are baked to this machine's paths and aren't portable —
VS Code's `settings.json` has no variable substitution for arbitrary
extension keys. Adjust them after `apply` on a different machine:

- `snyk.advanced.cliPath`
- `black-formatter.path` (removed for now — add it back with a valid value
  if you want Black autoformatting; the malformed value that was here
  before was inert)

## Non-goals

- Golang-specific extensions — add `golang.go` (and anything else) yourself
  whenever you actually start Go work.
- Alpine Linux / `code-server` — not supported. Official VS Code doesn't
  ship for musl libc, and `code-server` pulls from Open VSX instead of the
  Marketplace `apply` expects.
```

- [ ] **Step 3: Run the verification check to confirm it passes**

Run the same command from Step 1.
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add ide/vscode/README.md
git commit -m "Add ide/vscode/README.md"
```

---

### Task 7: Wire into root docs

**Files:**
- Modify: `/Users/adas/dotfiles/README.md`
- Modify: `/Users/adas/dotfiles/CLAUDE.md`

**Interfaces:**
- None (documentation only).

- [ ] **Step 1: Write the verification check first**

```bash
grep -q "ide/vscode" README.md && grep -q "ide/vscode" CLAUDE.md && echo OK
```

Expected: FAIL (neither file mentions it yet)

- [ ] **Step 2: Add a section to `README.md`**

Append after the existing content:

```markdown

## VS Code

VS Code settings, keybindings, snippets, and extensions are managed under
`ide/vscode/` — single unified profile, no per-language profiles. See
`ide/vscode/README.md` for day-to-day usage and
`docs/superpowers/specs/2026-09-08-vscode-ide-config-design.md` for the
full design rationale.
```

- [ ] **Step 3: Add a row to `CLAUDE.md`'s file map table**

In the `## File map` table, add a row (after the `home/.ssh/config` row):

```markdown
| `ide/vscode/`      | VS Code settings/keybindings/snippets (live symlinks) + extensions.txt (installed via `ide/vscode/apply`) |
```

- [ ] **Step 4: Run the verification check to confirm it passes**

Run the same command from Step 1.
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "Document ide/vscode/ in root README and CLAUDE.md"
```

---

### Task 8: Run `export` then `apply` for real on this machine

This task makes real, live changes to this machine's actual VS Code
configuration: it replaces the real `settings.json`/`keybindings.json`/
`snippets/` with symlinks (backing up the originals first, per Task 3's
`apply` logic) and installs/uninstalls real extensions in the `Default`
profile. Confirm before running — this is the one task in this plan that
touches live state outside the repo.

**Files:** none created — this task exercises Tasks 2–5's deliverables against the real machine.

- [ ] **Step 1: Run `export` first, to confirm it's a no-op**

```bash
cd ~/dotfiles/ide/vscode && ./export
```

Expected output includes a line like `vscode-export: wrote 59 extensions to
extensions.txt` (the live Default profile still has its old ~59-extension
list at this point) and **no** "bootstrapped" line, since Task 4 already
created `settings.json`/`keybindings.json` in the repo. Since `export`
always regenerates `extensions.txt` from the live install, this run
temporarily overwrites Task 5's curated 71-line file with the live
59-line one — expected, and fixed by `apply` in Step 3 below.

- [ ] **Step 2: Restore the curated extensions.txt**

```bash
cd ~/dotfiles && git checkout ide/vscode/extensions.txt
```

(`export`'s job is to snapshot *current* installs when you've just changed
something by hand; it isn't the right tool for a one-time bulk migration
onto a curated list. `apply`, next, is.)

- [ ] **Step 3: Run `apply`**

```bash
cd ~/dotfiles/ide/vscode && ./apply
```

Expected: prints backup lines for `settings.json` and `keybindings.json`
(the real pre-existing files, now saved as `.bak-<timestamp>`), a "linked"
line for each of `settings.json`/`keybindings.json`/`snippets`, an
"installing" block listing the 23 new extensions from the design spec's
§2 diff (`aaron-bond.better-comments`, `amazonwebservices.amazon-q-vscode`,
`atlassian.atlascode`, `bokuweb.vscode-ripgrep`, `catppuccin.catppuccin-vsc`,
`chrisdias.vscode-opennewinstance`, `cweijan.dbclient-jdbc`,
`cweijan.vscode-redis-client`, `github.codespaces`,
`github.vscode-github-actions`, `gruntfuggly.todo-tree`,
`mechatroner.rainbow-csv`, `ms-azuretools.vscode-containers`,
`ms-kubernetes-tools.vscode-kubernetes-tools`,
`ms-python.vscode-python-envs`, `pomdtr.excalidraw-editor`,
`postman.postman-for-vscode`, `redhat.fabric8-analytics`,
`serayuzgur.crates`, `streetsidesoftware.avro`, `tgriesser.avro-schemas`,
`usernamehw.errorlens`, `vadimcn.vscode-lldb`), and a "pruning" block
listing the 11 removed ones present in the live Default profile
(`akamud.vscode-theme-onedark`, `bungcip.better-toml`,
`dracula-theme.theme-dracula`, `equinusocio.vsc-material-theme`,
`equinusocio.vsc-material-theme-icons`, `github.github-vscode-theme`,
`hyperdarker.intellij-neo-dark`, `mskelton.one-dark-theme`,
`nicohlr.pycharm`, `teabyii.ayu`, `zhuangtongfa.material-theme`).

- [ ] **Step 4: Verify the real machine now matches the repo**

```bash
readlink "$HOME/Library/Application Support/Code/User/settings.json"
# expect: /Users/adas/dotfiles/ide/vscode/settings.json

readlink "$HOME/Library/Application Support/Code/User/keybindings.json"
# expect: /Users/adas/dotfiles/ide/vscode/keybindings.json

diff <(code --list-extensions | LC_ALL=C sort) <(LC_ALL=C sort ~/dotfiles/ide/vscode/extensions.txt)
# expect: no output (exact match)
```

- [ ] **Step 5: Restart VS Code** so the new symlinked settings/keybindings take effect, and spot-check that Catppuccin Mocha + material-icon-theme still render correctly.

- [ ] **Step 6: Commit** (only if `apply` or the checks above surfaced anything worth recording — e.g. if you note the backup file paths for your own reference)

```bash
git add -A && git commit -m "Apply unified vscode config on work Mac" --allow-empty
```
