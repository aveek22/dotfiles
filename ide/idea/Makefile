# Convenience wrappers around ./export and ./apply. Run from ide/idea/.
# `make` with no target prints this help rather than mutating anything.
.PHONY: help apply export test

help:
	@echo "make apply   - symlink keymaps/colors/templates/fileTemplates/codestyles dirs + curated options/*.xml"
	@echo "make export  - snapshot current settings/keymap/colors/etc + plugins.txt (reference only) into this dir"
	@echo "make test    - run the test suite in tests/"

apply:
	./apply

export:
	./export

test:
	@for t in tests/test_*.sh; do \
		echo "### $$t ###"; \
		bash "$$t" || exit 1; \
	done
