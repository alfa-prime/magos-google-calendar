# 1. BASE
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV LANG=ru_RU.UTF-8 \
    LC_ALL=ru_RU.UTF-8 \
    PYTHONIOENCODING=utf-8 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.12 \
    PATH="/code/.venv/bin:$PATH" \
    PYTHONPATH="/code"

RUN apt-get update && apt-get install -y --no-install-recommends locales \
 micro \
 && sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen \
 && locale-gen ru_RU.UTF-8 \
 && rm -rf /var/lib/apt/lists/*

# Используем /code как корень проекта
WORKDIR /code

# 2. BUILDER
FROM base AS builder
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-cache

# 3. DEVELOPMENT
FROM base AS development
COPY --from=builder /code/.venv /code/.venv

COPY ./app ./app
COPY ./migrations ./migrations
COPY ./alembic.ini ./alembic.ini

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# 4. PRODUCTION
FROM base AS production
COPY --from=builder /code/.venv /code/.venv

COPY ./app ./app
COPY ./migrations ./migrations
COPY ./alembic.ini ./alembic.ini

EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]