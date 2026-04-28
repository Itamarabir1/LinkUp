.PHONY: up down build logs ps restart migrate

COMPOSE=docker compose --env-file backend/.env --env-file frontend/.env

up: ## Start all services
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

build: ## Rebuild and start all services
	$(COMPOSE) up -d --build

logs: ## Follow logs for all services
	$(COMPOSE) logs -f

ps: ## Show status of all services
	$(COMPOSE) ps

restart: ## Restart all services
	$(COMPOSE) restart

migrate: ## Run database migrations
	$(COMPOSE) run --rm migrate
