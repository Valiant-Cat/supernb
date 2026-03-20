SHELL := /bin/bash

.PHONY: update update-upstreams build-impeccable install-codex install-claude-code install-opencode verify-installs verify-claude-loop init-initiative run-initiative execute-next apply-execution import-execution record-result advance-phase certify-phase upgrade-artifacts migrate-legacy clean-initiative prompt-bootstrap prompt-closeout test check-copy init-i18n show-command render-command save-command bootstrap quickstart

update:
	./scripts/update-supernb.sh

update-upstreams:
	./scripts/update-upstreams.sh

bootstrap:
	./scripts/bootstrap-supernb.sh $(if $(HARNESS),--harness "$(HARNESS)",) $(if $(PROJECT_DIR),--project-dir "$(PROJECT_DIR)",)

quickstart:
	@echo "Open docs/quickstart.md"

build-impeccable:
	./scripts/build-impeccable-dist.sh

install-codex:
	./scripts/install-codex.sh

install-claude-code:
	./scripts/install-claude-code.sh "$(if $(PROJECT_DIR),$(PROJECT_DIR),.)"

install-opencode:
	./scripts/install-opencode.sh "$(if $(PROJECT_DIR),$(PROJECT_DIR),.)"

verify-installs:
	./scripts/supernb verify-installs $(if $(HARNESS),--harness "$(HARNESS)",) $(if $(PROJECT_DIR),--project-dir "$(PROJECT_DIR)",)

verify-claude-loop:
	./scripts/supernb verify-claude-loop $(if $(WORKSPACE),--workspace "$(WORKSPACE)",) $(if $(ALLOW_LIVE_RUN),--allow-live-run,) $(if $(CLEANUP),--cleanup,) $(if $(OBSERVATION_TIMEOUT_SECONDS),--observation-timeout-seconds "$(OBSERVATION_TIMEOUT_SECONDS)",) $(if $(AUDIT_TIMEOUT_SECONDS),--audit-timeout-seconds "$(AUDIT_TIMEOUT_SECONDS)",)

init-initiative:
	@if [ -z "$(INITIATIVE)" ]; then echo "Usage: make init-initiative INITIATIVE=my-product [TITLE='My Product']"; exit 1; fi
	GOAL="$(GOAL)" REPOSITORY="$(REPOSITORY)" PROJECT_DIR="$(PROJECT_DIR)" HARNESS="$(HARNESS)" PLATFORM="$(PLATFORM)" STACK="$(STACK)" PRODUCT_CATEGORY="$(PRODUCT_CATEGORY)" MARKETS="$(MARKETS)" RESEARCH_WINDOW="$(RESEARCH_WINDOW)" SEED_COMPETITORS="$(SEED_COMPETITORS)" SOURCE_LOCALE="$(if $(SOURCE_LOCALE),$(SOURCE_LOCALE),en)" TARGET_LOCALES="$(TARGET_LOCALES)" QUALITY_BAR="$(if $(QUALITY_BAR),$(QUALITY_BAR),10m-dau-grade)" CONSTRAINTS="$(CONSTRAINTS)" ./scripts/init-initiative.sh "$(INITIATIVE)" "$(TITLE)"

run-initiative:
	@if [ -z "$(INITIATIVE_ID)" ] && [ -z "$(SPEC)" ]; then echo "Usage: make run-initiative INITIATIVE_ID=<id> [PHASE=auto] or make run-initiative SPEC=/path/to/initiative.yaml"; exit 1; fi
	./scripts/supernb run $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) $(if $(PHASE),--phase "$(PHASE)",)

execute-next:
	@if [ -z "$(INITIATIVE_ID)" ] && [ -z "$(SPEC)" ]; then echo "Usage: make execute-next INITIATIVE_ID=<id> [HARNESS=codex|claude-code|opencode] [PROJECT_DIR=/path] [DRY_RUN=1]"; exit 1; fi
	./scripts/supernb execute-next $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) $(if $(PHASE),--phase "$(PHASE)",) $(if $(HARNESS),--harness "$(HARNESS)",) $(if $(PROJECT_DIR),--project-dir "$(PROJECT_DIR)",) $(if $(PROMPT_FILE),--prompt-file "$(PROMPT_FILE)",) $(foreach arg,$(subst ,, ,$(CLI_ARGS)),--cli-arg "$(arg)") $(if $(DRY_RUN),--dry-run,)

apply-execution:
	@if [ -z "$(PACKET)" ]; then echo "Usage: make apply-execution INITIATIVE_ID=<id> PACKET=/path/to/packet [CERTIFY=1] [APPLY_CERTIFICATION=1]"; exit 1; fi
	./scripts/supernb apply-execution $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) --packet "$(PACKET)" $(if $(STATUS),--status "$(STATUS)",) $(if $(SUMMARY),--summary "$(SUMMARY)",) $(if $(CERTIFY),--certify,) $(if $(APPLY_CERTIFICATION),--apply-certification,) $(if $(ACTOR),--actor "$(ACTOR)",) $(if $(DATE),--date "$(DATE)",) $(if $(NO_RERUN),--no-rerun,)

import-execution:
	@if [ -z "$(INITIATIVE_ID)" ] && [ -z "$(SPEC)" ]; then echo "Usage: make import-execution INITIATIVE_ID=<id> PHASE=<phase> REPORT_JSON=/path/to/report.json"; exit 1; fi
	@if [ -z "$(PHASE)" ] || [ -z "$(REPORT_JSON)" ]; then echo "PHASE and REPORT_JSON are required."; exit 1; fi
	./scripts/supernb import-execution $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) --phase "$(PHASE)" --report-json "$(REPORT_JSON)" $(if $(RESPONSE_FILE),--response-file "$(RESPONSE_FILE)",) $(if $(STDOUT_FILE),--stdout-file "$(STDOUT_FILE)",) $(if $(STDERR_FILE),--stderr-file "$(STDERR_FILE)",) $(foreach path,$(subst ,, ,$(ARTIFACT_PATHS)),--artifact-path "$(path)") $(if $(HARNESS),--harness "$(HARNESS)",) $(if $(EXECUTION_STATUS),--execution-status "$(EXECUTION_STATUS)",) $(if $(EXIT_CODE),--exit-code "$(EXIT_CODE)",)

record-result:
	@if [ -z "$(INITIATIVE_ID)" ] && [ -z "$(SPEC)" ]; then echo "Usage: make record-result INITIATIVE_ID=<id> STATUS=<status> SUMMARY='...'; optional PHASE=<phase> SOURCE=manual-override OVERRIDE_REASON='...' or SOURCE=execution-packet SOURCE_PACKET=/path NOTES_FILE=/path ARTIFACT_PATHS='a,b'"; exit 1; fi
	@if [ -z "$(STATUS)" ] || [ -z "$(SUMMARY)" ]; then echo "STATUS and SUMMARY are required."; exit 1; fi
	./scripts/supernb record-result $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) $(if $(PHASE),--phase "$(PHASE)",) --status "$(STATUS)" --summary "$(SUMMARY)" $(if $(SOURCE),--source "$(SOURCE)",) $(if $(OVERRIDE_REASON),--override-reason "$(OVERRIDE_REASON)",) $(if $(SOURCE_PACKET),--source-packet "$(SOURCE_PACKET)",) $(if $(NOTES_FILE),--notes-file "$(NOTES_FILE)",) $(foreach path,$(subst ,, ,$(ARTIFACT_PATHS)),--artifact-path "$(path)") $(if $(NO_RERUN),--no-rerun,)

advance-phase:
	@if [ -z "$(INITIATIVE_ID)" ] && [ -z "$(SPEC)" ]; then echo "Usage: make advance-phase INITIATIVE_ID=<id> PHASE=<phase> STATUS=<status> [ACTOR=name] [SUMMARY='...']"; exit 1; fi
	@if [ -z "$(PHASE)" ] || [ -z "$(STATUS)" ]; then echo "PHASE and STATUS are required."; exit 1; fi
	./scripts/supernb advance-phase $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) --phase "$(PHASE)" --status "$(STATUS)" $(if $(ACTOR),--actor "$(ACTOR)",) $(if $(DATE),--date "$(DATE)",) $(if $(SUMMARY),--summary "$(SUMMARY)",) $(if $(NO_RERUN),--no-rerun,)

certify-phase:
	@if [ -z "$(INITIATIVE_ID)" ] && [ -z "$(SPEC)" ]; then echo "Usage: make certify-phase INITIATIVE_ID=<id> [PHASE=<phase>] [APPLY=1] [ACTOR=name]"; exit 1; fi
	./scripts/supernb certify-phase $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) $(if $(PHASE),--phase "$(PHASE)",) $(if $(APPLY),--apply,) $(if $(ACTOR),--actor "$(ACTOR)",) $(if $(DATE),--date "$(DATE)",)

upgrade-artifacts:
	@if [ -z "$(INITIATIVE_ID)" ] && [ -z "$(SPEC)" ]; then echo "Usage: make upgrade-artifacts INITIATIVE_ID=<id> or make upgrade-artifacts SPEC=/path/to/initiative.yaml"; exit 1; fi
	./scripts/supernb upgrade-artifacts $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",)

migrate-legacy:
	@if [ -z "$(INITIATIVE_ID)" ] && [ -z "$(SPEC)" ]; then echo "Usage: make migrate-legacy INITIATIVE_ID=<id> [LEGACY_ROOT=/path/to/.supernb]"; exit 1; fi
	./scripts/supernb migrate-legacy $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) $(if $(LEGACY_ROOT),--legacy-root "$(LEGACY_ROOT)",) $(if $(NO_UPGRADE),--no-upgrade,)

clean-initiative:
	@if [ -z "$(INITIATIVE_ID)" ] && [ -z "$(SPEC)" ]; then echo "Usage: make clean-initiative INITIATIVE_ID=<id> [APPLY=1] [DELETE=1] [ARCHIVE_DIR=/path]"; exit 1; fi
	./scripts/supernb clean-initiative $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) $(if $(APPLY),--apply,) $(if $(DELETE),--delete,) $(if $(ARCHIVE_DIR),--archive-dir "$(ARCHIVE_DIR)",) $(if $(KEEP_COMMAND_BRIEFS),--keep-command-briefs "$(KEEP_COMMAND_BRIEFS)",) $(if $(KEEP_EXECUTIONS_PER_PHASE),--keep-executions-per-phase "$(KEEP_EXECUTIONS_PER_PHASE)",) $(if $(PRUNE_PHASE_RESULTS),--prune-phase-results,) $(if $(KEEP_PHASE_RESULTS_PER_PHASE),--keep-phase-results-per-phase "$(KEEP_PHASE_RESULTS_PER_PHASE)",)

prompt-bootstrap:
	./scripts/supernb prompt-bootstrap $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) $(if $(PROJECT_DIR),--project-dir "$(PROJECT_DIR)",) $(if $(PHASE),--phase "$(PHASE)",) $(if $(TITLE),--title "$(TITLE)",) $(if $(INITIATIVE),--initiative-slug "$(INITIATIVE)",) $(if $(GOAL),--goal "$(GOAL)",) $(if $(NO_RUN),--no-run,) $(if $(START_LOOP),--start-loop,) $(if $(NO_AUTO_INIT),--no-auto-init,)

prompt-closeout:
	./scripts/supernb prompt-closeout $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(SPEC),--spec "$(SPEC)",) $(if $(PHASE),--phase "$(PHASE)",) $(if $(REPORT_JSON),--report-json "$(REPORT_JSON)",) $(if $(RESPONSE_FILE),--response-file "$(RESPONSE_FILE)",) $(if $(STDOUT_FILE),--stdout-file "$(STDOUT_FILE)",) $(if $(STDERR_FILE),--stderr-file "$(STDERR_FILE)",) $(foreach path,$(subst ,, ,$(ARTIFACT_PATHS)),--artifact-path "$(path)") $(if $(ACTOR),--actor "$(ACTOR)",) $(if $(HARNESS),--harness "$(HARNESS)",)

test:
	./scripts/supernb test

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
	./scripts/render-command.sh --command "$(COMMAND)" $(if $(GOAL),--goal "$(GOAL)",) $(if $(REPOSITORY),--repository "$(REPOSITORY)",) $(if $(PLATFORM),--platform "$(PLATFORM)",) $(if $(STACK),--stack "$(STACK)",) $(if $(MARKETS),--markets "$(MARKETS)",) $(if $(LOCALES),--locales "$(LOCALES)",) $(if $(CONSTRAINTS),--constraints "$(CONSTRAINTS)",) $(if $(SOURCE_LOCALE),--source-locale "$(SOURCE_LOCALE)",) $(if $(TARGET_LOCALES),--target-locales "$(TARGET_LOCALES)",) $(if $(CAPABILITY_HINT),--capability-hint "$(CAPABILITY_HINT)",) $(if $(TRANSLATION_CONSTRAINTS),--translation-constraints "$(TRANSLATION_CONSTRAINTS)",) $(if $(PRODUCT_CATEGORY),--product-category "$(PRODUCT_CATEGORY)",) $(if $(SEED_COMPETITORS),--seed-competitors "$(SEED_COMPETITORS)",) $(if $(RESEARCH_WINDOW),--research-window "$(RESEARCH_WINDOW)",) $(if $(QUALITY_BAR),--quality-bar "$(QUALITY_BAR)",) $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",)

save-command:
	@if [ -z "$(COMMAND)" ]; then echo "Usage: make save-command COMMAND=<command-name> [GOAL='...'] [TITLE='...']"; exit 1; fi
	./scripts/save-command-brief.sh --command "$(COMMAND)" $(if $(TITLE),--title "$(TITLE)",) $(if $(INITIATIVE_ID),--initiative-id "$(INITIATIVE_ID)",) $(if $(GOAL),--goal "$(GOAL)",) $(if $(REPOSITORY),--repository "$(REPOSITORY)",) $(if $(PLATFORM),--platform "$(PLATFORM)",) $(if $(STACK),--stack "$(STACK)",) $(if $(MARKETS),--markets "$(MARKETS)",) $(if $(LOCALES),--locales "$(LOCALES)",) $(if $(CONSTRAINTS),--constraints "$(CONSTRAINTS)",) $(if $(SOURCE_LOCALE),--source-locale "$(SOURCE_LOCALE)",) $(if $(TARGET_LOCALES),--target-locales "$(TARGET_LOCALES)",) $(if $(CAPABILITY_HINT),--capability-hint "$(CAPABILITY_HINT)",) $(if $(TRANSLATION_CONSTRAINTS),--translation-constraints "$(TRANSLATION_CONSTRAINTS)",) $(if $(PRODUCT_CATEGORY),--product-category "$(PRODUCT_CATEGORY)",) $(if $(SEED_COMPETITORS),--seed-competitors "$(SEED_COMPETITORS)",) $(if $(RESEARCH_WINDOW),--research-window "$(RESEARCH_WINDOW)",) $(if $(QUALITY_BAR),--quality-bar "$(QUALITY_BAR)",)
