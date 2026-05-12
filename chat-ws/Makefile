.PHONY: help run-go run-ai run-all install-ai test-go clean

help: ## הצג עזרה
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install-ai: ## התקן תלויות Python ל-AI service
	cd ai && pip install -r requirements.txt

run-go: ## הרץ שרת Go WebSocket
	@echo "🚀 Starting Go WebSocket server..."
	go run cmd/server/main.go

run-ai: ## הרץ שירות ניתוח AI (Python)
	@echo "🤖 Starting AI Analyzer service..."
	cd ai && python -m service.chat_analyzer_service

run-all: ## הרץ את שני ה-services במקביל (דורש Redis)
	@echo "🚀 Starting both services..."
	@echo "⚠️  Make sure Redis is running!"
	@trap 'kill 0' EXIT; \
	make -j2 run-go run-ai

test-go: ## הרץ בדיקות Go
	go test -race -count=1 ./...

test-cover: ## הרץ בדיקות Go עם כיסוי קוד
	go test -race -coverprofile=coverage.out ./...
	go tool cover -func=coverage.out

clean: ## נקה קבצים זמניים
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
