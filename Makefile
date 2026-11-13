PYTHON ?= .venv/bin/python
PROJECT ?= projects/water-crisis
PROFILE ?= preview

.PHONY: doctor validate storyboard preview render assemble build test lint typecheck
doctor:
	$(PYTHON) -m studio.cli doctor
validate:
	$(PYTHON) -m studio.cli validate $(PROJECT)
storyboard:
	$(PYTHON) -m studio.cli storyboard $(PROJECT)
preview:
	$(PYTHON) -m studio.cli preview $(PROJECT)
render:
	$(PYTHON) -m studio.cli render $(PROJECT) --profile $(PROFILE)
assemble:
	$(PYTHON) -m studio.cli assemble $(PROJECT) --profile $(PROFILE)
build:
	$(PYTHON) -m studio.cli build $(PROJECT) --profile $(PROFILE)
test:
	$(PYTHON) -m pytest -q
lint:
	$(PYTHON) -m ruff check studio tests
typecheck:
	$(PYTHON) -m mypy
