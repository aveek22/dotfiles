# dotfiles
Personal repository to host my dotfiles

## Add symlink

- Delete the `.zshrc` file from `~`.
- Clone the repo to user root.
- Add symlink `ln -s ~/dotfiles/home/.zshrc ~/.zshrc`.
- Source terminal `source ~/.zshrc`

## VS Code

VS Code settings, keybindings, snippets, and extensions are managed under
`ide/vscode/` — single unified profile, no per-language profiles. See
`ide/vscode/README.md` for day-to-day usage and
`docs/superpowers/specs/2026-09-08-vscode-ide-config-design.md` for the
full design rationale.