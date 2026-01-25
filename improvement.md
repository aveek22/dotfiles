# Dotfiles Improvement Plan
**Last Updated:** 25 January 2026  
**Target:** Senior Software Engineer - Java, Scala, Python, Docker, K8s Development on macOS

---

## Executive Summary

Current state analysis reveals a functional but **fragmented dotfiles setup** with several critical gaps for enterprise-grade development. Key areas requiring immediate attention:

- ✅ **Working:** Basic shell configuration, Kafka/AWS tooling, Docker aliases
- ⚠️ **Missing:** Version management for JVM languages, automated installation, security hardening
- ❌ **Critical Gaps:** No JVM tooling, missing IDE configurations, no backup/restore strategy

---

## 🔴 CRITICAL IMPROVEMENTS (Priority 1)

### 1. JVM Version Management with SDKMAN - **PARTIALLY CONFIGURED**
**Problem:** SDKMAN is installed but not fully configured for multi-version Java/Scala management.

**Impact:** Cannot easily switch between Java versions for different projects (Java 8, 11, 17, 21) or manage Scala versions.

**Solution:**
```bash
# SDKMAN is already initialized in .zshrc - enhance usage
# No Brewfile additions needed - SDKMAN manages everything

# Install multiple Java versions
sdk install java 11.0.25-tem
sdk install java 17.0.13-tem
sdk install java 21.0.5-tem
sdk install java 8.0.432-tem

# Install Scala versions
sdk install scala 2.12.20
sdk install scala 2.13.15
sdk install scala 3.3.4

# Install other JVM tools
sdk install gradle 8.12
sdk install maven 3.9.9
sdk install sbt 1.10.6
```

**Implementation:**
- [ ] Verify SDKMAN installation: `sdk version`
- [ ] Install multiple Java/Scala versions via SDKMAN
- [ ] Configure project-specific versions using `.sdkmanrc` files
- [ ] Add SDKMAN usage guide to README
- [ ] Create aliases for quick version switching

**SDKMAN Aliases for `.alias`:**
```bash
# SDKMAN - Quick version management
alias sdkl="sdk list"
alias sdki="sdk install"
alias sdku="sdk use"
alias sdkd="sdk default"
alias sdkc="sdk current"
alias sdkupgrade="sdk upgrade"
alias sdkupdate="sdk update"

# Quick Java switching
alias java8="sdk use java 8.0.432-tem"
alias java11="sdk use java 11.0.25-tem"
alias java17="sdk use java 17.0.13-tem"
alias java21="sdk use java 21.0.5-tem"

# Quick Scala switching
alias scala212="sdk use scala 2.12.20"
alias scala213="sdk use scala 2.13.15"
alias scala3="sdk use scala 3.3.4"
```

**Project-specific `.sdkmanrc` example:**
```bash
# Place in project root
# Automatically switches versions when entering directory
java=17.0.13-tem
scala=2.13.15
maven=3.9.9
gradle=8.12
```

**Enable auto-switching:**
```bash
# Add to .zshrc to enable automatic sdk env switching
sdk_auto_env=true
```

### 2. Automated Installation & Idempotency
**Problem:** Current `install` script only creates symlinks. Not idempotent, no error handling.

**Impact:** Cannot reliably setup a new machine or recover from partial failures.

**Solution:**
```bash
#!/usr/bin/env bash
# install.sh - Idempotent installation script

set -euo pipefail

# Check prerequisites
# Install Homebrew if missing
# Install Oh My Zsh if missing
# Install SDKMAN if missing
# Run Brewfile
# Create symlinks (check existence first)
# Configure pyenv, sdkman, goenv
# Install default Java/Scala/Go versions
# Set up Git config
# Verify installation
```

**Implementation:**
- [ ] Create comprehensive `install.sh` with error handling
- [ ] Add `bootstrap.sh` for first-time setup
- [ ] Create `update.sh` for keeping tools current
- [ ] Add `uninstall.sh` for safe removal

### 3. Secure Secrets Management - **SECURITY RISK**
**Problem:** 
- Hardcoded `LOCALSTACK_API_KEY` in `.zshrc` (committed to Git!)
- Artifactory credentials read from plain `.netrc`
- AWS credentials in environment

**Impact:** **CRITICAL SECURITY VULNERABILITY** - API keys exposed in version control.

**Solution:**
```bash
# Use encrypted secret management
brew "sops"           # Secrets management
brew "age"            # Encryption

# .zshrc approach
export LOCALSTACK_API_KEY=$(cat ~/.secrets/localstack | sops -d)
```

**Implementation:**
- [ ] **IMMEDIATE:** Remove `LOCALSTACK_API_KEY` from `.zshrc` and Git history
- [ ] Create `.secrets/` directory (add to `.gitignore`)
- [ ] Encrypt sensitive values using SOPS or 1Password CLI
- [ ] Document secret setup in README
- [ ] Add pre-commit hook to prevent committing secrets

### 4. Git Configuration Management
**Problem:** No `.gitconfig` in dotfiles. Git configuration not versioned.

**Solution:**
```ini
# home/.gitconfig
[user]
    name = Your Name
    email = your.email@example.com

[core]
    editor = vim
    excludesfile = ~/.gitignore_global
    autocrlf = input
    
[alias]
    co = checkout
    br = branch
    ci = commit
    st = status
    unstage = reset HEAD --
    last = log -1 HEAD
    visual = log --graph --decorate --oneline --all

[pull]
    rebase = true

[init]
    defaultBranch = main

[diff]
    tool = vimdiff

[credential]
    helper = osxkeychain
```

**Implementation:**
- [ ] Create `.gitconfig` with sensible defaults
- [ ] Create `.gitignore_global` for JVM/Python/Go artifacts
- [ ] Symlink both files in install script
- [ ] Configure delta or diff-so-fancy for better diffs

**Sample `.gitignore_global`:**
```gitignore
# macOS
.DS_Store
.AppleDouble
.LSOverride
._*

# IDE
.idea/
.vscode/
*.swp
*.swo
*~
.project
.classpath
.settings/

# Java/Scala/JVM
*.class
*.jar
*.war
*.ear
target/
*.log
.gradle/
build/
.sbt/
project/target/
project/project/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
dist/
.uv/

# Go
# Binaries
*.exe
*.exe~
*.dll
*.so
*.dylib
*.test

# Go build
vendor/
go.work
go.work.sum

# Output of the go coverage tool
*.out

# Dependency directories
/Godeps/

# Environment
.env
.env.local
*.secret
*.secrets

# Terraform
.terraform/
*.tfstate
*.tfstate.backup
.terraform.lock.hcl

# Docker
.dockerignore
docker-compose.override.yml
```

---

## 🟡 HIGH PRIORITY IMPROVEMENTS (Priority 2)

### 5. Docker & Kubernetes Enhancements

**Current Issues:**
- Basic Docker aliases only
- No Docker cleanup automation
- Limited K8s productivity tools
- No local K8s cluster setup

**Additions to Brewfile:**
```bash
brew "docker-compose"     # If not using Docker Desktop
brew "docker-credential-helper"
brew "kubectx"            # Fast context switching
brew "kubens"             # Fast namespace switching
brew "stern"              # Multi-pod log tailing
brew "helm"               # K8s package manager
brew "k9s"                # Already have it? Verify
brew "kind"               # Local K8s clusters
brew "skaffold"           # K8s development workflow
brew "kustomize"          # K8s config management
cask "lens"               # K8s IDE (alternative to k9s)
```

**Enhanced Aliases (.alias):**
```bash
# Docker - Enhanced
alias dclean="docker system prune -af --volumes"
alias dstop="docker stop \$(docker ps -aq)"
alias drm="docker rm \$(docker ps -aq)"
alias dlogs="docker logs -f"
alias dins="docker inspect"
alias dstats="docker stats --no-stream"

# Docker Compose
alias dcl="docker-compose logs -f"
alias dcr="docker-compose restart"
alias dce="docker-compose exec"

# Kubernetes - Enhanced
alias kgp="kubectl get pods"
alias kgd="kubectl get deployments"
alias kgs="kubectl get services"
alias kd="kubectl describe"
alias kdel="kubectl delete"
alias kl="kubectl logs -f"
alias kex="kubectl exec -it"
alias kpf="kubectl port-forward"
alias kctx="kubectx"
alias kns="kubens"
alias ktop="kubectl top"
alias kdrain="kubectl drain --ignore-daemonsets --delete-emptydir-data"

# Stern - multi-pod logs
alias klogs="stern"
```

**Implementation:**
- [ ] Install enhanced K8s tooling
- [ ] Create `scripts/k8s-utils.sh` with common functions
- [ ] Set up `kind` configuration for local testing
- [ ] Document K8s workflow in README

### 6. Python Environment - **WELL CONFIGURED**

**Current Status:**
- ✅ Pyenv configured and working
- ✅ Poetry installed and in use
- ✅ UV installed and in use
- ⚠️ Poetry path hardcoded (can be improved)

**Minor Improvements:**
```bash
# Brewfile additions
brew "pyenv-virtualenv"   # Virtual environment plugin
brew "pipx"               # Install Python CLI tools in isolation
brew "ruff"               # Fast Python linter/formatter (if not installed via uv)
```

**`.zshrc` enhancements:**
```bash
# Python - Cleaner setup
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# Set default Python version
export PYENV_VERSION="3.12"  # Or your preferred version

# Poetry & UV - unified path
export PATH="$HOME/.local/bin:$PATH"

# UV configuration
export UV_CACHE_DIR="$HOME/.cache/uv"
export UV_PYTHON_PREFERENCE="only-managed"  # Prefer pyenv versions
```

**Implementation:**
- [ ] Install pyenv-virtualenv for better venv support
- [ ] Install pipx for isolated CLI tools (black, ruff, etc.)
- [ ] Document Poetry + UV workflow in README
- [ ] Create `.python-version` files for projects
- [ ] Set up pre-commit hooks using UV

### 7. Golang Development Environment - **NEW**

**Problem:** No Golang tooling configured for microservices/cloud-native development.

**Impact:** Cannot manage multiple Go versions, missing essential Go development tools.

**Solution:**
```bash
# Brewfile additions
brew "go"                 # Latest Go version
brew "goenv"              # Go version management
brew "golangci-lint"      # Fast Go linters
brew "delve"              # Go debugger
brew "gopls"              # Go language server
```

**`.zshrc` additions:**
```bash
# Go Environment
export GOENV_ROOT="$HOME/.goenv"
export PATH="$GOENV_ROOT/bin:$PATH"
eval "$(goenv init -)"

# Go Path Configuration
export GOPATH="$HOME/go"
export GOBIN="$GOPATH/bin"
export PATH="$PATH:$GOBIN"

# Go Build Cache
export GOCACHE="$HOME/.cache/go-build"

# Go Module Proxy (optional - use Athens or default)
export GOPROXY="https://proxy.golang.org,direct"
export GOSUMDB="sum.golang.org"

# Enable Go modules (default in Go 1.16+)
export GO111MODULE="on"

# Go Private Repos (if needed)
# export GOPRIVATE="github.com/yourorg/*"
```

**Essential Go Aliases (.alias):**
```bash
# Golang
alias gob="go build"
alias gor="go run"
alias got="go test ./..."
alias gotv="go test -v ./..."
alias goc="go clean"
alias goi="go install"
alias gom="go mod"
alias gomt="go mod tidy"
alias gomv="go mod vendor"
alias gof="go fmt ./..."
alias goget="go get -u"
alias govet="go vet ./..."
alias golint="golangci-lint run"
alias gocover="go test -coverprofile=coverage.out ./... && go tool cover -html=coverage.out"

# Go Tools
alias air="air"           # Live reload (install via: go install github.com/air-verse/air@latest)
alias gotestsum="gotestsum"  # Better test output
```

**Project Structure for Go:**
```bash
# Create standard Go workspace
mkdir -p ~/go/{bin,pkg,src}

# Recommended tools to install via go install
go install github.com/air-verse/air@latest
go install gotest.tools/gotestsum@latest
go install github.com/google/wire/cmd/wire@latest
go install github.com/golang/mock/mockgen@latest
```

**`.editorconfig` for Go projects:**
```ini
# dotfiles/home/.editorconfig
root = true

[*.go]
indent_style = tab
indent_size = 4
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true
```

**Implementation:**
- [ ] Install goenv for version management
- [ ] Install Go 1.21+ and Go 1.22+ via goenv
- [ ] Set up GOPATH structure
- [ ] Install essential Go tools (air, gotestsum, wire)
- [ ] Configure golangci-lint
- [ ] Add Go to `.gitignore_global`
- [ ] Document Go workflow in README
- [ ] Create sample `go.mod` template

### 8. Shell Enhancements & Performance

**Current Issues:**
- Oh My Zsh with too many plugins (can slow startup)
- No shell performance monitoring
- Missing modern CLI tools

**Additions:**
```bash
# Brewfile
brew "zoxide"             # Smarter cd (z)
brew "fzf"                # Fuzzy finder
brew "bat"                # Better cat
brew "exa"                # Better ls (or lsd)
brew "ripgrep"            # Better grep
brew "fd"                 # Better find
brew "delta"              # Better git diff
brew "htop"               # Better top
brew "tldr"               # Simpler man pages
brew "thefuck"            # Correct previous command
```

**Implementation:**
- [ ] Benchmark zsh startup time: `time zsh -i -c exit`
- [ ] Add fzf integration for history search (Ctrl+R)
- [ ] Configure zoxide to replace cd
- [ ] Create aliases for bat/exa to replace cat/ls

---

## 🟢 MEDIUM PRIORITY IMPROVEMENTS (Priority 3)

### 9. IDE Configuration Files

**Problem:** No IDE settings versioned. IntelliJ IDEA path added but no configs.

**Solution:**
```
dotfiles/
├── idea/
│   ├── settings.zip          # Export from File > Manage IDE Settings
│   ├── keymaps/
│   └── templates/
│       ├── scala.xml
│       ├── java.xml
│       └── python.xml
├── vscode/
│   ├── settings.json
│   ├── keybindings.json
│   └── extensions.txt        # code --list-extensions > extensions.txt
```

**Implementation:**
- [ ] Export and version IntelliJ IDEA settings
- [ ] Create script to sync IDE settings
- [ ] Document IDE setup process
- [ ] Add VSCode settings if used

### 9. macOS System Configuration

**Problem:** No macOS defaults management. Manual system configuration.

**Solution:**
Create `macos/defaults.sh`:
```bash
#!/usr/bin/env bash

# macOS Defaults for Developer Workflow

# Finder
defaults write com.apple.finder AppleShowAllFiles -bool true
defaults write com.apple.finder ShowPathbar -bool true
defaults write com.apple.finder ShowStatusBar -bool true

# Dock
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock show-recents -bool false

# Keyboard
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 15

# Screenshots location
mkdir -p ~/Desktop/Screenshots
defaults write com.apple.screencapture location ~/Desktop/Screenshots

# Restart affected apps
killall Finder Dock SystemUIServer
```

**Implementation:**
- [ ] Create `macos/defaults.sh`
- [ ] Document current preferences
- [ ] Add to main install script
- [ ] Create restore script

### 10. Backup & Sync Strategy

**Problem:** No backup mechanism. No way to verify installation completeness.

**Solution:**
```bash
# scripts/backup.sh
#!/usr/bin/env bash
# Backup additional config files not in dotfiles

BACKUP_DIR="$HOME/dotfiles/backup/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup locations
cp -r ~/.aws "$BACKUP_DIR/" 2>/dev/null || true
cp -r ~/.kube "$BACKUP_DIR/" 2>/dev/null || true
cp ~/.netrc "$BACKUP_DIR/" 2>/dev/null || true
cp -r ~/.m2 "$BACKUP_DIR/" 2>/dev/null || true
cp -r ~/.sbt "$BACKUP_DIR/" 2>/dev/null || true
cp -r ~/.gradle "$BACKUP_DIR/" 2>/dev/null || true

# List of Homebrew packages
brew bundle dump --file="$BACKUP_DIR/Brewfile" --force

echo "Backup created at $BACKUP_DIR"
```

**Implementation:**
- [ ] Create backup script
- [ ] Add backup to gitignore
- [ ] Schedule weekly backups (cron or launchd)
- [ ] Document restore process

### 11. Build Tool Configurations

**Problem:** No Maven, Gradle, or SBT configurations versioned.

**Solution:**
```
dotfiles/
├── maven/
│   └── settings.xml          # ~/.m2/settings.xml
├── gradle/
│   └── gradle.properties     # ~/.gradle/gradle.properties
├── sbt/
│   ├── repositories          # ~/.sbt/repositories
│   └── plugins/
│       └── plugins.sbt
```

**Sample `.m2/settings.xml`:**
```xml
<settings>
  <localRepository>${user.home}/.m2/repository</localRepository>
  <mirrors>
    <mirror>
      <id>artifactory</id>
      <mirrorOf>*</mirrorOf>
      <url>YOUR_ARTIFACTORY_URL</url>
    </mirror>
  </mirrors>
  <servers>
    <server>
      <id>artifactory</id>
      <username>${env.ARTIFACTORY_USER}</username>
      <password>${env.ARTIFACTORY_PASSWORD}</password>
    </server>
  </servers>
</settings>
```

**Implementation:**
- [ ] Export Maven settings (sanitize credentials)
- [ ] Export Gradle settings
- [ ] Export SBT configuration
- [ ] Add symlinks to install script

### 12. Cleanup & Maintenance Scripts

**Problem:** TODO mentions cleanup scripts but none exist.

**Solution:**
```bash
# scripts/cleanup.sh
#!/usr/bin/env bash

echo "🧹 Cleaning up development caches..."

# Docker cleanup
echo "Cleaning Docker..."
docker system prune -af --volumes

# Homebrew cleanup
echo "Cleaning Homebrew..."
brew cleanup --prune=all

# Poetry cache
echo "Cleaning Poetry cache..."
poetry cache clear pypi --all

# UV cache
echo "Cleaning UV cache..."
uv cache clean

# Maven cache (SDKMAN managed)
echo "Cleaning Maven cache..."
rm -rf ~/.m2/repository/com/example/*  # Be specific to your org!

# Gradle cache (SDKMAN managed)
echo "Cleaning Gradle cache..."
rm -rf ~/.gradle/caches
rm -rf ~/.gradle/wrapper/dists

# SBT cache (SDKMAN managed)
echo "Cleaning SBT cache..."
find ~/.sbt -name "*.lock" -delete
rm -rf ~/.sbt/1.0/dependency

# Golang cache
echo "Cleaning Go cache..."
go clean -cache -modcache -testcache
rm -rf ~/go/pkg/mod/cache

# pyenv cache
echo "Cleaning pyenv cache..."
rm -rf ~/.pyenv/cache/*

# Terraform plugin cache
echo "Cleaning Terraform cache..."
rm -rf ~/.terraform.d/plugin-cache/*

# SDKMAN archives
echo "Cleaning SDKMAN archives..."
rm -rf ~/.sdkman/archives/*

# System caches
echo "Cleaning system caches..."
rm -rf ~/Library/Caches/Homebrew
rm -rf ~/Library/Caches/pip

# Calculate space saved
echo "✅ Cleanup complete!"
```

**Implementation:**
- [ ] Create comprehensive cleanup script
- [ ] Add dry-run mode to preview deletions
- [ ] Schedule monthly cleanup reminder
- [ ] Track cache sizes before/after

### 13. Unversioned Configuration Files Audit - **CRITICAL DISCOVERY**

**Problem:** Based on `.zshrc` analysis, multiple configuration directories and files exist outside dotfiles repository.

**Impact:** These configs are not backed up, not versioned, and will be lost on machine migration.

**Discovered Configurations:**

#### A. XDG Config Directory
```bash
# Currently set in .zshrc
export XDG_CONFIG_HOME="/Users/adas/.xdg/config/"
```

**Tools using XDG_CONFIG_HOME:**
- **k9s** - Kubernetes CLI manager (skin configuration)
- Potentially other tools following XDG Base Directory specification

**Action Required:**
```bash
# Add to dotfiles structure
dotfiles/
├── xdg/
│   └── config/
│       └── k9s/
│           ├── skin.yml          # K9s color scheme
│           ├── config.yml         # K9s settings
│           └── hotkeys.yml        # Custom keybindings
```

**Symlink in install script:**
```bash
mkdir -p ~/.xdg/config
ln -s ~/dotfiles/xdg/config/k9s ~/.xdg/config/k9s
```

#### B. AWS Configuration - **SENSITIVE**
```bash
# Referenced in .zshrc
~/.aws/
  ├── config              # AWS profiles and settings
  ├── credentials         # AWS access keys (DO NOT VERSION)
  └── ... (git-managed per .zshrc aliases)
```

**Current State:** You manage `~/.aws` with Git (see aliases: `awshome`, `awswork`)

**Recommendations:**
- [ ] Document the `~/.aws` Git workflow in README
- [ ] Add `~/.aws/credentials` to `.gitignore` (if not already)
- [ ] Create template `config` file without sensitive data
- [ ] Add to backup script (encrypted backup only)

#### C. Kubernetes Configuration - **SENSITIVE**
```bash
~/.kube/
  ├── config              # K8s cluster contexts (CONTAINS CERTIFICATES)
  ├── cache/
  └── http-cache/
```

**Security Risk:** Contains cluster certificates and tokens

**Action Required:**
```bash
# Create sanitized template
dotfiles/
├── kube/
│   ├── config.template     # Sanitized structure
│   └── README.md          # Setup instructions
```

**DO NOT version actual `~/.kube/config` - contains secrets!**

#### D. Terraform Configuration
```bash
# Already referenced in .zshrc
~/.terraform.d/
  ├── plugin-cache/       # Cached plugins (excluded from version control)
  ├── plugins/
  └── credentials.tfrc.json  # Terraform Cloud token (DO NOT VERSION)
```

**Action Required:**
```bash
dotfiles/
├── terraform/
│   ├── terraformrc         # Global terraform settings
│   └── README.md          # Document plugin cache setup
```

#### E. Build Tool Configurations (Already Noted in Section 11)
```bash
~/.m2/              # Maven (SDKMAN managed)
  └── settings.xml

~/.gradle/          # Gradle (SDKMAN managed)
  └── gradle.properties

~/.sbt/             # SBT (SDKMAN managed)
  ├── repositories
  └── plugins/
```

#### F. Additional Unversioned Configs

**Python Configs:**
```bash
~/.pyenv/
  └── version           # Global Python version (should version)

~/.config/pypoetry/   # Poetry config (if exists)
  └── config.toml
```

**Git Configs (Missing Entirely):**
```bash
~/.gitconfig          # NOT VERSIONED - Critical!
~/.gitignore_global   # NOT VERSIONED - Critical!
```

**Shell Configs (Partially Versioned):**
```bash
~/.netrc              # Artifactory credentials - SECURITY RISK
~/.zshenv             # Empty but should be used
~/.zshrc              # ✓ Already versioned
~/.alias              # ✓ Already versioned
```

**Other Potential Configs:**
```bash
~/.vimrc              # Vim configuration (if you use vim)
~/.tmux.conf          # Already mentioned in Brewfile (tmux installed)
~/.editorconfig       # Cross-editor configuration
~/.curlrc             # curl defaults
~/.wgetrc             # wget defaults
~/.docker/config.json # Docker registry auth (SENSITIVE)
```

**Application-Specific:**
```bash
~/Library/Application Support/pypoetry/  # Poetry venv location
/Applications/IntelliJ IDEA.app/         # IDE path in PATH
```

#### G. SDKMAN Configuration
```bash
~/.sdkman/
  ├── etc/
  │   └── config        # SDKMAN settings (should version preferences)
  ├── candidates/       # Installed versions (do not version)
  └── archives/         # Downloaded archives (do not version)
```

**Action Required:**
```bash
dotfiles/
├── sdkman/
│   └── config        # Version SDKMAN preferences
```

**Implementation Plan:**

**Phase 1: Critical Security (Immediate)**
- [ ] Audit `~/.netrc` permissions (should be 600)
- [ ] Move `.netrc` to encrypted secrets storage
- [ ] Verify `~/.kube/config` is not in any Git repo
- [ ] Verify `~/.aws/credentials` is not in any Git repo
- [ ] Check `~/.docker/config.json` for registry credentials

**Phase 2: Essential Configs (Week 1)**
- [ ] Create `.gitconfig` and `.gitignore_global` (Priority #1)
- [ ] Export k9s configuration from `~/.xdg/config/k9s/`
- [ ] Create SDKMAN config template
- [ ] Document AWS/Kube config workflows
- [ ] Create `.editorconfig` for consistent formatting

**Phase 3: Build Tools (Week 2)**
- [ ] Export Maven `settings.xml` (sanitize credentials)
- [ ] Export Gradle `gradle.properties`
- [ ] Export SBT configurations
- [ ] Create Poetry `config.toml` if customized

**Phase 4: Shell Enhancements (Week 2)**
- [ ] Create `.zshenv` for environment variables
- [ ] Create `.vimrc` if using vim
- [ ] Create `.tmux.conf` for tmux configuration
- [ ] Create `.curlrc` and `.wgetrc` if needed

**Phase 5: Documentation (Week 3)**
- [ ] Document all unversioned configs in README
- [ ] Create migration guide
- [ ] Document secret management workflow
- [ ] Create config audit script

**Recommended Dotfiles Structure (Complete):**
```bash
dotfiles/
├── README.md
├── TODO.md
├── improvement.md
├── install.sh              # NEW: Idempotent installer
├── backup.sh               # NEW: Backup script
├── cleanup.sh              # NEW: Cache cleanup
├── validate.sh             # NEW: Installation validator
│
├── brew/
│   └── Brewfile
│
├── home/                   # Existing
│   ├── .zshrc
│   ├── .zshenv            # NEW: Environment variables
│   ├── .alias
│   ├── .gitconfig         # NEW: Git configuration
│   ├── .gitignore_global  # NEW: Global Git ignores
│   ├── .editorconfig      # NEW: Editor settings
│   ├── .vimrc             # NEW: Vim config (optional)
│   ├── .tmux.conf         # NEW: Tmux config (optional)
│   └── .ssh/
│       └── config
│
├── xdg/                    # NEW: XDG configs
│   └── config/
│       └── k9s/
│           ├── skin.yml
│           ├── config.yml
│           └── hotkeys.yml
│
├── sdkman/                 # NEW: SDKMAN config
│   └── config
│
├── maven/                  # NEW: Build tools
│   └── settings.xml
│
├── gradle/                 # NEW
│   └── gradle.properties
│
├── sbt/                    # NEW
│   ├── repositories
│   └── plugins/
│       └── plugins.sbt
│
├── terraform/              # NEW
│   └── terraformrc
│
├── kube/                   # NEW: Templates only
│   ├── config.template
│   └── README.md
│
├── aws/                    # NEW: Templates only
│   ├── config.template
│   └── README.md
│
├── python/                 # NEW
│   └── poetry/
│       └── config.toml
│
├── golang/                 # NEW
│   └── .editorconfig
│
├── scripts/                # Existing
│   ├── kube
│   ├── oh-my-zsh/
│   ├── k8s-utils.sh       # NEW
│   └── backup.sh          # NEW
│
├── macos/                  # NEW
│   └── defaults.sh
│
├── idea/                   # NEW: IDE settings
│   ├── settings.zip
│   └── templates/
│
├── vscode/                 # NEW
│   ├── settings.json
│   └── extensions.txt
│
├── itermcolors/           # Existing
│
└── target/                # Existing
```

**Security Checklist for Configs:**
```bash
# Files that MUST NOT be versioned (add to .gitignore)
**/*credentials*
**/*secrets*
**/.netrc
~/.kube/config
~/.aws/credentials
~/.docker/config.json
~/.terraform.d/credentials.tfrc.json
**/*.pem
**/*.key
**/id_rsa*
**/*.p12

# Files with permissions checks
chmod 600 ~/.netrc
chmod 600 ~/.ssh/config
chmod 600 ~/.kube/config
chmod 600 ~/.aws/credentials
```

---

## 🔵 NICE TO HAVE IMPROVEMENTS (Priority 4)

### 14. Development Environment Documentation

**Enhanced README Structure:**
```markdown
# Dotfiles

## Quick Start
## Prerequisites
## Installation
## Daily Workflow
## Troubleshooting
## Tool Reference
  - JVM (Java/Scala)
  - Python
  - Docker/Kubernetes
  - Cloud (AWS)
  - Build Tools
## Customization Guide
## FAQ
```

### 15. Testing & Validation

**Create `tests/validate.sh`:**
```bash
#!/usr/bin/env bash
# Validate dotfiles installation

echo "🔍 Validating installation..."

# Check symlinks
test -L ~/.zshrc || echo "❌ .zshrc not linked"
test -L ~/.ssh/config || echo "❌ SSH config not linked"
test -L ~/.gitconfig || echo "❌ .gitconfig not linked"

# Check tools
command -v pyenv >/dev/null || echo "❌ pyenv not found"
command -v sdk >/dev/null || echo "❌ SDKMAN not found"
command -v goenv >/dev/null || echo "❌ goenv not found"
command -v docker >/dev/null || echo "❌ docker not found"
command -v kubectl >/dev/null || echo "❌ kubectl not found"

# Check Java versions via SDKMAN
sdk list java | grep -q "17.0" || echo "⚠️ Java 17 not installed via SDKMAN"

# Check config files
test -f ~/.gitconfig || echo "❌ .gitconfig missing"
test -f ~/.gitignore_global || echo "❌ .gitignore_global missing"
test -d ~/.xdg/config || echo "⚠️ XDG_CONFIG_HOME not set up"

echo "✅ Validation complete"
```

### 16. Containerized Development Environment

**Create `Dockerfile` for reproducible environments:**
```dockerfile
# For testing or sharing development environment
FROM ubuntu:22.04

# Install dotfiles
RUN git clone https://github.com/yourusername/dotfiles /root/dotfiles
RUN cd /root/dotfiles && ./install.sh

CMD ["zsh"]
```

### 17. Brewfile Organization

**Split into categories:**
```
brew/
├── Brewfile              # All tools (current)
├── Brewfile.essential    # Core tools only
├── Brewfile.java         # JVM tooling
├── Brewfile.python       # Python tooling
├── Brewfile.cloud        # AWS, K8s, Docker
├── Brewfile.optional     # Nice-to-haves
```

---

## 📋 IMMEDIATE ACTION PLAN

### Week 1: Security & Critical Setup
- [ ] **DAY 1:** Audit unversioned configs (Section 13 - run security checklist)
- [ ] **DAY 1:** Remove LOCALSTACK_API_KEY from Git history
- [ ] **DAY 1:** Move `.netrc` to encrypted secrets storage (SOPS)
- [ ] **DAY 2:** Create `.gitconfig` and `.gitignore_global` (CRITICAL)
- [ ] **DAY 2:** Export k9s config from `~/.xdg/config/k9s/`
- [ ] **DAY 3:** Configure SDKMAN with multiple Java/Scala versions
- [ ] **DAY 4:** Set up Golang environment with goenv
- [ ] **DAY 5:** Build idempotent `install.sh` with config symlinks

### Week 2: Development Tooling & Configs
- [ ] **DAY 1:** Export Maven, Gradle, SBT configurations
- [ ] **DAY 2:** Add enhanced K8s tools (kubectx, stern, etc.)
- [ ] **DAY 2:** Create `.editorconfig`, `.tmux.conf`, `.vimrc`
- [ ] **DAY 3:** Enhance Python setup (pipx, pyenv-virtualenv)
- [ ] **DAY 3:** Export Poetry config if customized
- [ ] **DAY 4:** Install and configure Go development tools
- [ ] **DAY 5:** Add modern CLI tools (fzf, ripgrep, bat, zoxide)

### Week 3: Maintenance, Documentation & Validation
- [ ] **DAY 1:** Create cleanup scripts (Docker, Maven, Go, SDKMAN cache)
- [ ] **DAY 2:** Set up backup strategy (include XDG configs)
- [ ] **DAY 3:** Export IDE configurations (IntelliJ, VSCode)
- [ ] **DAY 4:** Configure macOS defaults
- [ ] **DAY 5:** Create validation script and test full installation

---

## 🛡️ SECURITY CHECKLIST

- [ ] No API keys in version control (check LOCALSTACK_API_KEY)
- [ ] `.netrc` moved to encrypted secrets (SOPS or 1Password)
- [ ] `.netrc` file permissions set to 600
- [ ] SSH key permissions set to 600 (`chmod 600 ~/.ssh/*`)
- [ ] `~/.kube/config` not in any Git repository
- [ ] `~/.aws/credentials` not in any Git repository
- [ ] `~/.docker/config.json` checked for registry credentials
- [ ] Terraform credentials not versioned
- [ ] Pre-commit hooks prevent committing secrets
- [ ] `.gitignore` includes all credential patterns
- [ ] Regular security audit of exposed credentials
- [ ] Two-factor authentication on all services
- [ ] SSH keys rotated annually
- [ ] XDG configs audited for sensitive data

---

## 📊 SUCCESS METRICS

### Before vs After Comparison

| Metric                     | Before                  | Target                       |
| -------------------------- | ----------------------- | ---------------------------- |
| **Fresh Install Time**     | Unknown/Manual          | < 30 minutes automated       |
| **Tools Managed**          | ~40                     | 70+                          |
| **Version Managers**       | 2 (pyenv, sdkman)       | 4 (pyenv, sdkman, goenv)     |
| **Languages Supported**    | Python, Java/Scala      | Python, Java/Scala, Go       |
| **Versioned Config Files** | 4 (.zshrc, .alias, etc) | 20+ (all critical configs)   |
| **XDG Configs Versioned**  | 0                       | k9s, others as discovered    |
| **Build Tool Configs**     | 0                       | Maven, Gradle, SBT           |
| **Documented Workflows**   | Minimal                 | Comprehensive                |
| **IDE Configs Versioned**  | 0                       | All (IDEA, VSCode, GoLand)   |
| **Security Issues**        | 2+ exposed keys         | 0                            |
| **Cleanup Automation**     | Manual                  | Automated (6 ecosystems)     |
| **Backup Strategy**        | None                    | Weekly automated + encrypted |

---

## 🎯 RECOMMENDED TOOL ADDITIONS SUMMARY

### Essential (Add Immediately)
```ruby
# SDKMAN managed (not in Brewfile)
# Java 8, 11, 17, 21 - via: sdk install java
# Scala 2.12, 2.13, 3.x - via: sdk install scala
# Gradle, Maven, SBT - via: sdk install

# Golang
brew "goenv"              # Go version management
brew "golangci-lint"      # Go linters
brew "delve"              # Go debugger

# Security
brew "sops"
brew "age"

# Shell Enhancement
brew "fzf"
brew "zoxide"
brew "ripgrep"
brew "bat"
brew "exa"

# K8s
brew "kubectx"
brew "kubens"
brew "stern"
brew "helm"

# Python (complement existing setup)
brew "pyenv-virtualenv"   # Virtual environments
brew "pipx"               # Isolated tool installation

# Git
brew "delta"
brew "gh"                 # GitHub CLI
```

### Consider Adding
```ruby
brew "lazydocker"     # Docker TUI
brew "lazygit"        # Git TUI  
brew "tmux"           # Already have it - configure it
brew "neovim"         # Modern vim
brew "asdf"           # Universal version manager (alternative to multiple *env)
```

---

## 📚 LEARNING RESOURCES

### Version Management
- [SDKMAN Documentation](https://sdkman.io/)
- [SDKMAN Usage Guide](https://sdkman.io/usage)
- [goenv Documentation](https://github.com/go-nv/goenv)
- [pyenv Documentation](https://github.com/pyenv/pyenv)

### Python Tools
- [UV Documentation](https://docs.astral.sh/uv/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

### Golang
- [Effective Go](https://go.dev/doc/effective_go)
- [Go Project Layout](https://github.com/golang-standards/project-layout)
- [golangci-lint](https://golangci-lint.run/)

### General Dotfiles
- [Awesome Dotfiles](https://github.com/webpro/awesome-dotfiles)
- [Mathias Bynens' dotfiles](https://github.com/mathiasbynens/dotfiles)
- [Thoughtbot dotfiles](https://github.com/thoughtbot/dotfiles)

### Security
- [SOPS Documentation](https://github.com/mozilla/sops)
- [1Password CLI](https://developer.1password.com/docs/cli)

---

## 🚀 QUICK START COMMANDS

### SDKMAN (Java/Scala)
```bash
# List available versions
sdk list java
sdk list scala

# Install specific versions
sdk install java 17.0.13-tem
sdk install scala 2.13.15

# Switch versions
sdk use java 17.0.13-tem
sdk default java 17.0.13-tem

# Project-specific: create .sdkmanrc in project root
echo "java=17.0.13-tem" > .sdkmanrc
echo "scala=2.13.15" >> .sdkmanrc
```

### Python (Poetry + UV)
```bash
# Create new project with Poetry
poetry new myproject
cd myproject

# Or init in existing directory
poetry init

# Add dependencies with UV (faster)
uv pip install django

# Or use Poetry
poetry add django

# Install project dependencies
poetry install

# Run commands in virtual environment
poetry run python script.py
poetry shell  # Activate venv
```

### Golang
```bash
# Install Go versions with goenv
goenv install 1.22.0
goenv global 1.22.0

# Create new Go module
mkdir myapp && cd myapp
go mod init github.com/username/myapp

# Install dependencies
go get github.com/gin-gonic/gin

# Build & run
go build
go run main.go

# Test
go test ./...

# Format & lint
go fmt ./...
golangci-lint run
```

### Multi-Language Project Example
```bash
# Project with Java backend, Python scripts, Go services

# 1. Set up Java/Scala (SDKMAN)
cd backend/
echo "java=17.0.13-tem" > .sdkmanrc
echo "scala=2.13.15" >> .sdkmanrc
sdk env install  # Auto-install versions

# 2. Set up Python (Poetry)
cd ../data-pipeline/
echo "3.11" > .python-version
poetry install

# 3. Set up Go (goenv)
cd ../api-gateway/
echo "1.22.0" > .go-version
go mod download
```

---

## 🔄 MAINTENANCE SCHEDULE

- **Daily:** Source new aliases/functions
- **Weekly:** Review TODO.md, update Brewfile, run `sdk update`
- **Monthly:** Run cleanup script, update tools (`sdk upgrade`, `brew upgrade`, `go install -u`)
- **Quarterly:** Review and prune unused tools, update Go modules
- **Annually:** Fresh install test, security audit, rotate SSH keys

---

## CONCLUSION

Your dotfiles foundation is solid for Python/AWS/K8s work but **critical configuration audit reveals 15+ unversioned config files** that need immediate attention alongside **JVM tooling optimization**, **Golang support**, and **security hardening**.

### What You Already Have ✅
- SDKMAN installed and initialized
- Poetry and UV configured for Python
- Comprehensive AWS/K8s tooling (with k9s using XDG config)
- Good Docker workflow
- Basic shell configuration

### Critical Discoveries from Config Audit 🔍
- **XDG Config:** `~/.xdg/config/k9s/` contains unversioned k9s settings
- **Git Configs:** `.gitconfig` and `.gitignore_global` completely missing
- **Build Tools:** Maven, Gradle, SBT configs not versioned
- **Security Risks:** `.netrc` with plaintext credentials, LOCALSTACK_API_KEY exposed
- **SDKMAN Config:** Preferences not versioned
- **Shell:** `.zshenv` empty but should contain environment variables

### What's Needed 🔧

**Immediate (Week 1):**
1. **Security Audit:** Fix exposed secrets (.netrc, LOCALSTACK_API_KEY)
2. **Git Configs:** Create and version .gitconfig, .gitignore_global (CRITICAL)
3. **XDG Configs:** Export k9s configurations
4. **SDKMAN:** Install multiple Java/Scala versions, configure project defaults

**Short-term (Week 2-3):**
5. **Golang:** Complete setup with goenv, tools, and aliases
6. **Build Tools:** Version Maven/Gradle/SBT configurations
7. **Shell:** Populate .zshenv, create .editorconfig, .tmux.conf
8. **Automation:** Idempotent install script with all config symlinks

The improvements above will create a:

✅ **Production-grade dotfiles setup**  
✅ **Multi-language development environment** (Java, Scala, Python, Go)  
✅ **20+ versioned configuration files** (vs current 4)  
✅ **Reproducible across machines** in < 30 minutes  
✅ **Secure secret management** (zero exposed credentials)  
✅ **Comprehensive automation** (install, backup, cleanup, validation)  
✅ **Well-documented workflow** with troubleshooting guides

Start with the **Week 1 Critical Actions** focusing on:
1. **Config Audit** - Identify and secure all unversioned configs (Section 13)
2. **Security fixes** - Remove LOCALSTACK_API_KEY, encrypt .netrc
3. **Git setup** - Create .gitconfig and .gitignore_global
4. **SDKMAN** - Multi-version Java/Scala setup with .sdkmanrc
5. **XDG export** - Version k9s and other XDG-based configs

**Estimated Implementation Time:** 3-4 weeks (1-2 hours daily)  
**Maintenance Overhead:** ~1 hour monthly once established
