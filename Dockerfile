FROM python:3.12-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip --no-cache-dir install --upgrade pip && \
    pip --no-cache-dir install -r requirements.txt

COPY src .
CMD ["python", "-m", "quoth", "-c", "config/config.yaml"]
