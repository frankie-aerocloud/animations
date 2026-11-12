PYTHON ?= .venv/bin/python
PROJECT ?= world-runs-out-of-water
PROFILE ?= preview

.PHONY: doctor validate quality-test render-film test lint typecheck
doctor:
	$(PYTHON) studio.py doctor
validate:
	$(PYTHON) studio.py validate $(PROJECT)
quality-test:
	$(PYTHON) studio.py quality-test --profile $(PROFILE)
render-film:
	$(PYTHON) studio.py render-film $(PROJECT) --profile $(PROFILE)
test:
	$(PYTHON) -m pytest
lint:
	$(PYTHON) -m ruff check studio.py studio tests
typecheck:
	$(PYTHON) -m mypy studio
