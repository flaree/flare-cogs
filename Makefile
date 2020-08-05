# thanks zeph
PYTHON ?= python3.8
DIFF := $(shell git diff --name-only --staged "*.py" "*.pyi")
ifeq ($(DIFF),)
	DIFF := $(shell git ls-files "*.py" "*.pyi")
endif

lint:
	$(PYTHON) -m flake8 --count --select=E9,F7,F82 --show-source $(DIFF)
stylecheck:
	$(PYTHON) -m autoflake --check --imports aiohttp,discord,redbot $(DIFF)
	$(PYTHON) -m isort --check-only $(DIFF)
	$(PYTHON) -m black --check $(DIFF)
reformat:
	$(PYTHON) -m autoflake --in-place --imports=aiohttp,discord,redbot $(DIFF)
	$(PYTHON) -m isort $(DIFF)
	$(PYTHON) -m black $(DIFF)
reformatblack:
	$(PYTHON) -m black $(DIFF)

# Translations
gettext:
	$(PYTHON) -m redgettext --command-docstrings --verbose --recursive redbot --exclude-files "redbot/pytest/**/*"
