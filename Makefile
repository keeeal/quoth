build:
	docker compose build

run:
	docker compose up quothbot

lock:
	pip install -Uq pip pip-tools; \
	pip-compile -v -o requirements.txt \
		--resolver backtracking\
		--generate-hashes \
		--no-emit-index-url \
		--upgrade \
		pyproject.toml
	pip-compile -v -o requirements-dev.txt \
		--resolver backtracking\
		--generate-hashes \
		--no-emit-index-url \
		--upgrade \
		--extra dev \
		pyproject.toml
