FROM python:3.9-slim as base

FROM base as app

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY src/ /app
WORKDIR /app

FROM base as dev

COPY requirements-dev.txt /
RUN pip install -r requirements-dev.txt

COPY src/ /app
WORKDIR /app
