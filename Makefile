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
# Building the pypi package (publishing is CI-only: tag-triggered trusted
# publishing — see README-release-guide.md).
# Wheels only: an sdist would ship whichever platform's lib was fetched
# locally, and the bundled library makes a source install meaningless.
.PHONY: pypi-build
pypi-build:
	rm -rf dist
	python -m build --wheel
