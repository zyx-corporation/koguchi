.PHONY: docs test lint typecheck quality

docs:
	PYTHONPATH=src python3 -m pdoc koguchi -o docs/api
	@echo "Docs generated at docs/api/index.html"

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

typecheck:
	mypy src/

quality: lint test typecheck
	@echo "All quality checks passed!"
