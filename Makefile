COMPOSE_DEV = docker compose -f docker-compose.dev.yml
COMPOSE_PROD = docker compose -f docker-compose.prod.yml

.PHONY: up-dev down-dev logs-dev up-prod down-prod check format migrations migrate clean-dev

# РАЗРАБОТКА
up-dev:
	$(COMPOSE_DEV) up --build -d

down-dev:
	$(COMPOSE_DEV) down

logs-dev:
	$(COMPOSE_DEV) logs -f app

bash-dev:
	$(COMPOSE_DEV) exec app bash


# удаляет все данные БД (обнулить БД)
clean-dev:
	$(COMPOSE_DEV) down -v

# МИГРАЦИИ (ALEMBIC) только для DEV окружения
# Создать файл миграции. Использование: make migrations name=initial
migrations:
	$(COMPOSE_DEV) exec app uv run alembic revision --autogenerate -m "$(name)"

# Применить миграции вручную
migrate:
	$(COMPOSE_DEV) exec app uv run alembic upgrade head

# Посмотреть историю миграций
migration-history:
	$(COMPOSE_DEV) exec app uv run alembic history --verbose


# ПРОДАКШЕН
up-prod:
	$(COMPOSE_PROD) up --build -d

down-prod:
	$(COMPOSE_PROD) down

logs-prod:
	$(COMPOSE_PROD) logs -f app

bash-prod:
	$(COMPOSE_PROD) exec app bash

# удаляет все данные БД (обнулить БД)
clean-prod:
	$(COMPOSE_PROD) down -v

clean:
	docker system prune -a --volumes -f


# КАЧЕСТВО КОДА
check:
	ruff check .

format:
	ruff format .

# Сборка проекта для LLM
to-llm:
	files-to-prompt . -m > to_llm.md