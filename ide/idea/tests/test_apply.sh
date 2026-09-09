#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/fixtures.sh"

real_repo_dir="$dir/.."
setup_fake_idea_env
trap teardown_fake_idea_env EXIT
stage_fake_repo_dir "$real_repo_dir"

# minimal repo content to apply: one whole-dir with content, one curated
# options file
mkdir -p "$FAKE_REPO_DIR/keymaps" "$FAKE_REPO_DIR/colors" "$FAKE_REPO_DIR/templates" "$FAKE_REPO_DIR/fileTemplates" "$FAKE_REPO_DIR/codestyles" "$FAKE_REPO_DIR/options"
echo '<keymap name="Mine" />' > "$FAKE_REPO_DIR/keymaps/Mine.xml"
echo '<application><component name="Test" /></application>' > "$FAKE_REPO_DIR/options/find.xml"

# pre-existing real (non-symlinked) keymaps/ dir and find.xml — must be
# backed up, not destroyed
mkdir -p "$FAKE_CONFIG_DIR/keymaps"
echo '<keymap name="Old" />' > "$FAKE_CONFIG_DIR/keymaps/Old.xml"
echo '<application><component name="Old" /></application>' > "$FAKE_CONFIG_DIR/options/find.xml"

"$FAKE_REPO_DIR/apply"

# 1. keymaps/ is now a symlink pointing at the repo copy
if [ "$(readlink "$FAKE_CONFIG_DIR/keymaps")" != "$FAKE_REPO_DIR/keymaps" ]; then
    echo "FAIL: keymaps/ was not symlinked to the repo copy"
    exit 1
fi

# 2. the pre-existing real keymaps/ dir was backed up before symlinking
backup_dir="$(find "$FAKE_CONFIG_DIR" -maxdepth 1 -name 'keymaps.bak-*' | head -1)"
if [ -z "$backup_dir" ] || [ ! -f "$backup_dir/Old.xml" ]; then
    echo "FAIL: pre-existing keymaps/ was not backed up before symlinking"
    exit 1
fi

# 3. find.xml is now a symlink pointing at the repo copy
if [ "$(readlink "$FAKE_CONFIG_DIR/options/find.xml")" != "$FAKE_REPO_DIR/options/find.xml" ]; then
    echo "FAIL: options/find.xml was not symlinked to the repo copy"
    exit 1
fi

# 4. the pre-existing real find.xml was backed up before symlinking
backup_file="$(find "$FAKE_CONFIG_DIR/options" -maxdepth 1 -name 'find.xml.bak-*' | head -1)"
if [ -z "$backup_file" ] || ! grep -q 'name="Old"' "$backup_file"; then
    echo "FAIL: pre-existing options/find.xml was not backed up before symlinking"
    exit 1
fi

# 5. other whole-dirs (colors, templates, fileTemplates, codestyles) also symlinked
for name in colors templates fileTemplates codestyles; do
    if [ "$(readlink "$FAKE_CONFIG_DIR/$name")" != "$FAKE_REPO_DIR/$name" ]; then
        echo "FAIL: $name/ was not symlinked"
        exit 1
    fi
done

# 6. running apply again is a no-op (doesn't re-backup an already-correct symlink)
before_backups="$(find "$FAKE_CONFIG_DIR" -maxdepth 1 -name 'keymaps.bak-*' | wc -l | tr -d ' ')"
"$FAKE_REPO_DIR/apply"
after_backups="$(find "$FAKE_CONFIG_DIR" -maxdepth 1 -name 'keymaps.bak-*' | wc -l | tr -d ' ')"
if [ "$before_backups" != "$after_backups" ]; then
    echo "FAIL: second apply run created an unnecessary backup of an already-correct symlink"
    exit 1
fi

# 7. a missing individual repo file (e.g. debugger.xml not committed yet)
# must not abort the whole run — other curated files still get linked.
# Uses a second fresh env so this doesn't interact with the state above.
teardown_fake_idea_env
setup_fake_idea_env
stage_fake_repo_dir "$real_repo_dir"
mkdir -p "$FAKE_REPO_DIR/keymaps" "$FAKE_REPO_DIR/colors" "$FAKE_REPO_DIR/templates" "$FAKE_REPO_DIR/fileTemplates" "$FAKE_REPO_DIR/codestyles" "$FAKE_REPO_DIR/options"
echo '<application><component name="Test" /></application>' > "$FAKE_REPO_DIR/options/find.xml"
# deliberately no debugger.xml in the fake repo dir

"$FAKE_REPO_DIR/apply"

if [ "$(readlink "$FAKE_CONFIG_DIR/options/find.xml")" != "$FAKE_REPO_DIR/options/find.xml" ]; then
    echo "FAIL: a missing debugger.xml aborted the run before find.xml was linked"
    exit 1
fi

# 8. apply never touches plugins/ — no install/uninstall/reconcile side
# effects (locks in the "document only" plugin decision)
mkdir -p "$FAKE_CONFIG_DIR/plugins/some-plugin"
plugins_before="$(find "$FAKE_CONFIG_DIR/plugins" -mindepth 1 -maxdepth 1 | sort)"
"$FAKE_REPO_DIR/apply"
plugins_after="$(find "$FAKE_CONFIG_DIR/plugins" -mindepth 1 -maxdepth 1 | sort)"
if [ "$plugins_before" != "$plugins_after" ]; then
    echo "FAIL: apply modified $FAKE_CONFIG_DIR/plugins — it must never touch plugins"
    exit 1
fi

echo "PASS: test_apply.sh"
