#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/fixtures.sh"

real_repo_dir="$dir/.."
setup_fake_vscode_env
trap teardown_fake_vscode_env EXIT
stage_fake_repo_dir "$real_repo_dir"

# seed a live (non-symlinked) settings.json to exercise the bootstrap path
echo '{"foo": "bar"}' > "$FAKE_USER_DIR/settings.json"

"$FAKE_REPO_DIR/export"

# 1. extensions.txt reflects the fake install list, sorted
expected_sorted="$(sort "$FAKE_EXTENSIONS_FILE")"
actual="$(cat "$FAKE_REPO_DIR/extensions.txt")"
if [ "$actual" != "$expected_sorted" ]; then
    echo "FAIL: extensions.txt does not match fake install list"
    echo "expected: $expected_sorted"
    echo "actual:   $actual"
    exit 1
fi

# 2. settings.json got bootstrapped from the live (non-symlinked) file
if ! grep -q '"foo": "bar"' "$FAKE_REPO_DIR/settings.json"; then
    echo "FAIL: settings.json was not bootstrapped from the live file"
    exit 1
fi

# 3. running export again does not clobber a manually-edited repo copy
echo '{"foo": "edited-by-hand"}' > "$FAKE_REPO_DIR/settings.json"
"$FAKE_REPO_DIR/export"
if ! grep -q 'edited-by-hand' "$FAKE_REPO_DIR/settings.json"; then
    echo "FAIL: second export run clobbered the manually-edited repo settings.json"
    exit 1
fi

echo "PASS: test_export.sh"
