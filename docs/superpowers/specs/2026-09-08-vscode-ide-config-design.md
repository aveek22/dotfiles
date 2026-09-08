# VS Code (and future IDE) config in dotfiles — design

**Date:** 2026-09-08
**Status:** Approved, pending implementation plan

## Context

Three machines need to converge on one VS Code setup: a work MacBook (this
machine), a personal MacBook, and an Ubuntu machine. The goal was originally
framed as "account independence" — being able to log in with a different
email per machine (work Copilot benefits vs. personal) without that leaking
into shared config.

**Finding that shaped the whole design:** VS Code account/auth state
(Copilot/Chat sign-in, Settings Sync account) lives in OS keychain / VS
Code's own secret storage — never in `settings.json`, `keybindings.json`,
extensions lists, or anything else this design touches. Account independence
was never actually at risk; it falls out for free once config lives in
dotfiles instead of VS Code's built-in cloud Settings Sync (which *would*
tie sync to one account — rejected for that reason, and because the user
can't use one GitHub account across all machines anyway).

## Decisions

### 1. Single unified profile — no per-language profiles

The machine had 5 VS Code profiles (Default, FrontEnd, JVM, Python, Rusty).
Investigation showed:

- FrontEnd/JVM/Python already had `useDefaultFlags: {settings, keybindings,
  snippets, tasks: true, extensions: false}` — they only ever diverged on
  *extensions*, not settings.
- Rusty had a genuinely separate `settings.json`, but the only real
  divergence was a different color theme and one harmless TOML-formatter
  setting — "probably a mistake" per the user, folded into shared settings.
- `profileAssociations` in `globalStorage/storage.json` showed the profiles
  weren't actually being used for per-project switching in practice — nearly
  every workspace (including clearly JVM/Scala ones) was parked on the
  Python profile regardless of stack.
- VS Code extensions activate lazily per file type
  (`activationEvents: onLanguage:*`) for the large majority of extensions
  ([VS Code docs](https://code.visualstudio.com/api/references/activation-events)).
  Live evidence from `code --status` on this machine: with the Python
  profile active and only markdown/JSON files open, only the markdown and
  JSON language servers had actually spawned — not Pylance, Jupyter, or any
  of the other ~40 enabled-but-idle extensions. Merging everything into one
  profile does not make idle extensions activate; only opening a matching
  file type does.
- The one real cost of merging: extensions with eager/`*`-style activation
  run everywhere once merged, regardless of relevance. Confirmed one
  concrete case on this machine: AWS Toolkit's CloudFormation language
  server (`cfn-lsp-server-standalone.js`) was already running with zero
  CloudFormation files in the workspace. This is a per-extension property,
  not a reason to keep separate profiles.

**Decision:** collapse to a single `Default` profile everywhere. No
FrontEnd/JVM/Python/Rusty profiles going forward, and no new Golang profile
(user will add Go tooling manually later, whenever needed — out of scope
here).

The 4 now-unused profiles on this machine are left as-is; deleting them from
VS Code's Profiles UI is a manual step the user does later, not scripted by
this work (profile deletion isn't CLI-scriptable).

### 2. Unified extension list

Computed as the union of all 5 profiles' extension lists (87 unique),
minus 16 items identified as theme-shopping debris or redundant duplicates
— safe to drop once one shared theme wins:

```
akamud.vscode-theme-onedark
bungcip.better-toml                  (superseded by tamasfe.even-better-toml)
catppuccin.catppuccin-vsc-icons       (icon theme is material-icon-theme, not this)
catppuccin.catppuccin-vsc-pack
csantiago132.intellij-ish-darcula-theme
dracula-theme.theme-dracula
enkia.tokyo-night
equinusocio.vsc-material-theme
equinusocio.vsc-material-theme-icons
github.github-vscode-theme
hyperdarker.intellij-neo-dark
jeraldson.vscode-rusty-onedark
mskelton.one-dark-theme
nicohlr.pycharm
teabyii.ayu
zhuangtongfa.material-theme
```

Result: **71 extensions** (see `ide/vscode/extensions.txt` once written —
full list also captured in the implementation plan). No account/login
needed to install any of them — `code --install-extension` is anonymous
against the Marketplace on macOS and Ubuntu alike (this is not true for
Alpine/`code-server`, which uses Open VSX and isn't supported here — an
explicit non-goal, see below).

### 3. Shared theme

All profiles now render the same `workbench.colorTheme` — kept as
**Catppuccin Mocha** (Default's existing choice) with `material-icon-theme`
for icons. Rusty's distinct "Rusty One Dark" theme is intentionally lost as
a consequence of unifying settings — this was called out explicitly and
accepted.

### 4. `settings.json` cleanup

Applied while extracting the file into the repo:

- Remove stray `/tmp/postman-*` and `/var/folders/.../postman-*` entries
  from `chat.instructionsFilesLocations` (leftover temp-file references,
  not intentional config).
- Remove the empty `atlascode.jira.lastCreateSiteAndProject` block (dead
  state, regenerates on actual use).
- Remove the `vs-kubernetes` block (`minikube-path-linux` pointed at a
  Linux path on a macOS config; `minikube-show-information-expiration` is
  an auto-generated timestamp). Safe to drop — `ms-kubernetes-tools` is in
  the unified extension list, so the extension is still installed; it'll
  regenerate sane defaults if minikube is ever actually used. (The user
  manages real clusters via `scripts/kube` / EKS, not local minikube.)
- Collapse duplicate `"update.mode": "none"` keys — found nested inside
  nearly every settings object (`files.exclude`, `[python]`, `[yaml]`,
  etc.) in addition to the correct top-level key. Clear corruption from a
  prior bulk write; keep only the top-level key.
- Fold in Rusty's `evenBetterToml.formatter.indentEntries: true` (harmless
  everywhere, useful for any TOML file — Cargo.toml, pyproject.toml, etc.).

Also found while reviewing: `black-formatter.path` currently holds
`["\"poetry run black .\"]"]`  — a malformed value (a string that's
itself literal bracket/quote characters, not a real args array). Combined
with the extension not even being installed in the old Python profile
(§2's unification fixes that half), this setting was effectively dead.
Fix to a valid value (or remove it and let the extension use its default
resolution) while cleaning up.

Two settings remain genuinely machine-specific and are **not** portable —
VS Code's `settings.json` has no OS/path variable substitution for
arbitrary extension keys:
- `snyk.advanced.cliPath` — absolute path baked to this user's home dir.
- `black-formatter.path` — once fixed to a valid value, still machine-specific
  if it references an absolute interpreter/poetry path.

These get a one-line callout in `ide/vscode/README.md` (or equivalent) to
adjust per machine after symlinking, rather than a false promise of full
portability.

### 5. Directory layout

Nested under `ide/` (not a top-level `vscode/`) specifically so other IDEs
(IntelliJ was already flagged as a gap in `improvement.md`) can follow the
same self-contained-per-tool pattern later, consistent with how
`itermcolors/` and `brew/Brewfile` already work in this repo:

```
ide/
└── vscode/
    ├── settings.json      # single shared settings.json, cleaned (see §4)
    ├── keybindings.json    # exported as-is (currently VS Code defaults)
    ├── snippets/            # exported as-is (currently empty)
    ├── extensions.txt       # 71-item unified list (see §2)
    ├── export               # dumps live VS Code config into this directory
    └── apply                 # symlinks config in + installs extensions
```

### 6. Sync mechanism: symlinks + install script (hybrid)

- `settings.json`, `keybindings.json`, `snippets/` are **live symlinks**
  from VS Code's real User directory into `ide/vscode/` — matches this
  repo's existing pattern (`.zshrc`, `.ssh/config`) and the user's stated
  preference. VS Code writes these files in place, so the symlink survives
  normal editing.
- User directory path differs by OS and must be resolved by the `apply`
  script, not hardcoded:
  - macOS: `~/Library/Application Support/Code/User/`
  - Ubuntu (official VS Code, not code-server): `~/.config/Code/User/`
- Extensions **cannot** be symlinked — installing a package isn't writing a
  file. `export` runs `code --list-extensions` into `extensions.txt`;
  `apply` reads it back and runs `code --install-extension` per line
  (idempotent — already-installed extensions are no-ops). Same mechanism
  works unmodified on Ubuntu since it's official VS Code + the same MS
  Marketplace, not code-server/Open VSX.
- No profile-hash resolution needed anywhere in this design — that
  complexity only existed when Rusty had its own `settings.json` under an
  opaque per-machine profile folder. Collapsing to one profile removes it
  entirely.

## Non-goals / explicitly deferred

- **Golang extensions/tooling** — user will add `golang.go` (and anything
  else) manually, whenever they actually start Go work. Not part of this
  pass.
- **Alpine Linux / `code-server`** — raised as a hypothetical while
  checking the account-independence boundary, not an actual target. Official
  VS Code doesn't ship for musl libc; `code-server` pulls from Open VSX
  instead of the MS Marketplace, which the `apply` script doesn't handle.
  Documented as a known limitation, not designed for.
- **Deleting the 4 now-unused profiles from this machine's VS Code** — a
  manual, non-scriptable UI step the user will do later.
- **Other IDEs (IntelliJ, etc.)** — the `ide/` parent directory is named to
  leave room for this, but no other IDE's config is implemented now.

## Answers to the original questions (for the record)

1. **Is this maintainable/evolvable?** Yes. The design turned out simpler
   than initially scoped, once profile-per-language was reconsidered — one
   settings surface, one extension list, two small scripts, OS-aware paths.
   Account independence was never really at risk since VS Code auth is
   OS-keychain-scoped, not file-based.
2. **Is per-language profiling worth it for a polyglot dev?** No, given
   this user's actual usage pattern (profiles existed but weren't being
   switched per-project in practice) and VS Code's lazy, per-file-type
   extension activation model (confirmed live on this machine via
   `code --status`). The one place profiles would earn their keep — walling
   off a genuinely eager/`*`-activating extension — is better solved by
   fixing or removing that specific extension than by maintaining parallel
   profiles.
