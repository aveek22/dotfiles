# IntelliJ IDEA config in dotfiles — design

**Date:** 2026-09-09
**Status:** Approved, pending implementation plan

## Context

Following the same account-independent, symlink-based approach used for
VS Code (`docs/superpowers/specs/2026-09-08-vscode-ide-config-design.md`),
the goal is to centralize IntelliJ IDEA settings/shortcuts/etc. in
`dotfiles/ide/idea` so a work Mac and a personal Mac converge on one setup,
synced via git.

**Scope, decided up front:** settings, keymap/shortcuts, color scheme, code
style, and templates — not plugins. IntelliJ has no clean equivalent of
`code --install-extension` (the `idea` CLI shim just launches the full GUI
app via `open -na`; its `installPlugins` subcommand requires the IDE fully
closed and is slower/less battle-tested, with no reliable prune/uninstall
counterpart). The user manages plugin installation manually. `plugins.txt`
is still tracked, but purely as a **reference snapshot** — see Decision 5.

**Investigation findings that shaped the design** (from this machine,
IntelliJ IDEA 2026.2):

- `keymaps/`, `colors/`, `templates/` (live templates), and `fileTemplates/`
  are all currently **empty** — nothing has been customized away from
  IntelliJ's defaults yet. `codestyles/Default.xml` exists but is the stock
  default (44 bytes).
- `options/` holds ~60 individual XML files, mixing genuine user
  preferences with machine state, telemetry, caches, and account identity —
  unlike VS Code's single curated `settings.json`, this can't be symlinked
  wholesale.
- Spot-checking file contents surfaced concrete, non-obvious risks:
  - `ui.lnf.xml` is misleadingly named — it actually holds project-view
    file-nesting rules (`.js`/`.js.map` groupings etc.), not theme/Look and
    Feel. Content is fully portable.
  - `nodejs.xml` bakes in an absolute interpreter path
    (`/opt/homebrew/bin/node`) — machine-specific.
  - `github.xml` ties to this machine's work GitHub account
    (`aveek-das_DPGMEDIA`) — exactly the account-independence problem the
    VS Code design solved for. Must be excluded.
  - `git_toolbox_blame.xml` is a clean, portable preference
    (`blameInlineAuthorNameType=FIRSTNAME`) — safe to include.
  - `ide.general.xml` mixes one real preference
    (`confirmOpenNewProject2`) with auto-managed `Registry` entries IntelliJ
    writes for itself (`ide.experimental.ui`, a JetBrains trace-status URL).
    Syncing the whole file risks carrying stale/experimental flags onto
    another machine for one preference's worth of benefit — excluded for
    now.
- IntelliJ's config directory is version-qualified
  (`~/Library/Application Support/JetBrains/IntelliJIdea<version>/`) and
  this machine has two: `IntelliJIdea2026.1` and `IntelliJIdea2026.2`.
  IntelliJ migrates settings into a new version dir automatically on first
  launch after an upgrade.

## Decisions

### 1. Directory layout

Nested under `ide/`, alongside `ide/vscode/`, following the same
self-contained-per-tool pattern:

```
ide/
└── idea/
    ├── Makefile           # help / apply / export / test
    ├── apply              # symlinks tracked files+dirs into the live config dir
    ├── export             # bootstraps repo copies from the live config dir
    ├── lib.sh             # idea_config_dir() + shared IDEA_OPTION_FILES list
    ├── README.md          # rationale, excluded-file list, non-goals
    ├── plugins.txt        # reference snapshot only — see Decision 5
    ├── options/           # curated individual XML files (subset of the real options/)
    │   ├── colors.scheme.xml
    │   ├── console-font.xml
    │   ├── editor-font.xml
    │   ├── terminal-font.xml
    │   ├── ui.lnf.xml
    │   ├── find.xml
    │   ├── findUsages.xml
    │   ├── diff.xml
    │   ├── debugger.xml
    │   ├── filetypes.xml
    │   ├── overrideFileTypes.xml
    │   ├── csvSettings.xml
    │   ├── git_toolbox_blame.xml
    │   ├── javaRuleManager.xml
    │   ├── scala.xml
    │   ├── scala_config.xml
    │   ├── spellchecker-dictionary.xml
    │   ├── textmate.xml
    │   ├── advancedSettings.xml
    │   └── avro_idl.xml
    ├── keymaps/           # whole-dir symlink target (empty today)
    ├── colors/            # whole-dir symlink target (empty today)
    ├── templates/         # whole-dir symlink target (live templates, empty today)
    ├── fileTemplates/     # whole-dir symlink target (empty today)
    ├── codestyles/        # whole-dir symlink target (Default.xml, stock default)
    └── tests/             # mirrors ide/vscode/tests/ structure
```

### 2. Sync mechanism: two-tier symlinks (whole-dir + curated file)

Two different symlink strategies, chosen per directory based on whether
*everything* in it is inherently a deliberate customization:

- **Whole-directory symlink** for `keymaps/`, `colors/`, `templates/`,
  `fileTemplates/`, `codestyles/` — anything a user places in these dirs
  *is* a customization (a saved custom keymap, an exported color scheme, a
  live template, etc.), so there's no noise to curate out. Same trick as
  VS Code's `snippets/`. All five are currently empty or stock-default, but
  the mechanism is in place so any future customization is captured
  automatically with zero extra steps.
- **Curated individual-file symlink** for `options/`, since it mixes real
  settings with machine state, telemetry, caches, and account identity that
  must never be synced. `lib.sh` defines the allowlist once, as a single
  source of truth both `apply` and `export` iterate over:

  ```bash
  IDEA_OPTION_FILES=(
      colors.scheme.xml console-font.xml editor-font.xml terminal-font.xml
      ui.lnf.xml find.xml findUsages.xml diff.xml debugger.xml
      filetypes.xml overrideFileTypes.xml csvSettings.xml git_toolbox_blame.xml
      javaRuleManager.xml scala.xml scala_config.xml spellchecker-dictionary.xml
      textmate.xml advancedSettings.xml avro_idl.xml
  )
  ```

### 3. Version-dir resolution

`lib.sh` resolves the newest `IntelliJIdea<version>` directory rather than
hardcoding a version string, so the setup survives IntelliJ upgrades
without edits:

```bash
idea_config_dir() {
    ls -d "$HOME/Library/Application Support/JetBrains/IntelliJIdea"* 2>/dev/null \
        | sort -V | tail -1
}
```

If no such directory exists at all (fresh machine, IDE never launched),
`apply` fails with a clear message telling the user to launch IntelliJ once
first so the config directory gets created — same pattern as `vscode/apply`
guarding on the `code` CLI not being in `PATH` yet.

### 4. Excluded from tracking (documented in README, not just omitted silently)

- **Machine-specific paths:** `nodejs.xml` (interpreter path),
  `path.macros.xml`, `jdk.table.xml`, `proxy.settings.xml`
- **Account-specific:** `github.xml`, `gitlab.xml` — tied to this machine's
  work JetBrains/GitHub identity; syncing would break work/personal
  independence, the same failure mode the VS Code design avoided by keeping
  auth out of file-based config entirely.
- **Sensitive/environment-specific:** `databaseDrivers.xml`,
  `databaseSettings.xml`, `remote-servers.xml`
- **Mixed real-setting + auto-managed state:** `ide.general.xml` — see
  investigation findings above. Revisit later if a setting inside it
  actually matters enough to accept the risk.
- **Pure machine state/telemetry/cache:** everything else under `options/`
  not in `IDEA_OPTION_FILES` — `recentProjects.xml`, `window.state.xml`,
  `window.layouts.xml`, `usage.statistics.xml`,
  `features.usage.statistics.xml`, `trusted-paths.xml`,
  `actionSummary.xml`, `jupyter-settings-v2.xml`, feedback/onboarding/survey
  files, `scalafmt_dynamic_resolve_cache.xml`, and similar.

### 5. `plugins.txt` — reference snapshot, no install/uninstall automation

Reinstated after initially being scoped out, but strictly as a personal
record, not an automation target:

- `export` regenerates `plugins.txt` **unconditionally** every run (like
  `extensions.txt`) — sorted plugin folder names from
  `<config_dir>/plugins/`.
- `apply` **never touches plugins** — no install, no uninstall, no
  reconciliation. Plugin management stays fully manual via the Marketplace
  UI, per the user's stated preference.
- Folder names are a human-readable memory aid for re-searching the
  Marketplace on a new machine, not guaranteed to be the exact Marketplace
  plugin ID — confirmed during investigation that several installed
  plugins (`gittoolbox`, `terraform`, `github-actions-manager`,
  `avro-schema-support`) don't expose their ID at a shallow jar path the way
  `makefile`/`astro`/`vitejs` did. README calls this out explicitly so it's
  never mistaken for an installable identifier list.

## Day-2 workflow (adding settings, shortcuts, plugins)

**Setting/keymap/color-scheme/template change:** no export step needed for
anything under the five whole-directory areas — `keymaps/`, `colors/`,
`templates/`, `fileTemplates/`, `codestyles/` are live symlinks, so
customizing in IntelliJ writes straight through to the repo. Just
`git diff`, commit, `git pull` on other machines.

**Tracking a *new* `options/*.xml` file** (e.g. a fresh customization, or a
new plugin adds a preferences file you want synced):

1. Customize the setting in IntelliJ as normal.
2. Find the new/changed file under the live `options/` dir.
3. **Review its content** for machine-specific paths, account identity, or
   secrets — the same check applied to `github.xml`/`nodejs.xml`/
   `ide.general.xml` during this design's investigation — before deciding
   it's safe to track.
4. Add its filename to `IDEA_OPTION_FILES` in `ide/idea/lib.sh`.
5. Run `ide/idea/export` — bootstraps that file into `ide/idea/options/`
   for the first time (bootstrap-once semantics, same as
   `vscode/export`'s handling of `settings.json`).
6. `git diff`, commit.
7. Other machines: `git pull`, then `ide/idea/apply` — the file is now in
   the shared list, so it gets symlinked there too (backing up whatever
   local copy exists first).

Adding to the allowlist is a deliberate, reviewed, one-line edit — not an
automatic reconcile-from-everything-installed the way VS Code's
`extensions.txt` is. There's no IntelliJ equivalent of "regenerate the whole
list from what's installed" here, since the source is a curated subset by
design, not everything present.

**Installing/removing a plugin:** manage it yourself via the Marketplace UI
as always. Run `ide/idea/export` afterward if you want `plugins.txt`
refreshed as a record; nothing else needs to happen, and no other machine's
`apply` will install or remove anything as a result.

## Non-goals / explicitly deferred

- **Scripted plugin install/uninstall** — rejected due to `idea` CLI
  limitations (requires IDE fully closed, slow, no reliable prune) and the
  user's explicit preference to self-manage plugins.
- **`ide.general.xml`** — deferred pending a concrete need for the one real
  preference it holds; not worth the Registry/experiment-flag risk today.
- **Other JetBrains products** (PyCharm, DataGrip, WebStorm, etc.) — only
  IntelliJ IDEA is installed on this machine; not designed for now.
- **IntelliJ's built-in cloud Settings Sync** — rejected as the sync
  mechanism itself, same reasoning as VS Code's built-in Settings Sync: it
  ties sync to one JetBrains/cloud account and would fight a symlink-based
  approach by writing into the same live files.

## Answers to the original question (for the record)

**What's the workflow for adding more [settings/plugins] to the dotfiles in
the future?** Two different answers depending on which:

- Whole-directory areas (keymap, colors, templates, file templates, code
  style): automatic — the symlink means any customization already lives in
  the repo the moment you make it.
- `options/*.xml` settings: manual, reviewed, one-line addition to
  `IDEA_OPTION_FILES` in `lib.sh`, then `export` to bootstrap it in. Kept
  manual deliberately, since `options/` mixes real settings with
  machine-specific/sensitive files that must never be auto-synced.
- Plugins: no dotfiles workflow at all beyond an unconditionally
  regenerated `plugins.txt` reference snapshot — installation stays fully
  manual, by design.

## Addendum (2026-09-09): active-keymap pointer lives in a subdirectory

First real use of the "add a new tracked settings file" workflow (setting
a custom `Ctrl+~` terminal-toggle shortcut) surfaced a gap this design
didn't anticipate: *which* keymap is active isn't recorded directly under
`options/`, but under a platform-specific subdirectory,
`options/mac/keymap.xml` — a one-line pointer
(`<active_keymap name="..."/>`), directly analogous to `colors.scheme.xml`
in every way that mattered for the original allowlist criteria (pure
preference, no absolute paths, no account identity). Two adjacent files
checked at the same time and confirmed **not** worth tracking:
`keymapFlags.xml` (bookkeeping for which keymap-related UI notices have
already been shown) and `other.xml` (a large generic bucket mixing dozens
of unrelated UI-state values — search-history strings, splitter
proportions — alongside one incidental `"KEYMAP": "terminal"` entry that
was just the Keymap settings dialog's last search query, not an
active-keymap pointer).

`IDEA_OPTION_FILES` entries were generalized to allow a subdirectory
component (`mac/keymap.xml`), and `apply`/`export` were fixed to create
the parent directory on whichever side needs it — `export`'s `cp` failed
outright on a repo that had never bootstrapped that subdirectory before
(caught by a new test asserting bootstrap into a not-yet-existing
`options/mac/`); `apply` was fixed defensively for the mirror case (a
fresh machine where the live `options/mac/` has also never been created),
even though the real machine here already had it. Both fixes are
backward-compatible — a flat filename's `dirname` is `.`, so the added
`mkdir -p` is a no-op for every existing entry.
