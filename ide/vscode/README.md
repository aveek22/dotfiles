# VS Code config

Single unified `Default` profile — no per-language profiles. See
`docs/superpowers/specs/2026-09-08-vscode-ide-config-design.md` for the
full rationale (why profiles were dropped, how the extension list was
curated, what was cleaned up).

## First-time setup on a new machine

```bash
make export   # only does anything if settings.json/keybindings.json aren't
                # already committed here — on a freshly cloned repo they will be
make apply    # symlinks settings/keybindings/snippets into place, installs
                # every extension in extensions.txt, uninstalls anything else
```

`make` alone (no target) prints the available commands: `apply`, `export`,
`prune` (alias for `apply` — pruning is bundled into it, not a separate
step), `test`. Plain `./export`/`./apply` still work directly if you'd
rather skip `make`.

## Day-to-day

- **Change a setting, keybinding, or theme:** just do it in VS Code as
  normal — `settings.json`/`keybindings.json`/`snippets/` are live symlinks
  into this directory, so the change already landed here. `git diff`,
  commit.
- **Add an extension:** install it, then run `make export` to refresh
  `extensions.txt`, then commit. Other machines pick it up via
  `git pull && make apply`.
- **Remove an extension:** uninstall it, `make export`, commit. `apply`
  (and `prune`, its alias) is **additive + prune** — on every machine it
  runs on, it installs everything in `extensions.txt` *and* uninstalls
  anything installed that isn't listed, printing both lists before acting.
  A one-off extension installed locally without adding it to
  `extensions.txt` will get removed the next time `apply` runs there.

## Known machine-specific settings

VS Code's `settings.json` has no variable substitution for arbitrary
extension keys, so a path baked to one machine won't resolve on another.
Currently nothing tracked here has that problem — `snyk.advanced.cliPath`
was removed (the Snyk extension isn't used) and `black-formatter.path` was
removed (its old value was malformed and inert anyway). If you add a
setting with an absolute machine-specific path later, note it here.

- `black-formatter.path` — add it back with a valid value if you want
  Black autoformatting; it's not tracked here right now.

## Non-goals

- Golang-specific extensions — add `golang.go` (and anything else) yourself
  whenever you actually start Go work.
- Alpine Linux / `code-server` — not supported. Official VS Code doesn't
  ship for musl libc, and `code-server` pulls from Open VSX instead of the
  Marketplace `apply` expects.
