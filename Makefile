.PHONY: install test test-cov lint format run clean

install:
	pip install -e ".[dev]"

test:
	pytest

test-cov:
	pytest --cov=wfc --cov-report=term-missing

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

run:
	python -m wfc --help

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
