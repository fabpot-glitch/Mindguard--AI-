.PHONY: help install train test run docker-build docker-up clean lint format

help:
	@echo "MindGuard AI - Makefile Commands"
	@echo "================================"
	@echo "make install     - Install dependencies"
	@echo "make train       - Train the model"
	@echo "make test        - Run tests"
	@echo "make run         - Run the application"
	@echo "make docker-build - Build Docker images"
	@echo "make docker-up   - Start Docker containers"
	@echo "make clean       - Clean temporary files"
	@echo "make lint        - Run linters"
	@echo "make format      - Format code"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

train:
	python -m models.train

test:
	pytest tests/ -v --cov=. --cov-report=term-missing

run:
	python main.py

docker-build:
	docker-compose -f deployment/docker/docker-compose.yml build

docker-up:
	docker-compose -f deployment/docker/docker-compose.yml up -d

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov

lint:
	flake8 .
	mypy .

format:
	black .
	isort .