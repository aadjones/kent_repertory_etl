.PHONY: default clean install test lint

# Default target (runs install)
default: install

# Create a fresh virtual environment and install dependencies
install:
	python3.11 -m venv env
	./env/bin/pip install --upgrade pip setuptools wheel
	./env/bin/pip install -r requirements.txt
	./env/bin/pip install -e .
	@echo "Virtual environment created. Run 'source env/bin/activate' to activate it."

# Remove build artifacts and caches, including the virtual environment
clean:
	rm -rf env __pycache__ *.egg-info build dist
	@echo "Virtual environment and build artifacts removed."

# Run tests using pytest
test:
	./env/bin/pytest

# Run linters and formatters
lint:
	./env/bin/flake8 .
	./env/bin/black --check .
	./env/bin/isort --check-only .
