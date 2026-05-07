.PHONY: render-pgbouncer-userlist up down build logs ps restart migrate admin-check admin-grant admin-revoke openapi

# Secrets and DB/Redis/RabbitMQ passwords: single source of truth — backend/.env
COMPOSE=docker compose --env-file backend/.env

render-pgbouncer-userlist: ## Regenerate infrastructure/pgbouncer/userlist.txt from backend/.env
	bash "$(CURDIR)/scripts/ops/render-pgbouncer-userlist.sh"

up: render-pgbouncer-userlist ## Start all services (refreshes pgbouncer userlist first)
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

build: render-pgbouncer-userlist ## Rebuild and start all services
	$(COMPOSE) up -d --build

logs: ## Follow logs for all services
	$(COMPOSE) logs -f

ps: ## Show status of all services
	$(COMPOSE) ps

restart: render-pgbouncer-userlist ## Recreate pgbouncer (fresh env + userlist), then restart stack
	$(COMPOSE) up -d --no-deps --force-recreate pgbouncer
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

openapi: ## Export OpenAPI schema from FastAPI and regenerate the frontend client
	cd backend && uv run python scripts/export_openapi.py --out ../frontend/openapi-snapshot.json
	cd frontend && npm run gen:api
	@echo "Done. Review changes in frontend/src/api/generated/ and commit them."
