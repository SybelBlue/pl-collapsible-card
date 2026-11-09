SHELL := /bin/sh
.SHELLFLAGS := -eu -c

.DEFAULT_GOAL := test

UV_CACHE_DIR ?= /tmp/learnvia-uv-cache
UV_RUN ?= uv run --active --locked

LIB_TEST_PATHS := \
	elements \
	scripts \
	serverFilesCourse

QUESTION_PATHS ?= questions
E2E_SEED_COUNT ?= 3
E2E_FUZZ_SEED_COUNT ?= 10
E2E_FUZZ_SEED ?=
E2E_DIFF_BASE ?= main
E2E_DIFF_HEAD ?= HEAD
E2E_SHARD_COUNT ?= 6
E2E_SHARD ?=
E2E_SHARD_REPORT ?=
E2E_RUN_ARGS = --question-path "$(QUESTION_PATHS)" --seed-count "$(E2E_SEED_COUNT)" --fuzz-seeds
E2E_DIFF_ARGS = --base "$(E2E_DIFF_BASE)" --head "$(E2E_DIFF_HEAD)" --seed-count "$(E2E_FUZZ_SEED_COUNT)"
E2E_COMMON_ARGS = \
	$(if $(strip $(E2E_FUZZ_SEED)),--fuzz-seed "$(E2E_FUZZ_SEED)") \
	$(if $(strip $(PRAIRIELEARN_PATH)),--prairielearn-path "$(PRAIRIELEARN_PATH)")
E2E_SHARD_ARGS = \
	$(if $(strip $(E2E_SHARD)),--shard "$(E2E_SHARD)") \
	$(if $(strip $(E2E_SHARD_REPORT)),--shard-report "$(E2E_SHARD_REPORT)")
IGNORED_ELEMENTS :=

PRETTIER_EXCLUDES = $(foreach element,$(IGNORED_ELEMENTS),"!$(element)/**")
JSON_PATHS := "infoCourse.json" "{.vscode,courseInstances,elements,questions}/**/*.{json,jsonc}"
FORMAT_MODE = $(if $(filter check-format-%,$@),--check,--write)
REQUIRED_VENDOR_PACKAGES := prairielearn-schemas prairielearn-htmlmustache

export UV_CACHE_DIR

DOCKER_JOBS_DIR ?= $(shell mktemp -d /tmp/pl-docker-jobs.XXXXXX)

export DOCKER_JOBS_DIR

.PHONY: deps deps-install venv install-hooks refresh-git-hooks clean-git-hooks
.PHONY: vendor-update-all vendor-update-required vendor-check-upstream vendor-check-required vendor-check-prairielearn vendor-verify
.PHONY: update-vendored check-vendored verify-vendored
.PHONY: test test-helpers test-e2e test-e2e-sharded test-e2e-fuzz test-e2e-fuzz-diff-only test-e2e-fuzz-sharded test-content add-e2e-regression-seed
.PHONY: validate validate-json validate-htmlmustache check-navigator typecheck
.PHONY: format format-py format-json format-html check-format check-format-py check-format-json check-format-html
.PHONY: check ci-dryrun ci-run ci-retry ci-watch release-dry-run release release-push dev docker clean clean-python clean-js clean-docker

# install deps, RUN ME FIRST
# requires pnpm and uv to be installed on the commandline
deps: install-hooks deps-install
	$(UV_RUN) pl-vendor sync

# Reproducible dependency installation shared by local setup and CI.
deps-install:
	pnpm install --frozen-lockfile
	uv sync --locked

venv: deps
	uv venv --refresh

install-hooks:
	git config core.hooksPath .githooks

clean-git-hooks:
	@if git config --local --get-all core.hooksPath >/dev/null; then \
		git config --local --unset-all core.hooksPath; \
	fi

refresh-git-hooks: clean-git-hooks
	@$(MAKE) install-hooks

vendor-update-all update-vendored:
	@$(UV_RUN) pl-vendor update

vendor-update-required:
	@$(UV_RUN) python scripts/update_required_vendored.py

vendor-check-upstream check-vendored:
	@$(UV_RUN) pl-vendor check upstream content

vendor-check-required:
	@$(UV_RUN) pl-vendor check upstream content $(REQUIRED_VENDOR_PACKAGES)

vendor-check-prairielearn:
	@$(UV_RUN) pl-vendor check prairielearn python

vendor-verify verify-vendored:
	@$(UV_RUN) pl-vendor check installed


# Run tests
add-e2e-regression-seed:
	@$(UV_RUN) pl-e2e-test add-seed \
		"$(QUESTION_PATH)" "$(VARIANT_SEED)"

test: test-helpers test-e2e-sharded test-e2e-fuzz-sharded

test-helpers:
	@$(UV_RUN) pytest $(LIB_TEST_PATHS) $(PYTEST_ARGS)

test-e2e test-e2e-sharded: E2E_MODE = run
test-e2e test-e2e-sharded: E2E_SUITE_ARGS = $(E2E_RUN_ARGS)
test-e2e-fuzz-diff-only test-e2e-fuzz-sharded: E2E_MODE = diff
test-e2e-fuzz-diff-only test-e2e-fuzz-sharded: E2E_SUITE_ARGS = $(E2E_DIFF_ARGS)

test-e2e test-e2e-fuzz-diff-only:
	@if [ ! -d "$(QUESTION_PATHS)" ] || \
		! find "$(QUESTION_PATHS)" -name info.json -type f -print -quit | grep -q .; then \
		echo "No question info.json files found; skipping end-to-end tests."; \
	elif [ "$(E2E_MODE)" = "diff" ] && \
		! { git rev-parse --verify --quiet "$(E2E_DIFF_BASE)^{commit}" >/dev/null && \
			git rev-parse --verify --quiet "$(E2E_DIFF_HEAD)^{commit}" >/dev/null; }; then \
		echo "E2E diff refs $(E2E_DIFF_BASE)..$(E2E_DIFF_HEAD) are unavailable; skipping diff-only tests."; \
	else \
		$(UV_RUN) pl-e2e-test $(filter diff,$(E2E_MODE)) \
			$(E2E_SUITE_ARGS) $(E2E_COMMON_ARGS) $(E2E_SHARD_ARGS) $(PYTEST_ARGS); \
	fi

# The parallel wrapper assigns shards and reports itself.
test-e2e-sharded test-e2e-fuzz-sharded:
	@if [ ! -d "$(QUESTION_PATHS)" ] || \
		! find "$(QUESTION_PATHS)" -name info.json -type f -print -quit | grep -q .; then \
		echo "No question info.json files found; skipping end-to-end tests."; \
	elif [ "$(E2E_MODE)" = "diff" ] && \
		! { git rev-parse --verify --quiet "$(E2E_DIFF_BASE)^{commit}" >/dev/null && \
			git rev-parse --verify --quiet "$(E2E_DIFF_HEAD)^{commit}" >/dev/null; }; then \
		echo "E2E diff refs $(E2E_DIFF_BASE)..$(E2E_DIFF_HEAD) are unavailable; skipping diff-only tests."; \
	else \
		$(UV_RUN) pl-e2e-test parallel --shard-count "$(E2E_SHARD_COUNT)" \
			$(E2E_MODE) -- $(E2E_SUITE_ARGS) $(E2E_COMMON_ARGS) $(PYTEST_ARGS); \
	fi

test-e2e-fuzz: test-e2e-fuzz-diff-only

test-content: test-e2e

validate: validate-json validate-htmlmustache

validate-json:
	@$(UV_RUN) scripts/validate_json.py

validate-htmlmustache:
	@pnpm exec htmlmustache check

# Check assessments for missing, incomplete, or duplicate questions.
check-navigator:
	@if [ ! -f infoCourse.json ] || [ ! -d courseInstances ] || \
		! find courseInstances -name infoAssessment.json -type f -print -quit | grep -q .; then \
		echo "No course metadata with assessments found; skipping PrairieLearn Navigator."; \
	else \
		pnpm exec prairielearn-navigator check; \
	fi


# typecheck python
typecheck:
	@find . \( \
		$(foreach element,$(IGNORED_ELEMENTS),-path ./$(element) -o) \
		-path '*/.*' -o \
		-name node_modules -o \
		-name __pycache__ \
	\) -prune -o \( -name '*.py' -o -name '*.pyi' \) \
		-exec $(UV_RUN) pyright {} +


# format source
format: format-py format-json format-html

check-format: check-format-py check-format-json check-format-html

format-py check-format-py:
	@$(UV_RUN) ruff format $(if $(filter check-format-%,$@),--check) \
		$(foreach element,$(IGNORED_ELEMENTS),--extend-exclude $(element)) .

format-json check-format-json:
	@pnpm exec prettier $(FORMAT_MODE) $(JSON_PATHS) $(PRETTIER_EXCLUDES)

format-html check-format-html:
	@pnpm exec htmlmustache format $(FORMAT_MODE)

# One check list for local use, the pre-push hook, and GitHub Actions.
check:
	@$(UV_RUN) python scripts/run_parallel_checks.py \
		--check 'Vendored packages' '$(MAKE) vendor-verify' \
		--check 'Python compatibility' '$(MAKE) vendor-check-prairielearn' \
		--check 'Tests' '$(MAKE) --keep-going test' \
		--check 'Validation' '$(MAKE) --keep-going validate' \
		--check 'Formatting' '$(MAKE) --keep-going check-format' \
		--check 'Python types' '$(MAKE) typecheck' \
		--check 'File links' '$(MAKE) check-navigator'

ci-dryrun: check

release-dry-run:
	@$(UV_RUN) pl-vendor release build --dry-run

release:
	@$(UV_RUN) pl-vendor release build

release-push:
	@$(UV_RUN) pl-vendor release build --push

ci-run ci-retry ci-watch:
	@CI_BRANCH='$(BRANCH)' CI_RUN_ID='$(RUN_ID)' bash scripts/manage_ci_run.sh $(patsubst ci-%,%,$@)

# launch prairielearn
dev:
	@pnpm dlx @sybelblue/prairielearn-runner@latest

docker:
	docker run -it --rm --pull=always \
		-p 3000:3000 \
		-v ".:/course" \
		-v "$(DOCKER_JOBS_DIR):/jobs" \
		-e HOST_JOBS_DIR="$(DOCKER_JOBS_DIR)" \
		-v /var/run/docker.sock:/var/run/docker.sock \
		--add-host=host.docker.internal:172.17.0.1 \
		prairielearn/prairielearn:us-prod-live

# Remove project-local and Docker build artifacts.
clean: clean-python clean-js clean-docker

clean-python:
	@uv cache clean --cache-dir "$(UV_CACHE_DIR)"
	@rm -rf .venv build dist htmlcov
	@find . -type d \( \
		-name __pycache__ -o \
		-name .pytest_cache -o \
		-name .ruff_cache -o \
		-name .mypy_cache -o \
		-name '*.egg-info' \
	\) -prune -exec rm -rf {} +
	@find . -type f \( \
		-name '*.py[co]' -o \
		-name .coverage -o \
		-name 'coverage.*' \
	\) -delete

clean-js:
	@rm -rf node_modules

clean-docker:
	@image_refs="$$(docker image ls \
		--filter dangling=false \
		--format '{{.Repository}}:{{.Tag}}' \
		prairielearn/prairielearn)"; \
	if [ -n "$$image_refs" ]; then \
		docker image rm $$image_refs; \
	fi
