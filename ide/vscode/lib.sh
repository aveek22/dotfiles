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
