SHELL := /bin/bash

.PHONY: update build-impeccable install-codex install-claude-code install-opencode init-initiative check-copy init-i18n show-command render-command save-command

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

show-command:
	@if [ -z "$(COMMAND)" ]; then echo "Usage: make show-command COMMAND=<command-name>"; exit 1; fi
	./scripts/show-command-template.sh "$(COMMAND)"

render-command:
	@if [ -z "$(COMMAND)" ]; then echo "Usage: make render-command COMMAND=<command-name> [GOAL='...'] [REPOSITORY='...'] [STACK='...']"; exit 1; fi
	./scripts/render-command.sh --command "$(COMMAND)" $(if $(GOAL),--goal "$(GOAL)",) $(if $(REPOSITORY),--repository "$(REPOSITORY)",) $(if $(PLATFORM),--platform "$(PLATFORM)",) $(if $(STACK),--stack "$(STACK)",) $(if $(MARKETS),--markets "$(MARKETS)",) $(if $(LOCALES),--locales "$(LOCALES)",) $(if $(CONSTRAINTS),--constraints "$(CONSTRAINTS)",) $(if $(SOURCE_LOCALE),--source-locale "$(SOURCE_LOCALE)",) $(if $(TARGET_LOCALES),--target-locales "$(TARGET_LOCALES)",) $(if $(CAPABILITY_HINT),--capability-hint "$(CAPABILITY_HINT)",) $(if $(TRANSLATION_CONSTRAINTS),--translation-constraints "$(TRANSLATION_CONSTRAINTS)",)

save-command:
	@if [ -z "$(COMMAND)" ]; then echo "Usage: make save-command COMMAND=<command-name> [GOAL='...'] [TITLE='...']"; exit 1; fi
	./scripts/save-command-brief.sh --command "$(COMMAND)" $(if $(TITLE),--title "$(TITLE)",) $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(GOAL),--goal "$(GOAL)",) $(if $(REPOSITORY),--repository "$(REPOSITORY)",) $(if $(PLATFORM),--platform "$(PLATFORM)",) $(if $(STACK),--stack "$(STACK)",) $(if $(MARKETS),--markets "$(MARKETS)",) $(if $(LOCALES),--locales "$(LOCALES)",) $(if $(CONSTRAINTS),--constraints "$(CONSTRAINTS)",) $(if $(SOURCE_LOCALE),--source-locale "$(SOURCE_LOCALE)",) $(if $(TARGET_LOCALES),--target-locales "$(TARGET_LOCALES)",) $(if $(CAPABILITY_HINT),--capability-hint "$(CAPABILITY_HINT)",) $(if $(TRANSLATION_CONSTRAINTS),--translation-constraints "$(TRANSLATION_CONSTRAINTS)",)
