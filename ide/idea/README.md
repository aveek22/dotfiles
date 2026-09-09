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
