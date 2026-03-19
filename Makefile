SHELL := /bin/bash

.PHONY: update build-impeccable install-codex install-claude-code install-opencode init-initiative

update:
	./scripts/update-upstreams.sh

build-impeccable:
	./scripts/build-impeccable-dist.sh

install-codex:
	./scripts/install-codex.sh

install-claude-code:
	./scripts/install-claude-code.sh

install-opencode:
	./scripts/install-opencode.sh

init-initiative:
	@if [ -z "$(INITIATIVE)" ]; then echo "Usage: make init-initiative INITIATIVE=my-product [TITLE='My Product']"; exit 1; fi
	./scripts/init-initiative.sh "$(INITIATIVE)" "$(TITLE)"
