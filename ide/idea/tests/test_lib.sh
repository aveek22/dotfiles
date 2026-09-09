#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/fixtures.sh"

real_repo_dir="$dir/.."
setup_fake_idea_env
trap teardown_fake_idea_env EXIT
source "$real_repo_dir/lib.sh"

# 1. resolves the newest version dir when multiple exist
result="$(idea_config_dir)"
if [ "$result" != "$FAKE_CONFIG_DIR" ]; then
    echo "FAIL: expected newest config dir '$FAKE_CONFIG_DIR', got '$result'"
    exit 1
fi

# 2. errors clearly when no config dir exists at all
teardown_fake_idea_env
tmp="$(mktemp -d)"
export TMP_TEST_DIR="$tmp"
export HOME="$tmp/home"
mkdir -p "$HOME"
if idea_config_dir >/dev/null 2>&1; then
    echo "FAIL: idea_config_dir should have failed with no config dir present"
    exit 1
fi
rm -rf "$tmp"

echo "PASS: test_lib.sh"
