SHELL := /bin/bash

.PHONY: update build-impeccable install-codex install-claude-code install-opencode init-initiative check-copy init-i18n

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

check-copy:
	./scripts/check-no-hardcoded-copy.sh

init-i18n:
	@if [ -z "$(STACK)" ]; then echo "Usage: make init-i18n STACK=<flutter|android|web|ios|generic> [TARGET_DIR=.] [SOURCE_LOCALE=en] [TARGET_LOCALES='es,fr']"; exit 1; fi
	./scripts/init-i18n-foundation.sh --stack "$(STACK)" --target-dir "$(if $(TARGET_DIR),$(TARGET_DIR),.)" --source-locale "$(if $(SOURCE_LOCALE),$(SOURCE_LOCALE),en)" $(if $(TARGET_LOCALES),--target-locales "$(TARGET_LOCALES)",)
