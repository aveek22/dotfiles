#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$dir/../lib.sh"

HOME="/tmp/fake-home-$$"

result="$(uname() { echo Darwin; }; export -f uname; vscode_user_dir)"
expected="/tmp/fake-home-$$/Library/Application Support/Code/User"
if [ "$result" != "$expected" ]; then
    echo "FAIL: macOS path resolution wrong: got '$result' expected '$expected'"
    exit 1
fi

result="$(uname() { echo Linux; }; export -f uname; vscode_user_dir)"
expected="/tmp/fake-home-$$/.config/Code/User"
if [ "$result" != "$expected" ]; then
    echo "FAIL: Linux path resolution wrong: got '$result' expected '$expected'"
    exit 1
fi

if uname() { echo Plan9; }; export -f uname; vscode_user_dir >/dev/null 2>&1; then
    echo "FAIL: unsupported OS should have returned non-zero"
    exit 1
fi

echo "PASS: test_lib.sh"
