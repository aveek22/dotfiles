#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/fixtures.sh"

real_repo_dir="$dir/.."
setup_fake_idea_env
trap teardown_fake_idea_env EXIT
stage_fake_repo_dir "$real_repo_dir"

# seed a live (non-symlinked) keymaps/ dir and find.xml to exercise the
# bootstrap path
mkdir -p "$FAKE_CONFIG_DIR/keymaps"
echo '<keymap name="Live" />' > "$FAKE_CONFIG_DIR/keymaps/Live.xml"
echo '<application><component name="Live" /></application>' > "$FAKE_CONFIG_DIR/options/find.xml"

# seed two fake installed plugins
mkdir -p "$FAKE_CONFIG_DIR/plugins/zzz-plugin" "$FAKE_CONFIG_DIR/plugins/aaa-plugin"

"$FAKE_REPO_DIR/export"

# 1. keymaps/ got bootstrapped from the live (non-symlinked) dir
if [ ! -f "$FAKE_REPO_DIR/keymaps/Live.xml" ]; then
    echo "FAIL: keymaps/ was not bootstrapped from the live directory"
    exit 1
fi

# 2. find.xml got bootstrapped from the live (non-symlinked) file
if ! grep -q 'name="Live"' "$FAKE_REPO_DIR/options/find.xml"; then
    echo "FAIL: options/find.xml was not bootstrapped from the live file"
    exit 1
fi

# 3. plugins.txt lists both fake plugins, sorted
expected=$'aaa-plugin\nzzz-plugin'
actual="$(cat "$FAKE_REPO_DIR/plugins.txt")"
if [ "$actual" != "$expected" ]; then
    echo "FAIL: plugins.txt does not match fake plugin dirs"
    echo "expected: $expected"
    echo "actual:   $actual"
    exit 1
fi

# 4. running export again does not clobber a manually-edited repo copy of a
# bootstrap-once file
echo '<keymap name="EditedByHand" />' > "$FAKE_REPO_DIR/keymaps/Live.xml"
"$FAKE_REPO_DIR/export"
if ! grep -q 'EditedByHand' "$FAKE_REPO_DIR/keymaps/Live.xml"; then
    echo "FAIL: second export run clobbered the manually-edited repo keymaps/Live.xml"
    exit 1
fi

# 5. plugins.txt IS regenerated unconditionally on every run, even if a
# plugin was added since the last export (it's a reference snapshot, not
# bootstrap-once)
mkdir -p "$FAKE_CONFIG_DIR/plugins/new-plugin"
"$FAKE_REPO_DIR/export"
if ! grep -qFx 'new-plugin' "$FAKE_REPO_DIR/plugins.txt"; then
    echo "FAIL: plugins.txt was not regenerated to include a newly installed plugin"
    exit 1
fi

echo "PASS: test_export.sh"
