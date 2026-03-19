SHELL := /bin/bash

.PHONY: update build-impeccable install-codex install-claude-code install-opencode

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

