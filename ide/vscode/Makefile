# Convenience wrappers around ./export and ./apply. Run from ide/vscode/.
# `make` with no target prints this help rather than mutating anything.
.PHONY: help apply export prune test

help:
	@echo "make apply   - symlink settings/keybindings/snippets, install+prune extensions"
	@echo "make export  - snapshot current settings/keybindings/snippets/extensions into this dir"
	@echo "make prune   - alias for apply (pruning is bundled into apply, not a separate step)"
	@echo "make test    - run the test suite in tests/"

apply:
	./apply

export:
	./export

# apply already reconciles extensions as install+prune in one pass — there's
# no standalone prune-only mode. This alias exists so `make prune` does the
# expected thing instead of erroring.
prune: apply

test:
	@for t in tests/test_*.sh; do \
		echo "### $$t ###"; \
		bash "$$t" || exit 1; \
	done
