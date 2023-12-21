build:
	docker compose build bot

up:
	docker compose up data bot

test:
	docker compose run dev pytest tests

format:
	docker compose run dev sh -c \
		"isort --profile black . && black ."

check-format:
	docker compose run dev sh -c \
		"isort --profile black --check . && black --check ."

check-types:
	docker compose run dev mypy --check-untyped-defs .

requirements:
	docker compose run dev pip-compile \
		--verbose \
		--upgrade \
		--output-file requirements.txt \
		pyproject.toml
	docker compose run dev pip-compile \
		--verbose \
		--upgrade \
		--extra dev \
		--output-file requirements-dev.txt \
		pyproject.toml

clean:
	git clean -Xdf
