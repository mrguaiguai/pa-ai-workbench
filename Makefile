SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON ?= $(if $(wildcard apps/pa-api/.venv/bin/python),apps/pa-api/.venv/bin/python,python3)
NPM ?= npm
COMPOSE ?= docker compose

REPOSITORY_ROOT := $(CURDIR)
PA_API_ROOT := $(REPOSITORY_ROOT)/apps/pa-api
PA_WEB_ROOT := $(REPOSITORY_ROOT)/apps/pa-web
WEKNORA_ROOT := $(REPOSITORY_ROOT)/platform/weknora
PYTHONPATH_ROOTS := $(PA_API_ROOT):$(REPOSITORY_ROOT)/packages/agent-runtime:$(REPOSITORY_ROOT)/packages/knowledge-engine
PAR_CHECKER := scripts/validation/check_pa_repository_reorganization.py
WEB_OUT_DIR ?= /tmp/pa-ai-workbench-par-p2-03-web

.PHONY: help setup start pa-start pa-stop pa-status pa-logs status \
	weknora-dev-start weknora-dev-stop weknora-dev-status weknora-dev-logs \
	compose-config launchagents-install launchagents-uninstall \
	native-build native-test release-version release-images release-lite release-mac \
	validate validate-command-surface validate-python validate-backend validate-web \
	validate-static-acceptance validate-live-acceptance validate-clean-clone \
	validate-par validate-par-json validate-par-final

help:
	@echo "PA AI Workbench root commands"
	@echo ""
	@echo "Development:"
	@echo "  make setup                 prepare local PA + WeKnora dependencies"
	@echo "  make start                 start WeKnora and local PA services"
	@echo "  make pa-start|pa-stop      manage local PA API/Web processes"
	@echo "  make pa-status|pa-logs     inspect local PA process state"
	@echo "  make weknora-dev-start     start native development dependencies"
	@echo ""
	@echo "Operations:"
	@echo "  make status                read-only Compose and PA process status"
	@echo "  make compose-config        render the canonical root Compose model"
	@echo "  make launchagents-install  install/start macOS PA LaunchAgents"
	@echo "  make launchagents-uninstall remove macOS PA LaunchAgents"
	@echo ""
	@echo "Release:"
	@echo "  make release-version       print sanitized WeKnora version metadata"
	@echo "  make release-images        build native images"
	@echo "  make release-lite          build the WeKnora Lite archive"
	@echo "  make release-mac           build the WeKnora macOS app"
	@echo ""
	@echo "Validation:"
	@echo "  make validate              command, Python, backend, Web, and PAR gates"
	@echo "  make validate-static-acceptance  repository boundary contract tests"
	@echo "  make validate-live-acceptance  live PA + WeKnora workflow/browser gates"
	@echo "  make validate-clean-clone  reproduce final acceptance from an index-clean clone"
	@echo "  make validate-par-json     machine-readable PAR governance result"
	@echo "  make validate-par-final    final PAR governance and evidence gate"

setup:
	./scripts/dev/pa-workbench-setup.sh

start:
	./scripts/dev/pa-workbench-start.sh

pa-start:
	./scripts/dev/pa-dev-services.sh start

pa-stop:
	./scripts/dev/pa-dev-services.sh stop

pa-status:
	./scripts/dev/pa-dev-services.sh status

pa-logs:
	./scripts/dev/pa-dev-services.sh logs

weknora-dev-start:
	./scripts/dev/weknora-dev.sh start

weknora-dev-stop:
	./scripts/dev/weknora-dev.sh stop

weknora-dev-status:
	./scripts/dev/weknora-dev.sh status

weknora-dev-logs:
	./scripts/dev/weknora-dev.sh logs

status: pa-status
	$(COMPOSE) -f compose.yaml ps

compose-config:
	$(COMPOSE) --env-file infra/env/compose.env.example -f compose.yaml config --no-env-resolution

launchagents-install:
	./scripts/ops/install-pa-launchagents.sh

launchagents-uninstall:
	./scripts/ops/uninstall-pa-launchagents.sh

native-build:
	$(MAKE) -C platform/weknora build

native-test:
	$(MAKE) -C platform/weknora test

release-version:
	./scripts/release/weknora-version.sh info

release-images:
	./scripts/release/build-weknora-images.sh

release-lite:
	./scripts/release/package-weknora-lite.sh

release-mac:
	./scripts/release/package-weknora-mac-app.sh

validate: validate-command-surface validate-python validate-backend validate-web validate-static-acceptance validate-par

validate-command-surface:
	@find scripts/dev scripts/ops scripts/release scripts/validation -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n
	@echo "shell syntax: PASS"

validate-python:
	@$(PYTHON) -c 'from pathlib import Path; roots=[Path("apps/pa-api"),Path("packages/agent-runtime"),Path("packages/knowledge-engine"),Path("scripts"),Path("tests")]; files=[p for r in roots for p in r.rglob("*.py") if "__pycache__" not in p.parts and ".venv" not in p.parts]; [compile(p.read_bytes(),str(p),"exec") for p in files]; print(f"python syntax: PASS ({len(files)} files)")'

validate-backend:
	@PA_SKIP_DOTENV=1 DATABASE_URL=sqlite:///:memory: UPLOAD_DIR=/tmp/pa-par-p2-03-uploads PYTHONPATH="$(PYTHONPATH_ROOTS)" $(PYTHON) -m unittest discover -s tests/backend -v

validate-web:
	@cd apps/pa-web && ./node_modules/.bin/tsc --noEmit
	@cd apps/pa-web && ./node_modules/.bin/vite build --outDir "$(WEB_OUT_DIR)" --emptyOutDir

validate-static-acceptance:
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests/acceptance -v

validate-live-acceptance:
	@PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(PYTHONPATH_ROOTS):$(REPOSITORY_ROOT)/scripts/validation" $(PYTHON) scripts/validation/check_pa_repository_live_acceptance.py

validate-clean-clone:
	@PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(PYTHONPATH_ROOTS):$(REPOSITORY_ROOT)/scripts/validation" $(PYTHON) scripts/validation/check_pa_repository_clean_clone_acceptance.py

validate-par:
	$(PYTHON) $(PAR_CHECKER)

validate-par-json:
	$(PYTHON) $(PAR_CHECKER) --json

validate-par-final:
	$(PYTHON) $(PAR_CHECKER) --final
