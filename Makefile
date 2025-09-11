# Makefile for Spandak8s CLI

.PHONY: help install build snap clean test lint format

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-cov black flake8 mypy

build: ## Build Python package
	python setup.py sdist bdist_wheel

snap: clean ## Build Snap package
	@echo "Building Snap package..."
	@if ! command -v snapcraft >/dev/null 2>&1; then \
		echo "Error: snapcraft not installed. Install with: sudo snap install snapcraft --classic"; \
		exit 1; \
	fi
	snapcraft

snap-install: snap ## Install Snap package locally (dangerous mode)
	sudo snap install --dangerous spandak8s_*.snap

snap-clean: ## Clean Snap build artifacts
	snapcraft clean
	rm -f *.snap

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test: ## Run tests
	pytest tests/ -v

test-coverage: ## Run tests with coverage
	pytest tests/ --cov=spandak8s --cov-report=html

lint: ## Run linting
	flake8 spandak8s cmd pkg
	mypy spandak8s cmd pkg

format: ## Format code
	black spandak8s cmd pkg

check: lint test ## Run all checks (lint + test)

# Development workflow
dev-setup: install-dev ## Set up development environment
	@echo "Development environment ready!"
	@echo "Run 'make check' to validate your changes"

# Quick test of CLI installation
test-cli: ## Test CLI installation
	python -m spandak8s --version
	python -m spandak8s --help

# Build and test cycle
ci: clean lint test build ## Full CI pipeline (clean, lint, test, build)

# Release workflow
release: ci ## Prepare release package
	@echo "Release package ready in dist/"
	@echo "Upload to PyPI with: twine upload dist/*"

# Docker development (if needed)
docker-build: ## Build Docker development image
	docker build -t spandak8s-dev .

docker-run: ## Run CLI in Docker container
	docker run -it --rm -v ~/.kube:/root/.kube spandak8s-dev

# Kubernetes testing
k8s-test: ## Test Kubernetes connectivity
	kubectl cluster-info
	kubectl get nodes

# Documentation
docs: ## Generate documentation
	@echo "Documentation available in README.md"
	@echo "For API docs, visit: https://docs.spanda.ai"
