FROM python:3.11-slim as base

WORKDIR /app

FROM base as app

COPY requirements.txt .
RUN pip --no-cache-dir install --upgrade pip && \
    pip --no-cache-dir install -r requirements.txt

COPY src .
CMD ["python", "-m", "quoth", "-c", "config/config.yaml"]

FROM base as dev

COPY requirements-dev.txt .
RUN pip --no-cache-dir install --upgrade pip && \
    pip --no-cache-dir install -r requirements-dev.txt
