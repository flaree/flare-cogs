PYTHON ?= python3.8

# Python Code Style
reformat:
	$(PYTHON) -m black -l 99 `git ls-files "*.py"`
stylecheck:
	$(PYTHON) -m black -l 99 --check `git ls-files "*.py"`
stylediff:
	$(PYTHON) -m black -l 99 --check --diff `git ls-files "*.py"`

# Translations
gettext:
	$(PYTHON) -m redgettext --command-docstrings --verbose --recursive redbot --exclude-files "redbot/pytest/**/*"
