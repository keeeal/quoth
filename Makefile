build:
	docker compose build bot

up:
	docker compose up data bot

install-dev:
	pip --no-cache-dir install --upgrade pip && \
    pip --no-cache-dir install -r requirements-dev.txt

format:
	isort $(if $(check),--check,) --profile black src tests && \
	black $(if $(check),--check,) src tests

lint:
	mypy --check-untyped-defs src tests

test:
	pytest tests

lock:
	pip-compile --verbose --upgrade \
		--output-file requirements.txt \
		pyproject.toml
	pip-compile --verbose --upgrade --extra dev \
		--output-file requirements-dev.txt \
		pyproject.toml

clean:
	git clean -Xdf
