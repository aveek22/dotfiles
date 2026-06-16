# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Personal macOS dotfiles for a data/platform engineer. Files live in `home/` and are symlinked into `~`.

## Setup (first time)

```bash
ln -s ~/dotfiles/home/.zshrc ~/.zshrc
ln -s ~/dotfiles/home/.ssh/config ~/.ssh/config
```

For the custom oh-my-zsh agnoster theme, symlink `scripts/oh-my-zsh/agnoster.zsh-theme` into `~/.oh-my-zsh/themes/` replacing the default, then `source ~/.zshrc`.

Install Homebrew packages: `brew bundle --file=brew/Brewfile`

## File map

| Path               | Purpose                                                                                            |
| ------------------ | -------------------------------------------------------------------------------------------------- |
| `home/.zshrc`      | Zsh config — oh-my-zsh (agnoster theme), PATH exports, tool initialisation (pyenv, sdkman, poetry) |
| `home/.alias`      | All shell aliases (sourced by `.zshrc`)                                                            |
| `home/.ssh/config` | SSH host aliases for work GitHub, personal GitHub, and Bitbucket                                   |
| `brew/Brewfile`    | Homebrew formulae and casks                                                                        |
| `scripts/kube`     | Interactive script to update kubeconfig and open k9s for one of the three EKS clusters             |
| `itermcolors/`     | iTerm2 colour scheme `.itermcolors` files — import manually via iTerm2 preferences                 |

## Alias conventions in `home/.alias`

Aliases are grouped by tool. Key prefixes:

- `k` / `kcc` / `kcp` / `kt` — kubectl and Kafka CLI shortcuts
- `g` / `gc` / `ga` etc. — git shortcuts
- `d` / `dc` — docker / docker-compose
- `t` / `ti` / `tp` / `ta` / `taa` — terraform
- `awslogin` / `aws-*` / `at` / `ap` / `aet` / `aep` — AWS SSO login and ECR auth (rs-test / rs-prod accounts; data account)
- `kube` — calls `scripts/kube` for EKS cluster selection
- `pumlsvg` — generate SVG from `.puml` files using local PlantUML jar

## AWS profiles

| Alias      | Profile   | Account      |
| ---------- | --------- | ------------ |
| `at`       | `rs-test` | 975050087796 |
| `ap`       | `rs-prod` | 058264079373 |
| `aws-data` | `data`    | —            |

ECR login (`aet` / `aep`) sets the profile and pipes credentials into `docker login` for the matching registry.

## Kubernetes script (`scripts/kube`)

Presents a menu of three EKS clusters, runs `aws eks update-kubeconfig`, then opens k9s. Aliased as `kube` in the shell.
