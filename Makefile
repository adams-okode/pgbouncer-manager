# PgBouncer Manager Makefile

.PHONY: help build server cli ui docker docker-build docker-run docker-stop docker-clean

help:
	@echo "PgBouncer Manager"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  build      Build all components (server + UI)"
	@echo "  server     Build only the Go server"
	@echo "  cli        Build only the CLI tool"
	@echo "  ui         Build only the React UI"
	@echo "  docker     Build Docker image"
	@echo "  docker-run Run Docker container"
	@echo "  docker-stop Stop Docker container"
	@echo "  clean      Clean build artifacts"
	@echo "  dev        Run development server (UI only)"

server:
	@echo "Building Go server..."
	go build -o bin/server ./cmd/server/main.go

cli:
	@echo "Building CLI tool..."
	go build -o bin/cli ./cmd/cli/main.go

ui:
	@echo "Building React UI..."
	@cd ui && npm ci && npm run build

build: server ui

docker-build:
	@echo "Building Docker image..."
	docker build -t pgbouncer-manager:latest .

docker-run: docker-build
	@echo "Starting PgBouncer Manager..."
	@docker run -d --name pgbouncer-manager \
		-p 3000:3000 \
		-e CONFIG_DIR=/app/config \
		-e ENCRYPTION_KEY=$$ENCRYPTION_KEY \
		-v $$(pwd)/pgbouncer/config:/app/config:ro \
		pgbouncer-manager:latest

docker-stop:
	@echo "Stopping PgBouncer Manager..."
	@docker stop pgbouncer-manager || true
	@docker rm pgbouncer-manager || true

docker-clean: docker-stop
	@echo "Cleaning Docker artifacts..."
	@docker rmi pgbouncer-manager:latest || true

clean:
	@echo "Cleaning build artifacts..."
	rm -rf bin/
	rm -rf ui/dist/
	go clean -cache

dev:
	@echo "Starting development environment..."
	@cd ui && npm run dev

# Test targets
test:
	@echo "Running tests..."
	go test -v ./...

test-cover:
	@echo "Running tests with coverage..."
	go test -v -coverprofile=coverage.out ./...
	go tool cover -func=coverage.out

lint:
	@echo "Running linter..."
	golangci-lint run

# Database migrations (if needed)
migrate-up:
	@echo "Running migrations..."
alembic upgrade head

migrate-down:
	@echo "Rolling back migrations..."
alembic downgrade -1

migrate-new:
	@echo "Creating new migration..."
	alembic revision --autogenerate -m "$(message)"

# Deployment targets
deploy-local: build
	@echo "Deploying to local environment..."
	./bin/server

deploy-docker: docker-build
	@echo "Deploying to Docker..."
	@docker-compose up -d

deploy-k8s:
	@echo "Deploying to Kubernetes..."
	kubectl apply -f k8s/

# Helper targets
env:
	@echo "Creating .env file..."
	@test -f .env || cp .env.example .env
	@echo "Generated ENCRYPTION_KEY:"
	@openssl rand -base64 32
	@echo "Add this to your .env file."
