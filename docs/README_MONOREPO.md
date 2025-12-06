# 🌐 Pangea Network - Distributed AI Infrastructure

**Production-Grade Polyglot Monorepo**

[![Status](https://img.shields.io/badge/status-production--ready-brightgreen)](.)
[![Languages](https://img.shields.io/badge/languages-Go%20|%20Rust%20|%20Python-blue)](.)
[![Testing](https://img.shields.io/badge/testing-E2E%20Automated-success)](.)

---

## 📖 Quick Navigation

### 🚀 Getting Started

- **First Time?** → [Quick Start Guide](#quick-start)
- **Full Documentation** → [`MONOREPO_STRUCTURE.md`](MONOREPO_STRUCTURE.md)
- **Architecture** → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

### 📦 Project Structure

```
/services/          # Microservices (Go, Rust, Python)
/libraries/         # Shared schemas (Cap'n Proto)
/infra/            # Docker compose & infrastructure
/docs/             # Documentation
Makefile           # Build commands
setup.sh           # E2E test automation
```

---

## Quick Start

### Prerequisites

```bash
# Install Cap'n Proto compiler
brew install capnproto

# Verify Docker is running
docker --version
docker-compose --version
```

### One-Command Setup

```bash
# From project root
chmod +x setup.sh
./setup.sh
```

This automated script:
1. ✅ Validates environment (Docker, disk space, etc.)
2. ✅ Creates test data
3. ✅ Builds Docker images for all 3 services
4. ✅ Deploys services (`docker-compose up`)
5. ✅ Runs E2E distributed test suite
6. ✅ Streams logs from all services
7. ✅ Cleans up gracefully

### Manual Step-by-Step

```bash
# 1. Generate Cap'n Proto schemas (REQUIRED FIRST)
make schema-gen

# 2. Build all services
make build

# 3. Start containerized environment
docker-compose -f infra/docker-compose.yaml up -d

# 4. Run E2E tests
make e2e-test

# 5. View live logs
make logs

# 6. Stop services
make docker-down
```

### Makefile Command Reference

```bash
make help              # Show all available commands
make schema-gen        # Generate Cap'n Proto bindings (FIRST STEP)
make build            # Build all services
make test             # Run all unit tests
make docker-build     # Build Docker images
make docker-up        # Start services
make docker-down      # Stop services
make e2e-test         # Run distributed test suite
make clean            # Remove artifacts
make logs             # Stream all service logs
```

---

## 🏗️ Architecture Overview

### Three Microservices

#### 1. **Go Orchestrator** (`/services/go-orchestrator`)
- **Role:** Central RPC server, gradient aggregation, node coordination
- **Responsibilities:** 
  - Accept connections from workers
  - Aggregate gradients across workers
  - Distribute model parameters
  - Manage training synchronization
- **Technology:** Go 1.24+
- **Port:** 8080

#### 2. **Rust Compute Core** (`/services/rust-compute`)
- **Role:** High-performance data preprocessing and serialization
- **Responsibilities:**
  - Receive raw data from sources
  - Preprocess and split data for workers
  - Serialize to Cap'n Proto format (zero-copy)
  - Measure and report performance metrics
- **Technology:** Rust 1.84+
- **Port:** 9090

#### 3. **Python AI Service** (`/services/python-ai-client`)
- **Role:** ML model training, gradient computation, synchronization
- **Responsibilities:**
  - Connect to Rust Compute Core for data
  - Perform zero-copy Cap'n Proto deserialization
  - Execute training iterations (PyTorch/TensorFlow)
  - Compute gradients
  - Synchronize with Go Orchestrator
- **Technology:** Python 3.11+
- **Port:** Uses orchestrator & compute ports

### Data Flow

```
Raw Data
   ↓
[Rust Compute] ← Preprocesses & serializes to Cap'n Proto
   ↓
[Python AI Service] ← Zero-copy ingestion, training, gradient computation
   ↓
[Go Orchestrator] ← Gradient aggregation, parameter synchronization
   ↓
Updated Parameters → Distributed back to all workers
```

### Shared Cap'n Proto Schemas

**Location:** `/libraries/schemas/tensor.capnp`

All services communicate using Cap'n Proto for:
- ✅ Language-agnostic data contracts
- ✅ Zero-copy serialization
- ✅ Type-safe RPC messages
- ✅ Single source of truth

**Schemas generated for:** Go, Rust, Python (automatically via `make schema-gen`)

---

## 📋 Service Specifications

### /services/go-orchestrator

```go
// Entry point: main.go
// Package: pkg/gradient/manager.go
// Dependencies: go.mod

type Orchestrator struct {
    config          *OrchestratorConfig
    listener        net.Listener
    gradientManager *gradient.Manager
}

// Manages:
// - RPC server lifecycle
// - Gradient submission and aggregation
// - Worker synchronization
// - Graceful shutdown
```

**Build:**
```bash
cd services/go-orchestrator && go build -o bin/go-orchestrator main.go
```

### /services/rust-compute

```rust
// Entry point: src/main.rs
// Module: src/data_processing.rs
// Dependencies: Cargo.toml

pub struct Preprocessor {
    num_workers: usize,
    chunk_size: usize,
}

// Provides:
// - Parallel data distribution (Rayon)
// - Cap'n Proto serialization
// - Performance metrics
// - Zero-copy operations
```

**Build:**
```bash
cd services/rust-compute && cargo build --release
```

### /services/python-ai-client

```python
# Entry point: app/main.py
# Module: app/training_core.py
# Tests: tests/run_e2e_test.py
# Dependencies: requirements.txt

class TrainingEngine:
    def ingest_and_train_step(self, batch_data):
        """Zero-copy Cap'n Proto ingestion and training"""
        # Deserialize batch
        # Run training iteration
        # Compute gradients
        # Sync with orchestrator
        pass
```

**Build:**
```bash
cd services/python-ai-client && pip install -r requirements.txt
```

---

## 🧪 Testing

### Automated E2E Test

```bash
./setup.sh
```

### Manual Test Execution

```bash
# Start services
docker-compose -f infra/docker-compose.yaml up -d

# Run Python E2E test
docker exec python-worker-1 python tests/run_e2e_test.py

# Run individual service tests
cd services/go-orchestrator && go test ./...
cd services/rust-compute && cargo test --release
cd services/python-ai-client && python -m pytest tests/ -v
```

### Test Suite Coverage

- ✅ TrainingEngine initialization
- ✅ Zero-copy data ingestion
- ✅ Training step execution
- ✅ Gradient computation
- ✅ Orchestrator synchronization
- ✅ End-to-end distributed flow

---

## 📁 Project Layout

```
/
├── services/
│   ├── go-orchestrator/
│   │   ├── main.go
│   │   ├── go.mod
│   │   ├── Dockerfile
│   │   └── pkg/gradient/
│   ├── rust-compute/
│   │   ├── src/main.rs
│   │   ├── src/data_processing.rs
│   │   ├── Cargo.toml
│   │   └── Dockerfile
│   └── python-ai-client/
│       ├── app/main.py
│       ├── app/training_core.py
│       ├── tests/run_e2e_test.py
│       ├── requirements.txt
│       └── Dockerfile
├── libraries/
│   └── schemas/
│       ├── tensor.capnp          ← Single source of truth
│       ├── go/                   ← Auto-generated
│       ├── rust/                 ← Auto-generated
│       └── python/               ← Auto-generated
├── infra/
│   └── docker-compose.yaml       ← Local dev environment
├── docs/                         ← Documentation
├── Makefile                      ← Build commands
├── setup.sh                      ← E2E test automation
└── README.md                     ← This file
```

---

## 🔧 Configuration

### Environment Variables

Services read configuration from environment variables set in `docker-compose.yaml`:

```yaml
# Go Orchestrator
NODE_ID=1
RPC_ADDR=0.0.0.0:8080

# Rust Compute
LISTEN=0.0.0.0:9090
WORKERS=4
CHUNK_SIZE=32

# Python AI Service
WORKER_ID=1
ORCHESTRATOR_HOST=go-orchestrator
ORCHESTRATOR_PORT=8080
COMPUTE_HOST=rust-compute
COMPUTE_PORT=9090
```

### Customization

Edit `infra/docker-compose.yaml` to:
- Change ports
- Add environment variables
- Add volumes for data persistence
- Modify resource limits

---

## 🐛 Troubleshooting

### "capnp: command not found"
```bash
brew install capnproto
```

### "Port already in use"
```bash
# Change ports in docker-compose.yaml
# Or kill the process:
lsof -i :8080 && kill -9 <PID>
```

### "Services can't communicate"
```bash
# Verify networking
docker exec python-worker-1 ping rust-compute

# Check docker-compose.yaml for correct hostnames
grep hostname infra/docker-compose.yaml
```

### "E2E tests fail"
```bash
# Check logs
cat test_e2e.log

# View service logs
docker-compose -f infra/docker-compose.yaml logs
```

See [`MONOREPO_STRUCTURE.md`](MONOREPO_STRUCTURE.md) for comprehensive troubleshooting.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [`MONOREPO_STRUCTURE.md`](MONOREPO_STRUCTURE.md) | **⭐ Complete guide** - Structure, design, workflows |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architecture details and design decisions |
| Service READMEs | Individual service documentation |
| Code comments | Inline documentation and examples |

---

## 🚀 Deployment

### Local Development
```bash
docker-compose -f infra/docker-compose.yaml up
```

### Production with Kubernetes
1. Build images with `make docker-build`
2. Push to registry
3. Deploy using Kubernetes manifests
4. Scale services independently

### Health Checks

Each service includes health checks:
```bash
# View health status
docker-compose -f infra/docker-compose.yaml ps

# Test manually
curl http://localhost:8080/health          # Go Orchestrator
nc -z localhost 9090                       # Rust Compute
docker exec python-worker-1 python -c "..." # Python
```

---

## 🤝 Contributing

1. **Schema changes:** Update `/libraries/schemas/tensor.capnp`, run `make schema-gen`
2. **New services:** Create in `/services/<name>`, add to `Makefile` and `docker-compose.yaml`
3. **Bug fixes:** Submit to relevant service directory
4. **Tests:** Add to service test directory, verify with `make test`

---

## 📝 License

[Your License Here]

---

## 🆘 Support

- **Issues:** [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation:** [`MONOREPO_STRUCTURE.md`](MONOREPO_STRUCTURE.md)
- **Quick Help:** Run `make help`

---

**Last Updated:** December 2025  
**Version:** 1.0  
**Status:** Production Ready ✅
