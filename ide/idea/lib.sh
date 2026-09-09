#!/usr/bin/env bash
# Shared helpers for the idea export/apply scripts. Sourced, not executed.

# The curated allowlist of options/*.xml files considered safe and portable
# to sync (see docs/superpowers/specs/2026-09-09-idea-ide-config-design.md
# for the excluded-file rationale). Single source of truth for both export
# (bootstrap) and apply (symlink) — add to this list, never hardcode a
# second copy elsewhere.
IDEA_OPTION_FILES=(
    colors.scheme.xml console-font.xml editor-font.xml terminal-font.xml
    ui.lnf.xml find.xml findUsages.xml diff.xml debugger.xml
    filetypes.xml overrideFileTypes.xml csvSettings.xml git_toolbox_blame.xml
    javaRuleManager.xml scala.xml scala_config.xml spellchecker-dictionary.xml
    textmate.xml advancedSettings.xml avro_idl.xml
)

# The whole-directory areas where everything inside is inherently a
# deliberate customization — symlinked as directories, not curated
# file-by-file (see design spec, "Sync mechanism: two-tier symlinks").
IDEA_WHOLE_DIRS=(keymaps colors templates fileTemplates codestyles)

# Prints the absolute path to the newest IntelliJIdea<version> config
# directory under ~/Library/Application Support/JetBrains/. Exits non-zero
# if none exists yet (fresh machine, IDE never launched).
idea_config_dir() {
    local found
    found="$(ls -d "$HOME/Library/Application Support/JetBrains/IntelliJIdea"* 2>/dev/null | sort -V | tail -1)"
    if [ -z "$found" ]; then
        echo "idea: no IntelliJIdea config directory found under ~/Library/Application Support/JetBrains/" >&2
        echo "  Launch IntelliJ IDEA at least once so it creates its config directory, then re-run." >&2
        return 1
    fi
    echo "$found"
}
