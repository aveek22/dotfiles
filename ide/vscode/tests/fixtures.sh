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
    for f in export apply lib.sh; do
        if [ -f "$real_repo_dir/$f" ]; then
            cp "$real_repo_dir/$f" "$staged/"
            chmod +x "$staged/$f" 2>/dev/null || true
        fi
    done
    export FAKE_REPO_DIR="$staged"
}
