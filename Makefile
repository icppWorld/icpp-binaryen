SHELL := /bin/bash

# Disable built-in rules and variables
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

PYTHON_DIRS ?= src/icpp_binaryen test scripts

.PHONY: summary
summary:
	@echo "---"
	@echo "python  : $$(which python)"
	@echo "version : $$(grep __version__ src/icpp_binaryen/version.py)"

.PHONY: install-python
install-python:
	python -m ensurepip --upgrade
	python -m pip install --upgrade pip
	rm -rf src/*.egg-info
	python -m pip install -e ".[dev]"

.PHONY: get-binaryen
get-binaryen:
	python -m scripts.get_binaryen

.PHONY: python-format
python-format:
	@echo "---"
	@echo "python-format"
	python -m black $(PYTHON_DIRS)

.PHONY: python-lint
python-lint:
	@echo "---"
	@echo "python-lint"
	python -m pylint --jobs=0 --rcfile=.pylintrc $(PYTHON_DIRS)

.PHONY: python-type
python-type:
	@echo "---"
	@echo "python-type"
	python -m mypy --config-file .mypy.ini --show-column-numbers --strict $(PYTHON_DIRS)

.PHONY: all-static
all-static: \
	python-format python-lint python-type

.PHONY: unit-test
unit-test:
	@echo "---"
	@echo "unit-test"
	python -m pytest -vv test/unit

.PHONY: smoke-test
smoke-test:
	@echo "---"
	@echo "smoke-test"
	python -m pytest -vv test/smoke

.PHONY: all-tests
all-tests: all-static
	python -m pytest -vv test/unit test/smoke

.PHONY: parity-test
parity-test:
	python -m scripts.parity_test

.PHONY: check-downstream-pins
check-downstream-pins:
	@python -m scripts.check_downstream_pins

###########################################################################
# Ceremony 4 -- verify downstream (tiered). See README-feature-guide.md.
#
# Run these from the DOWNSTREAM repo's env (conda activate llama_cpp_canister):
# downstream-install-dev force-installs THIS tree over the PyPI wheel, so
# llama's post_wasm_function exercises the dev code rather than the release.
#
# Override the location when llama_cpp_canister is not a sibling:
#   make downstream-verify-api DOWNSTREAM_LLAMA=~/work/llama_cpp_canister
DOWNSTREAM_LLAMA ?= ../llama_cpp_canister

.PHONY: downstream-install-dev
downstream-install-dev:
	python -m pip install --force-reinstall --no-deps .

# The API tier: build llama's wasm on the host -- which runs fix_globals_limit
# as icpp.toml's post_wasm_function -- then deploy it and run its model-free
# API suite (health, memory status, access control). No models, no docker.
#
# Host caveat: llama's icpp.toml hard-codes ggml arch/x86/ sources, so this
# needs an x86_64 host; on an arm64 Mac rely on llama's CI or its docker path.
.PHONY: downstream-verify-api
downstream-verify-api: check-downstream-pins downstream-install-dev
	$(MAKE) -C $(DOWNSTREAM_LLAMA) build-info-cpp-wasm
	cd $(DOWNSTREAM_LLAMA) && icpp build-wasm
	$(MAKE) -C $(DOWNSTREAM_LLAMA) icp-test-identities
	cd $(DOWNSTREAM_LLAMA) && icp network start -d
	cd $(DOWNSTREAM_LLAMA) && icp deploy -e local -y --identity llama-cpp-testing
	cd $(DOWNSTREAM_LLAMA) && pytest -vv --network local --identity llama-cpp-testing \
	    test/test_canister_functions.py; \
	  status=$$?; icp network stop || true; exit $$status

# The release tier: the API tier plus the byte-level gates -- the parity golden
# and the wasm-hash-sensitive docker build with its prebuilt-wasm pytest
# (heavy: docker + models). parity-test runs here rather than in the API tier
# because it needs the _before_opt_internal artifact the build above produces.
#
# NOTE: parity-test exits 0 when that artifact is absent, printing
# PARITY SKIPPED -- a green run is not by itself proof.
.PHONY: downstream-verify-full
downstream-verify-full: downstream-verify-api
	$(MAKE) parity-test
	$(MAKE) -C $(DOWNSTREAM_LLAMA) docker-build-base docker-build-wasm
	$(MAKE) -C $(DOWNSTREAM_LLAMA) test-llm-wasm-prebuilt
	@echo "---"
	@echo "Compare the docker wasm hash printed above against the current"
	@echo "WASM-HASHES.md row before concluding a release is byte-identical."

###########################################################################
# Building the pypi package (publishing is CI-only: tag-triggered trusted
# publishing — see README-release-guide.md).
# Wheels only: an sdist would ship whichever platform's lib was fetched
# locally, and the bundled library makes a source install meaningless.
.PHONY: pypi-build
pypi-build:
	rm -rf dist
	python -m build --wheel
	$(MAKE) check-wheel-arch

# The wheel filename is a promise about the libbinaryen inside it. Verify it,
# because a tag that lies makes pip hand the wrong dylib to the wrong machine.
.PHONY: check-wheel-arch
check-wheel-arch:
	@echo "---"
	@echo "check-wheel-arch"
	python -m scripts.check_wheel_arch
