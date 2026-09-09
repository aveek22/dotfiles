#!/usr/bin/env bash
# Shared test fixture helpers for idea export/apply tests. Sourced, not
# executed.

# Creates a temp fake $HOME with a fake IntelliJIdea2026.2 config directory
# (plus an older IntelliJIdea2026.1 to exercise newest-wins resolution).
# Exported: FAKE_HOME, FAKE_CONFIG_DIR, FAKE_OLD_CONFIG_DIR, TMP_TEST_DIR.
# Overrides HOME.
setup_fake_idea_env() {
    local tmp
    tmp="$(mktemp -d)"
    export TMP_TEST_DIR="$tmp"
    export FAKE_HOME="$tmp/home"
    export FAKE_OLD_CONFIG_DIR="$FAKE_HOME/Library/Application Support/JetBrains/IntelliJIdea2026.1"
    export FAKE_CONFIG_DIR="$FAKE_HOME/Library/Application Support/JetBrains/IntelliJIdea2026.2"
    mkdir -p "$FAKE_OLD_CONFIG_DIR/options" "$FAKE_CONFIG_DIR/options" "$FAKE_CONFIG_DIR/plugins"
    export HOME="$FAKE_HOME"
}

teardown_fake_idea_env() {
    rm -rf "$TMP_TEST_DIR"
}

# Copies the real export/apply/lib.sh into a scratch dir so tests never
# write into the real ide/idea/ files. Sets FAKE_REPO_DIR.
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
