# Usage:
# make						# Runs copyright-update and flake test
# make build				# to build the package
# make copyright			# to build the package
#
# Set NO_VENV=True like this 'make NO_VENV=True build' to skip virtualenv activation for python commands


VIRTUAL_ENV_PATH=venv
SKIP_VENV="${NO_VENV}"
SETUP_MODULE=setup.py

.DEFAULT_GOAL := pre_commit

pre_commit: copyright flake8

help:
	@echo "Usage:"
	@echo "  make				- Run this before each commit. It runs all required pre-commit actions"
	@echo "  make copyright		- Updates copyright preamble for each file"
	@echo "  make flake8			- Runs codestyle checks"
	@echo "  make test			- Runs unit tests"
	@echo "  make build			- Builds distribution package"
	@echo "  make clean			- Removes temporary files, artifacts, etc"
	@echo ""
	@echo "Notes:"
	@echo "Set NO_VENV=True like this 'make NO_VENV=True build' to skip virtualenv activation for python commands"


copyright:
	@( \
       if [ -z $(SKIP_VENV) ]; then source $(VIRTUAL_ENV_PATH)/bin/activate; fi; \
       echo "Applying copyright..."; \
       ./development/copyright-update; \
       echo "DONE: copyright"; \
    )

flake8:
	@( \
       if [ -z $(SKIP_VENV) ]; then source $(VIRTUAL_ENV_PATH)/bin/activate; fi; \
       echo "Runing Flake8 checks..."; \
       ./development/flake8; \
       echo "DONE: Flake8"; \
    )

test:
	@( \
       if [ -z $(SKIP_VENV) ]; then source $(VIRTUAL_ENV_PATH)/bin/activate; fi; \
       echo "Runing unit tests..."; \
       pytest; \
       echo "DONE: Unit tests"; \
    )

build: copyright flake8 clean
	@( \
       if [ -z $(SKIP_VENV) ]; then source $(VIRTUAL_ENV_PATH)/bin/activate; fi; \
       echo "Building wheel package..."; \
       bash -c "cd src && python ./$(SETUP_MODULE) bdist_wheel --dist-dir=../dist --bdist-dir=../../build"; \
       echo "DONE: wheel package"; \
    )
	@( \
       if [ -z $(SKIP_VENV) ]; then source $(VIRTUAL_ENV_PATH)/bin/activate; fi; \
       echo "Building source distribution..."; \
       bash -c "cd src && python ./$(SETUP_MODULE) sdist --dist-dir=../dist"; \
       echo "DONE: source distribution"; \
    )

clean:
	rm -rf src/build dist/* *.egg-info src/*.egg-info .pytest_cache
