#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/fixtures.sh"

real_repo_dir="$dir/.."
setup_fake_vscode_env
trap teardown_fake_vscode_env EXIT
stage_fake_repo_dir "$real_repo_dir"

# minimal repo content to apply
echo '{"theme": "test"}' > "$FAKE_REPO_DIR/settings.json"
echo '[]' > "$FAKE_REPO_DIR/keybindings.json"
mkdir -p "$FAKE_REPO_DIR/snippets"
printf 'wanted.ext\n' > "$FAKE_REPO_DIR/extensions.txt"

# pre-existing real (non-symlinked) keybindings.json — must be backed up, not destroyed
echo '{"old": true}' > "$FAKE_USER_DIR/keybindings.json"

# fake "currently installed": has b.ext (should be pruned), missing wanted.ext (should be installed)
printf 'b.ext\n' > "$FAKE_EXTENSIONS_FILE"

"$FAKE_REPO_DIR/apply"

# 1. settings.json is now a symlink pointing at the repo copy
if [ "$(readlink "$FAKE_USER_DIR/settings.json")" != "$FAKE_REPO_DIR/settings.json" ]; then
    echo "FAIL: settings.json was not symlinked to the repo copy"
    exit 1
fi

# 2. pre-existing real keybindings.json was backed up before symlinking
if [ "$(readlink "$FAKE_USER_DIR/keybindings.json")" != "$FAKE_REPO_DIR/keybindings.json" ]; then
    echo "FAIL: keybindings.json was not symlinked"
    exit 1
fi
backup_file="$(find "$FAKE_USER_DIR" -maxdepth 1 -name 'keybindings.json.bak-*' | head -1)"
if [ -z "$backup_file" ] || ! grep -q '"old": true' "$backup_file"; then
    echo "FAIL: pre-existing keybindings.json was not backed up before symlinking"
    exit 1
fi

# 3. snippets/ symlinked too
if [ "$(readlink "$FAKE_USER_DIR/snippets")" != "$FAKE_REPO_DIR/snippets" ]; then
    echo "FAIL: snippets/ was not symlinked"
    exit 1
fi

# 4. extensions reconciled: wanted.ext installed, b.ext pruned
final="$(sort "$FAKE_EXTENSIONS_FILE")"
if [ "$final" != "wanted.ext" ]; then
    echo "FAIL: expected only wanted.ext installed after apply, got: $final"
    exit 1
fi

# 5. running apply again is a no-op on settings.json (doesn't re-backup an already-correct symlink)
before_backups="$(find "$FAKE_USER_DIR" -maxdepth 1 -name 'settings.json.bak-*' | wc -l | tr -d ' ')"
"$FAKE_REPO_DIR/apply"
after_backups="$(find "$FAKE_USER_DIR" -maxdepth 1 -name 'settings.json.bak-*' | wc -l | tr -d ' ')"
if [ "$before_backups" != "$after_backups" ]; then
    echo "FAIL: second apply run created an unnecessary backup of an already-correct symlink"
    exit 1
fi

echo "PASS: test_apply.sh"
