# 🌲 PANGEA MONOREPO - PRODUCTION-GRADE STRUCTURE GUIDE

**Version:** 1.0  
**Status:** Complete  
**Last Updated:** December 2025

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Part 1: Repository Root Structure](#part-1-repository-root-structure)
3. [Part 2: Shared Schema Management](#part-2-shared-schema-management)
4. [Part 3: Service-Level Organization](#part-3-service-level-organization)
5. [Part 4: Cross-Device Testing Environment](#part-4-cross-device-testing-environment)
6. [Quick Start Guide](#quick-start-guide)
7. [Development Workflows](#development-workflows)
8. [Troubleshooting](#troubleshooting)
9. [Design Principles](#design-principles)

---

## Overview

This document describes the production-grade, polyglot monorepo structure for **Pangea Network**, housing:

- **Go Orchestrator** (`/services/go-orchestrator`) - RPC server, gradient aggregation, node coordination
- **Rust Compute Core** (`/services/rust-compute`) - High-performance data preprocessing, serialization
- **Python AI Service** (`/services/python-ai-client`) - Zero-copy training, PyTorch/TensorFlow integration

The structure enforces:
- ✅ **Clear separation of concerns** - Independent service deployment and scaling
- ✅ **Automated tooling** - Centralized Makefile for consistent build/test/deploy commands
- ✅ **Single source of truth** - Shared Cap'n Proto schemas in `/libraries/schemas`
- ✅ **E2E testing** - Containerized environment with automated verification
- ✅ **No path issues** - Absolute paths and proper dependency management

---

## Part 1: Repository Root Structure

### Directory Layout

```
/
├── /services/                 # 📦 Independently deployable microservices
│   ├── /go-orchestrator/      # Go RPC server
│   ├── /rust-compute/         # Rust compute core
│   └── /python-ai-client/     # Python AI service
├── /libraries/                # 🔗 Shared code and schemas
│   └── /schemas/              # Cap'n Proto single source of truth
├── /infra/                    # 🧪 Infrastructure definitions
│   └── docker-compose.yaml    # Local dev environment
├── /docs/                     # 📚 Documentation (existing)
├── /tests/                    # 🧪 Integration tests (existing)
├── README.md                  # 📖 Project entry point
├── Makefile                   # ⚙️ Centralized build commands
├── setup.sh                   # 🚀 E2E test automation script
└── .gitignore                 # Git exclusion rules
```

### Root-Level Files

#### **README.md** (Project Entry Point)

Purpose: Main documentation and quick-start guide  
Role: Directs users to appropriate documentation and setup steps

```markdown
# Pangea Network - Distributed AI Infrastructure

**Setup:** See [Quick Start](#quick-start) below  
**Contributing:** See [DEVELOPMENT.md](DEVELOPMENT.md)  
**Architecture:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Go 1.24+, Rust 1.84+, Python 3.11+
- Cap'n Proto compiler: `brew install capnproto`

### One-Command Setup
```bash
# Build, deploy, and test everything
./setup.sh
```

### Manual Setup
```bash
# Generate all schemas
make schema-gen

# Build all services
make build

# Run in containers
make docker-up

# Execute E2E tests
make e2e-test
```
```

#### **Makefile** (Centralized Command Hub)

Purpose: Language-agnostic, unified interface for build/test/deploy  
Guarantees: Consistent workflow across all languages

Key Targets:
- `make schema-gen` - **MANDATORY FIRST STEP** - Generates bindings for Go/Rust/Python
- `make build` - Builds all services (after schema generation)
- `make test` - Runs unit tests for all services
- `make docker-build` - Creates Docker images
- `make docker-up` - Starts containerized environment
- `make e2e-test` - Runs distributed test suite
- `make clean` - Removes generated files and artifacts

**Implementation Details:**

```makefile
schema-gen: check-capnp
	@echo "🔗 Generating Cap'n Proto bindings..."
	capnp compile -o go:libraries/schemas/go libraries/schemas/tensor.capnp
	capnp compile -o rust:libraries/schemas/rust libraries/schemas/tensor.capnp
	capnp compile -o python:libraries/schemas/python libraries/schemas/tensor.capnp
	@echo "✅ All bindings synchronized from single source"
```

**Critical Guarantee:** All targets that build services first call `schema-gen`, ensuring all code uses synchronized schemas.

#### **setup.sh** (E2E Test Automation)

Purpose: Single entry-point for automated, end-to-end testing  
Runs: Complete pipeline from environment validation to teardown

**Execution Steps:**
1. ✅ Environment validation (Docker, disk space, project structure)
2. ✅ Test data creation
3. ✅ Docker image building
4. ✅ Service deployment (`docker-compose up`)
5. ✅ E2E test execution (`python /services/python-ai-client/tests/run_e2e_test.py`)
6. ✅ Live log streaming (60 seconds)
7. ✅ Graceful teardown

**Usage:**
```bash
./setup.sh
```

---

## Part 2: Shared Schema Management

### Directory Structure

```
/libraries/
├── /schemas/
│   ├── tensor.capnp          # 🔐 SINGLE SOURCE OF TRUTH
│   │                         # Contains: Tensor, TrainingBatch, GradientUpdate
│   ├── /go/                  # Go-generated bindings
│   │   └── tensor.capnp.go   # Auto-generated (DO NOT EDIT)
│   ├── /rust/                # Rust-generated bindings
│   │   └── lib.rs            # Auto-generated (DO NOT EDIT)
│   └── /python/              # Python-generated bindings
│       └── tensor_capnp.py   # Auto-generated (DO NOT EDIT)
└── (future) shared utility libraries
```

### tensor.capnp - The Single Source of Truth

**Location:** `/libraries/schemas/tensor.capnp`  
**Content:** Language-agnostic data contracts for distributed communication

```capnp
@0x8ab89e4d39cbedac;

# Core data structures for distributed ML
struct Tensor {
  shape @0 :List(UInt64);      # Tensor dimensions
  dtype @1 :DataType;          # Data type (float32, float64, etc.)
  data @2 :Data;               # Serialized tensor data
}

enum DataType {
  float32 @0;
  float64 @1;
  int32 @2;
  int64 @3;
  uint32 @4;
  uint64 @5;
}

struct TrainingBatch {
  batchId @0 :UInt64;
  samples @1 :List(Tensor);
  labels @2 :Tensor;
  metadata @3 :Text;
}

struct GradientUpdate {
  gradientId @0 :UInt64;
  gradients @1 :List(Tensor);
  loss @2 :Float64;
  timestamp @3 :UInt64;
  nodeId @4 :Text;
}

struct Message {
  messageId @0 :UInt64;
  messageType @1 :MessageType;
  sender @2 :Text;
  recipient @3 :Text;
  payload @4 :Data;
  timestamp @5 :UInt64;
}

enum MessageType {
  request @0;
  response @1;
  gradientSync @2;
  heartbeat @3;
}
```

### Schema Generation Automation

**Mandate:** All schema generation is automated via `make schema-gen`

**Process:**

1. **Pre-condition:** Cap'n Proto compiler must be available
   ```bash
   which capnp  # Verify installation
   ```

2. **Execution:** Single command generates all bindings
   ```bash
   make schema-gen
   ```

3. **Synchronization:** All services are guaranteed to use bindings generated from the **exact same** `tensor.capnp` source

4. **Integration:** Services reference generated bindings:
   - **Go:** Imports from `/libraries/schemas/go`
   - **Rust:** Includes via Cargo.toml path dependency
   - **Python:** Imports from `/libraries/schemas/python`

### Schema Update Workflow

When `tensor.capnp` changes:

1. Edit `/libraries/schemas/tensor.capnp`
2. Run `make schema-gen`
3. All services receive updated bindings automatically
4. Test with `make test` and `make e2e-test`

---

## Part 3: Service-Level Organization

### General Service Structure

Each service follows the same internal organization pattern:

```
/services/<service-name>/
├── src/ or app/              # Source code
├── <lang>-specific files     # go.mod, Cargo.toml, requirements.txt
├── Dockerfile                # Container build instructions
├── README.md                 # Service-specific documentation
└── tests/ or <test-dir>/     # Test files
```

### /services/go-orchestrator

**Purpose:** RPC server, connection manager, gradient synchronization  
**Technology:** Go 1.24+  
**Role in Architecture:** Central coordinator for distributed training

**Directory Structure:**

```
/services/go-orchestrator/
├── main.go                   # RPC server entry point
├── go.mod                    # Module definition
├── go.sum                    # Dependency lock file
├── Dockerfile                # Multi-stage build
├── pkg/
│   └── gradient/
│       └── manager.go        # Gradient aggregation logic
└── README.md
```

**Key Files:**

#### **main.go**

Entry point implementing:
- Server lifecycle (Start, Stop)
- Signal handling (SIGINT, SIGTERM) for graceful shutdown
- Connection acceptance and routing
- Configuration from CLI flags

```go
type Orchestrator struct {
    config          *OrchestratorConfig
    listener        net.Listener
    ctx             context.Context
    cancel          context.CancelFunc
    gradientManager *gradient.Manager
}

func main() {
    // Initialize config from flags
    // Create orchestrator
    // Start RPC server
    // Handle signals for graceful shutdown
}
```

#### **pkg/gradient/manager.go**

Gradient aggregation and synchronization:

```go
type Manager struct {
    mu               sync.RWMutex
    gradients        map[uint32]*GradientUpdate
    aggregationRound uint64
}

func (m *Manager) SubmitGradient(update *GradientUpdate) error
func (m *Manager) AggregateGradients() ([]float64, error)
func (m *Manager) GetAggregationStats() map[string]interface{}
func (m *Manager) Reset()
```

#### **Dockerfile**

Multi-stage build for minimal image size:

```dockerfile
FROM golang:1.24-alpine AS builder
# ... build stage ...

FROM alpine:latest
COPY --from=builder /app/go-orchestrator .
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --retries=3 ...
CMD ["./go-orchestrator", "-rpc-addr", "0.0.0.0:8080"]
```

**Build & Run:**

```bash
# Build
cd /services/go-orchestrator && go build -o bin/go-orchestrator main.go

# Docker
docker build -t pangea-go-orchestrator:latest .
docker run -p 8080:8080 pangea-go-orchestrator:latest
```

---

### /services/rust-compute

**Purpose:** High-performance data preprocessing and serialization  
**Technology:** Rust 1.84+  
**Role in Architecture:** Parallel data distribution to workers

**Directory Structure:**

```
/services/rust-compute/
├── src/
│   ├── main.rs               # RPC server, CLI handler
│   └── data_processing.rs    # Rayon-based preprocessing
├── Cargo.toml                # Rust package manifest
├── Cargo.lock                # Dependency lock
├── Dockerfile                # Container build
└── README.md
```

**Key Files:**

#### **src/data_processing.rs**

High-performance data splitting using Rayon:

```rust
pub struct Preprocessor {
    num_workers: usize,
    chunk_size: usize,
}

impl Preprocessor {
    /// Preprocess and split data using Rayon parallelization
    pub fn preprocess_and_split_data(&self, raw_data: Vec<Vec<f64>>) 
        -> Result<PreprocessResult> {
        // 1. Validates input
        // 2. Uses Rayon thread pool for parallel processing
        // 3. Distributes data across workers
        // 4. Measures performance
        // 5. Returns PreprocessResult
    }

    /// Serialize to Cap'n Proto format
    pub fn serialize_to_capnp(&self, result: &PreprocessResult) 
        -> Result<Vec<u8>>
}
```

**Features:**
- Parallel data distribution using `par_iter()`
- Round-robin worker assignment
- Zero-copy serialization (Cap'n Proto)
- Performance metrics (processing time, split counts)

#### **src/main.rs**

Entry point with CLI argument parsing:

```rust
#[derive(Parser, Debug)]
struct Args {
    #[arg(short, long, default_value = "1")]
    id: u32,
    
    #[arg(short, long, default_value = "0.0.0.0:9090")]
    listen: String,
    
    #[arg(short, long, default_value = "go-orchestrator:8080")]
    orchestrator: String,
    
    #[arg(short, long, default_value = "4")]
    workers: usize,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    // Create preprocessor
    // Start TCP listener
    // Accept and handle connections
}
```

#### **Cargo.toml**

Comprehensive dependency management:

```toml
[dependencies]
tokio = { version = "1.36", features = ["full"] }
rayon = "1.8"
capnp = "0.18"
clap = { version = "4.4", features = ["derive"] }
anyhow = "1.0"
```

#### **Dockerfile**

Multi-stage build with optimized Rust compilation:

```dockerfile
FROM rust:1.84-alpine AS builder
RUN apk add --no-cache musl-dev pkg-config openssl-dev
# ... build release binary ...

FROM alpine:latest
COPY --from=builder /app/target/release/pangea-rust-compute .
EXPOSE 9090
HEALTHCHECK --interval=10s ...
```

**Build & Run:**

```bash
# Build
cd /services/rust-compute && cargo build --release

# Docker
docker build -t pangea-rust-compute:latest .
docker run -p 9090:9090 pangea-rust-compute:latest
```

---

### /services/python-ai-client

**Purpose:** Zero-copy training, gradient computation, synchronization  
**Technology:** Python 3.11+, PyTorch/TensorFlow  
**Role in Architecture:** ML training and gradient generation

**Directory Structure:**

```
/services/python-ai-client/
├── app/
│   ├── main.py               # Service entry point
│   └── training_core.py      # Zero-copy ingestion & training
├── tests/
│   └── run_e2e_test.py       # E2E test suite
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container build
└── README.md
```

**Key Files:**

#### **app/main.py**

Service entry point and orchestration:

```python
def main():
    """Main entry point for Python AI Service."""
    # Configuration
    orchestrator_host = "go-orchestrator"
    compute_host = "rust-compute"
    
    # Initialize TrainingEngine
    engine = TrainingEngine(
        orchestrator_addr=(orchestrator_host, 8080),
        compute_addr=(compute_host, 9090),
        worker_id=1,
    )
    
    # Start training loop
    engine.run()

if __name__ == '__main__':
    main()
```

**Responsibilities:**
- Configuration management (from environment variables)
- TrainingEngine initialization
- Error handling and logging
- Main loop execution

#### **app/training_core.py**

Core training and gradient computation:

```python
class TrainingEngine:
    def __init__(self, orchestrator_addr, compute_addr, worker_id=1):
        # Initialize connections
        # Setup training parameters
        # Create model references
        pass

    def ingest_and_train_step(self, batch_data: np.ndarray) 
        -> Tuple[float, np.ndarray]:
        """
        Zero-copy Cap'n Proto ingestion and training step.
        
        1. Receives Cap'n Proto serialized batch from Rust Compute
        2. Performs zero-copy deserialization (pycapnp)
        3. Executes PyTorch/TensorFlow training iteration
        4. Computes loss and gradients
        5. Returns for synchronization
        """
        # Deserialize batch
        input_tensor = batch_data
        
        # Training step
        loss = model(input_tensor).loss
        gradients = model.backward()
        
        return loss, gradients

    def run(self):
        """Main training loop with gradient synchronization."""
        for epoch in range(self.epochs):
            for batch in get_batches():
                loss, gradients = self.ingest_and_train_step(batch)
                self._sync_gradients(loss, gradients)

    def _sync_gradients(self, loss: float, gradients: np.ndarray):
        """Send gradients to orchestrator for aggregation."""
        # Serialize gradients to Cap'n Proto
        # Send via RPC to go-orchestrator
        # Receive aggregated gradients from other workers
        # Apply parameter updates
        pass
```

**Key Features:**
- Zero-copy Cap'n Proto deserialization via `pycapnp`
- Integration with PyTorch/TensorFlow training
- Gradient computation and synchronization
- Error handling and logging

#### **tests/run_e2e_test.py**

Comprehensive E2E test suite:

```python
def test_training_engine_initialization():
    """Test TrainingEngine initialization."""
    # Create engine instance
    # Verify configuration
    # Assert success

def test_ingest_and_train_step():
    """Test single training step."""
    # Create dummy batch
    # Run training step
    # Verify loss and gradients

def test_distributed_training_flow():
    """Test complete E2E distributed flow."""
    # Initialize engine
    # Simulate data ingestion
    # Execute training step
    # Verify gradient synchronization

def run_all_tests():
    """Run all tests and report results."""
    # Execute each test
    # Collect results
    # Print summary
    # Return exit code
```

**Test Execution:**

```bash
# Local test
python -m pytest tests/

# Docker container test
docker exec python-worker-1 python tests/run_e2e_test.py
```

#### **requirements.txt**

Python dependencies (no version conflicts):

```
pycapnp>=1.0.0           # Cap'n Proto bindings
numpy>=1.24.0            # Array operations
torch>=2.0.0             # PyTorch (optional: tensorflow)
click>=8.1.0             # CLI framework
pyyaml>=6.0              # Configuration
pytest>=7.0.0            # Testing framework
pytest-asyncio>=0.21.0   # Async test support
```

#### **Dockerfile**

Python service containerization:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential gcc g++ git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app ./app
COPY tests ./tests

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "app/main.py"]
```

**Build & Run:**

```bash
# Build
cd /services/python-ai-client && pip install -r requirements.txt

# Docker
docker build -t pangea-python-ai:latest .
docker run pangea-python-ai:latest
```

---

## Part 4: Cross-Device Testing Environment

### /infra/docker-compose.yaml

**Purpose:** Define local development and testing environment  
**Guarantee:** All services discoverable by hostname

**Structure:**

```yaml
version: '3.9'

services:
  go-orchestrator:
    build:
      context: ../services/go-orchestrator
      dockerfile: Dockerfile
    container_name: go-orchestrator
    hostname: go-orchestrator
    ports:
      - "8080:8080"  # Expose to host
    networks:
      - pangea-network
    depends_on: []
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s

  rust-compute:
    build:
      context: ../services/rust-compute
      dockerfile: Dockerfile
    container_name: rust-compute
    hostname: rust-compute
    ports:
      - "9090:9090"
    networks:
      - pangea-network
    depends_on:
      go-orchestrator:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "9090"]
      interval: 10s
      timeout: 5s
      retries: 3

  python-worker-1:
    build:
      context: ../services/python-ai-client
      dockerfile: Dockerfile
    container_name: python-worker-1
    hostname: python-worker-1
    environment:
      - WORKER_ID=1
      - ORCHESTRATOR_HOST=go-orchestrator
      - ORCHESTRATOR_PORT=8080
      - COMPUTE_HOST=rust-compute
      - COMPUTE_PORT=9090
    networks:
      - pangea-network
    depends_on:
      go-orchestrator:
        condition: service_healthy
      rust-compute:
        condition: service_healthy

networks:
  pangea-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

**Key Features:**

1. **Build Contexts:** Relative paths to service directories
   ```yaml
   build:
     context: ../services/go-orchestrator  # Relative to docker-compose.yaml
   ```

2. **Networking:** Default bridge network with service name discovery
   ```
   python-worker-1 → go-orchestrator:8080  (via hostname)
   python-worker-1 → rust-compute:9090     (via hostname)
   ```

3. **Health Checks:** Each service includes health verification
   ```yaml
   healthcheck:
     test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "..."]
     interval: 10s
     timeout: 5s
     retries: 3
   ```

4. **Dependencies:** Services start in correct order
   ```yaml
   depends_on:
     go-orchestrator:
       condition: service_healthy  # Wait for health check
   ```

### setup.sh - E2E Test Automation

**Location:** `/setup.sh` (at project root)  
**Executable:** `chmod +x /setup.sh`

**Complete Execution Flow:**

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Environment Validation                          │
│ ✓ Docker installed                                      │
│ ✓ Docker Compose installed                              │
│ ✓ Docker daemon running                                 │
│ ✓ Project structure verified                            │
│ ✓ Disk space sufficient (>2GB)                          │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Test Data Setup                                 │
│ ✓ Create test_media/ directory                          │
│ ✓ Generate dummy CSV (100 samples)                      │
│ ✓ Location: test_media/test_data.csv                    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Docker Image Building                           │
│ ✓ docker-compose build (all 3 services)                 │
│ ✓ Go Orchestrator image built                           │
│ ✓ Rust Compute image built                              │
│ ✓ Python AI Service image built                         │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 4: Service Deployment                              │
│ ✓ docker-compose up -d (background)                     │
│ ✓ Services started: go-orchestrator, rust-compute,      │
│                     python-worker-1                     │
│ ✓ Wait 10 seconds for initialization                    │
│ ✓ Verify health checks pass                             │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 5: E2E Test Execution                              │
│ ✓ docker exec python-worker-1 python /app/tests/...    │
│ ✓ Run complete test suite (3 tests):                    │
│   - Initialization test                                 │
│   - Single training step test                           │
│   - Full E2E distributed flow test                      │
│ ✓ Capture results to test_e2e.log                       │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 6: Live Log Streaming (60 seconds)                 │
│ ✓ docker-compose logs -f (all services)                 │
│ ✓ Shows request → ingestion → gradient flow             │
│ ✓ Demonstrates distributed transaction coordination     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 7: Graceful Teardown                               │
│ ✓ docker-compose down (remove containers)               │
│ ✓ Clean up temporary resources                          │
│ ✓ Display final summary                                 │
└─────────────────────────────────────────────────────────┘
```

**Usage:**

```bash
# Execute from project root
./setup.sh

# Output:
# [INFO] 🚀 PANGEA NETWORK - END-TO-END TESTING SETUP
# [SUCCESS] Docker found: Docker version 25.0.0
# ...
# [SUCCESS] ALL TESTS PASSED!
```

**Error Handling:**

```bash
# Logs saved to: test_e2e.log
# On failure, displays:
# - Error details
# - Service logs for debugging
# - Debugging steps
# - Cleanup completes automatically
```

---

## Quick Start Guide

### Installation & Prerequisites

```bash
# 1. Install Cap'n Proto compiler
brew install capnproto

# 2. Verify installation
capnp --version

# 3. Clone/access the repository
cd /Users/abhinavnehra/WGT

# 4. Make setup script executable
chmod +x setup.sh
```

### One-Command Full E2E Test

```bash
./setup.sh
```

This runs: validate → setup → build → deploy → test → logs → teardown

### Manual Step-by-Step

```bash
# 1. Generate schemas (MANDATORY FIRST)
make schema-gen

# 2. Build all services
make build

# 3. Start containerized environment
make docker-up

# 4. Run E2E tests
make e2e-test

# 5. View logs
make logs

# 6. Stop services
make docker-down
```

### Development Mode

```bash
# Start services in foreground (see logs in real-time)
docker-compose -f infra/docker-compose.yaml up

# In another terminal, run tests
make e2e-test

# Or execute specific service tests
cd services/go-orchestrator && go test ./...
cd services/rust-compute && cargo test --release
cd services/python-ai-client && python -m pytest tests/
```

---

## Development Workflows

### Adding a New Service

1. **Create service directory:**
   ```bash
   mkdir -p /services/<new-service>
   ```

2. **Implement service:**
   - Create src files and language-specific manifest (go.mod, Cargo.toml, requirements.txt)
   - Implement main entry point
   - Add Dockerfile

3. **Reference schemas:**
   ```go
   // Go example
   import "github.com/pangea-net/shared-schemas/libraries/schemas/go"
   
   // Rust example
   include!("../../../libraries/schemas/rust/schema_capnp.rs");
   
   # Python example
   sys.path.insert(0, "../../libraries/schemas/python")
   import tensor_capnp
   ```

4. **Update docker-compose.yaml:**
   ```yaml
   <new-service>:
     build:
       context: ../services/<new-service>
     container_name: <new-service>
     hostname: <new-service>
     depends_on:
       <dependency>:
         condition: service_healthy
   ```

5. **Add Makefile target:**
   ```makefile
   build-<new-service>: schema-gen
     @echo "Building <new-service>..."
     cd services/<new-service> && <build-command>
   ```

### Updating Shared Schemas

1. **Edit tensor.capnp:**
   ```bash
   vim libraries/schemas/tensor.capnp
   ```

2. **Regenerate all bindings:**
   ```bash
   make schema-gen
   ```

3. **Update services to use new schema:**
   ```
   Each service automatically receives updated bindings
   Update code to use new fields/types
   ```

4. **Test:**
   ```bash
   make test
   make e2e-test
   ```

### Debugging Service Issues

```bash
# View service logs
docker-compose -f infra/docker-compose.yaml logs <service-name>

# Follow logs in real-time
docker-compose -f infra/docker-compose.yaml logs -f <service-name>

# Execute command in running container
docker exec <container-name> <command>

# Open shell in container
docker exec -it <container-name> /bin/bash

# View service status
docker-compose -f infra/docker-compose.yaml ps
```

### Running Service-Specific Tests

```bash
# Go service
cd services/go-orchestrator && go test ./...

# Rust service
cd services/rust-compute && cargo test --release

# Python service
cd services/python-ai-client && python -m pytest tests/ -v
```

---

## Troubleshooting

### Issue: "capnp: command not found"

**Solution:**
```bash
brew install capnproto
# Or on Linux:
# apt-get install capnproto libcapnp-dev
```

### Issue: "Docker daemon not running"

**Solution:**
```bash
# Start Docker Desktop or Docker daemon
# macOS: open /Applications/Docker.app
# Linux: sudo systemctl start docker
```

### Issue: "Port 8080/9090 already in use"

**Solution:**
```bash
# Find and kill process using port
lsof -i :8080
kill -9 <PID>

# Or change port in docker-compose.yaml
# ports:
#   - "8081:8080"
```

### Issue: "Services not communicating"

**Solution:**
```bash
# Verify network connectivity
docker exec <service1> ping <service2>

# Check service logs
docker-compose logs <service1> <service2>

# Verify docker-compose.yaml has correct hostnames
grep hostname infra/docker-compose.yaml
```

### Issue: "E2E tests fail"

**Solution:**
```bash
# Check test log
cat test_e2e.log

# View full service logs
docker-compose -f infra/docker-compose.yaml logs

# Verify services are healthy
docker-compose -f infra/docker-compose.yaml ps

# Run tests manually to see errors
docker exec python-worker-1 python -m pytest tests/ -v
```

### Issue: "Out of disk space"

**Solution:**
```bash
# Clean up Docker resources
docker system prune -a

# Clean up project artifacts
make clean

# Check available space
df -h

# Remove unnecessary images
docker rmi <image-id>
```

---

## Design Principles

### 1. **Single Source of Truth for Schemas**

- All data contracts defined in `/libraries/schemas/tensor.capnp`
- Generated bindings are consumed, never edited
- All services synchronized via single `make schema-gen` command

### 2. **Clear Separation of Concerns**

- **Go Orchestrator:** Coordination, RPC, gradient aggregation
- **Rust Compute:** Data preprocessing, serialization, performance
- **Python AI:** Training, gradient computation, synchronization

### 3. **Automated Tooling**

- Makefile provides unified interface across all languages
- `setup.sh` automates complete E2E pipeline
- No manual steps required for build/deploy/test

### 4. **Containerization for Consistency**

- Each service self-contained in Docker image
- Development environment mirrors production
- Testing in containers eliminates "works on my machine" issues

### 5. **Explicit Path Management**

- All paths relative to service root or project root
- No implicit path assumptions
- docker-compose.yaml uses relative `context` paths
- Python imports use absolute sys.path manipulation

### 6. **Comprehensive Testing**

- Unit tests per service
- Integration tests via E2E suite
- Health checks in every container
- Automatic validation before deployment

### 7. **Graceful Error Handling**

- Services handle SIGINT/SIGTERM for clean shutdown
- Health checks verify service readiness
- setup.sh traps errors and cleans up automatically
- Detailed logging for debugging

---

## Next Steps

1. **Run the setup:**
   ```bash
   ./setup.sh
   ```

2. **Explore the code:**
   - `/services/go-orchestrator` - Coordination logic
   - `/services/rust-compute` - Data processing
   - `/services/python-ai-client` - Training pipeline

3. **Modify and extend:**
   - Update `tensor.capnp` with new data types
   - Add new services following the pattern
   - Implement actual ML training logic

4. **Deploy to production:**
   - Use Kubernetes with Docker images
   - Scale services independently
   - Monitor via health checks

---

## Support & Documentation

- **Architecture:** See `docs/ARCHITECTURE.md`
- **API Documentation:** See service-specific `README.md` files
- **Troubleshooting:** See [Troubleshooting](#troubleshooting) section above
- **Contributing:** See `DEVELOPMENT.md` (to be created)

---

**Generated:** December 2025  
**Version:** 1.0  
**Status:** Production Ready
