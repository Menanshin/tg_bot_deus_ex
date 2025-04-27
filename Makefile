install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

format:
	black .
	isort .

lint:
	flake8 .
	mypy .

test:
	pytest tests/