.PHONY: up down build logs ps restart migrate admin-check admin-grant admin-revoke

# Secrets and DB/Redis/RabbitMQ passwords: single source of truth — backend/.env
COMPOSE=docker compose --env-file backend/.env

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

admin-check: ## Check admin flag by email: make admin-check EMAIL=user@example.com
	@test -n "$(EMAIL)" || (echo "ERROR: EMAIL is required. Usage: make admin-check EMAIL=user@example.com"; exit 1)
	$(COMPOSE) exec -T db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT user_id, email, is_admin FROM users WHERE lower(email)=lower('\''$(EMAIL)'\'' );"'

admin-grant: ## Grant admin by email: make admin-grant EMAIL=user@example.com
	@test -n "$(EMAIL)" || (echo "ERROR: EMAIL is required. Usage: make admin-grant EMAIL=user@example.com"; exit 1)
	$(COMPOSE) exec -T db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "UPDATE users SET is_admin = TRUE WHERE lower(email)=lower('\''$(EMAIL)'\'' );"'
	$(MAKE) admin-check EMAIL="$(EMAIL)"

admin-revoke: ## Revoke admin by email: make admin-revoke EMAIL=user@example.com
	@test -n "$(EMAIL)" || (echo "ERROR: EMAIL is required. Usage: make admin-revoke EMAIL=user@example.com"; exit 1)
	$(COMPOSE) exec -T db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "UPDATE users SET is_admin = FALSE WHERE lower(email)=lower('\''$(EMAIL)'\'' );"'
	$(MAKE) admin-check EMAIL="$(EMAIL)"
