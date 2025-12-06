.PHONY: help schema-gen build test clean docker-build docker-up docker-down e2e-test setup teardown

# Default target
help:
	@echo "WGT Monorepo - Production-Grade Polyglot Build System"
	@echo "===================================================="
	@echo ""
	@echo "Available targets:"
	@echo "  make schema-gen      - Generate Cap'n Proto bindings for all languages (REQUIRED FIRST STEP)"
	@echo "  make build           - Build all services (Go, Rust, Python)"
	@echo "  make test            - Run tests for all services"
	@echo "  make clean           - Clean all build artifacts and generated files"
	@echo "  make docker-build    - Build Docker images for all services"
	@echo "  make docker-up       - Start containerized environment with docker-compose"
	@echo "  make docker-down     - Stop and remove containers"
	@echo "  make e2e-test        - Run end-to-end distributed test suite"
	@echo "  make setup           - Complete setup and environment initialization"
	@echo "  make teardown        - Clean shutdown of all services"
	@echo ""

# ============================================================
# SCHEMA GENERATION - MANDATORY FIRST STEP
# ============================================================
schema-gen: check-capnp
	@echo "🔗 Generating Cap'n Proto bindings from single source of truth..."
	@echo "   Source: /libraries/schemas/tensor.capnp"
	@echo ""
	
	@echo "   [1/3] Generating Go bindings..."
	@mkdir -p libraries/schemas/go
	capnp compile -o go:libraries/schemas/go libraries/schemas/tensor.capnp
	@echo "   ✓ Go bindings generated at /libraries/schemas/go"
	@echo ""
	
	@echo "   [2/3] Generating Rust bindings..."
	@mkdir -p libraries/schemas/rust
	capnp compile -o rust:libraries/schemas/rust libraries/schemas/tensor.capnp
	@echo "   ✓ Rust bindings generated at /libraries/schemas/rust"
	@echo ""
	
	@echo "   [3/3] Generating Python bindings..."
	@mkdir -p libraries/schemas/python
	capnp compile -o python:libraries/schemas/python libraries/schemas/tensor.capnp
	@echo "   ✓ Python bindings generated at /libraries/schemas/python"
	@echo ""
	
	@echo "✅ Schema generation complete! All services now have synchronized bindings."
	@echo ""

check-capnp:
	@command -v capnp >/dev/null 2>&1 || { echo "❌ capnp compiler not found. Install with: brew install capnproto"; exit 1; }

# ============================================================
# SERVICE BUILD TARGETS
# ============================================================
build: schema-gen build-go build-rust build-python
	@echo "✅ All services built successfully!"

build-go: schema-gen
	@echo "🔨 Building Go Orchestrator..."
	cd services/go-orchestrator && go build -o bin/go-orchestrator main.go
	@echo "✓ Go Orchestrator built"

build-rust: schema-gen
	@echo "🔨 Building Rust Compute Core..."
	cd services/rust-compute && cargo build --release
	@echo "✓ Rust Compute Core built"

build-python: schema-gen
	@echo "🔨 Building Python AI Service..."
	cd services/python-ai-client && pip install -r requirements.txt
	@echo "✓ Python dependencies installed"

# ============================================================
# TESTING TARGETS
# ============================================================
test: test-go test-rust test-python
	@echo "✅ All unit tests passed!"

test-go:
	@echo "🧪 Running Go tests..."
	cd services/go-orchestrator && go test ./...
	@echo "✓ Go tests passed"

test-rust:
	@echo "🧪 Running Rust tests..."
	cd services/rust-compute && cargo test --release
	@echo "✓ Rust tests passed"

test-python:
	@echo "🧪 Running Python tests..."
	cd services/python-ai-client && python -m pytest tests/ -v
	@echo "✓ Python tests passed"

# ============================================================
# DOCKER TARGETS
# ============================================================
docker-build: schema-gen
	@echo "🐳 Building Docker images..."
	docker-compose -f infra/docker-compose.yaml build
	@echo "✓ Docker images built"

docker-up:
	@echo "🚀 Starting containerized environment..."
	docker-compose -f infra/docker-compose.yaml up -d
	@echo "✓ Services running in background"
	@echo ""
	@echo "Active services:"
	docker-compose -f infra/docker-compose.yaml ps
	@echo ""

docker-down:
	@echo "🛑 Stopping containerized environment..."
	docker-compose -f infra/docker-compose.yaml down
	@echo "✓ All services stopped and removed"

# ============================================================
# END-TO-END TESTING
# ============================================================
e2e-test: docker-up
	@echo "🧪 Running end-to-end distributed test..."
	@sleep 3  # Allow services to initialize
	docker exec python-worker-1 python /services/python-ai-client/tests/run_e2e_test.py
	@echo ""
	@echo "📋 Streaming logs from services..."
	@docker-compose -f infra/docker-compose.yaml logs -f &
	@sleep 30
	@docker-compose -f infra/docker-compose.yaml stop

# ============================================================
# ENVIRONMENT SETUP & TEARDOWN
# ============================================================
setup: schema-gen docker-build docker-up
	@echo "✅ Complete setup successful!"
	@echo ""
	@echo "Environment ready. Services running:"
	docker-compose -f infra/docker-compose.yaml ps
	@echo ""
	@echo "Next steps:"
	@echo "  - View logs: docker-compose -f infra/docker-compose.yaml logs -f"
	@echo "  - Run tests: make e2e-test"
	@echo "  - Shutdown: make teardown"

teardown: docker-down
	@echo "✅ Teardown complete"

# ============================================================
# CLEANUP
# ============================================================
clean:
	@echo "🧹 Cleaning build artifacts..."
	cd services/go-orchestrator && rm -rf bin/
	cd services/rust-compute && cargo clean
	cd services/python-ai-client && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf libraries/schemas/go/*.go
	rm -rf libraries/schemas/rust/*.rs
	rm -rf libraries/schemas/python/*.py
	@echo "✓ Cleanup complete"

# ============================================================
# DEVELOPMENT HELPERS
# ============================================================
logs:
	docker-compose -f infra/docker-compose.yaml logs -f

logs-go:
	docker-compose -f infra/docker-compose.yaml logs -f go-orchestrator

logs-rust:
	docker-compose -f infra/docker-compose.yaml logs -f rust-compute

logs-python:
	docker-compose -f infra/docker-compose.yaml logs -f python-worker-1

shell-go:
	docker exec -it go-orchestrator /bin/sh

shell-rust:
	docker exec -it rust-compute /bin/sh

shell-python:
	docker exec -it python-worker-1 /bin/bash

.SILENT: help
