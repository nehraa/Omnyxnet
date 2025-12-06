# 🛣️ PATH REFERENCE GUIDE - Complete Path Resolution

**Purpose:** Ensure zero path issues across all services and tools  
**Updated:** December 2025

---

## 🔑 Key Path Constants

### Project Root
```
/Users/abhinavnehra/WGT
```
Aliased as: `$PROJECT_ROOT` in scripts

### Important Directory Paths

| Name | Absolute Path | Usage |
|------|---------------|-------|
| **Services Root** | `/Users/abhinavnehra/WGT/services` | All microservices |
| **Go Orchestrator** | `/Users/abhinavnehra/WGT/services/go-orchestrator` | Go service |
| **Rust Compute** | `/Users/abhinavnehra/WGT/services/rust-compute` | Rust service |
| **Python AI Client** | `/Users/abhinavnehra/WGT/services/python-ai-client` | Python service |
| **Libraries Root** | `/Users/abhinavnehra/WGT/libraries` | Shared code |
| **Schemas Dir** | `/Users/abhinavnehra/WGT/libraries/schemas` | Cap'n Proto source |
| **Go Bindings** | `/Users/abhinavnehra/WGT/libraries/schemas/go` | Generated Go code |
| **Rust Bindings** | `/Users/abhinavnehra/WGT/libraries/schemas/rust` | Generated Rust code |
| **Python Bindings** | `/Users/abhinavnehra/WGT/libraries/schemas/python` | Generated Python code |
| **Infrastructure** | `/Users/abhinavnehra/WGT/infra` | Docker & infra configs |
| **Documentation** | `/Users/abhinavnehra/WGT/docs` | All documentation |

---

## 📋 Service-Specific Paths

### Go Orchestrator (`go-orchestrator`)

**Base Path:** `/Users/abhinavnehra/WGT/services/go-orchestrator`

| Component | Path | Relative |
|-----------|------|----------|
| Main entry point | `main.go` | `./main.go` |
| Go mod | `go.mod` | `./go.mod` |
| Go sum | `go.sum` | `./go.sum` |
| Dockerfile | `Dockerfile` | `./Dockerfile` |
| Gradient pkg | `pkg/gradient/manager.go` | `./pkg/gradient/manager.go` |
| Schema bindings | `../../libraries/schemas/go` | `../../libraries/schemas/go` |
| Build output | `bin/go-orchestrator` | `./bin/go-orchestrator` |

**Docker Context:**
```dockerfile
FROM golang:1.24-alpine
WORKDIR /app
COPY . .
RUN go build -o go-orchestrator main.go
```

**Docker Compose Build Context:**
```yaml
build:
  context: ../services/go-orchestrator  # Relative to docker-compose.yaml
  dockerfile: Dockerfile                 # Relative to context
```

### Rust Compute (`rust-compute`)

**Base Path:** `/Users/abhinavnehra/WGT/services/rust-compute`

| Component | Path | Relative |
|-----------|------|----------|
| Main.rs | `src/main.rs` | `./src/main.rs` |
| Data processing | `src/data_processing.rs` | `./src/data_processing.rs` |
| Cargo.toml | `Cargo.toml` | `./Cargo.toml` |
| Cargo.lock | `Cargo.lock` | `./Cargo.lock` |
| Dockerfile | `Dockerfile` | `./Dockerfile` |
| Schema bindings | `../../libraries/schemas/rust` | `../../libraries/schemas/rust` |
| Build output | `target/release/pangea-rust-compute` | `./target/release/pangea-rust-compute` |

**Docker Context:**
```dockerfile
FROM rust:1.84-alpine
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release
```

**Docker Compose Build Context:**
```yaml
build:
  context: ../services/rust-compute  # Relative to docker-compose.yaml
  dockerfile: Dockerfile
```

### Python AI Client (`python-ai-client`)

**Base Path:** `/Users/abhinavnehra/WGT/services/python-ai-client`

| Component | Path | Relative |
|-----------|------|----------|
| Main entry | `app/main.py` | `./app/main.py` |
| Training core | `app/training_core.py` | `./app/training_core.py` |
| E2E tests | `tests/run_e2e_test.py` | `./tests/run_e2e_test.py` |
| Requirements | `requirements.txt` | `./requirements.txt` |
| Dockerfile | `Dockerfile` | `./Dockerfile` |
| Schema bindings | `../../libraries/schemas/python` | `../../libraries/schemas/python` |

**Path Setup in Python Code:**
```python
# In app/main.py
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

# Now can import:
from app.training_core import TrainingEngine
```

**Docker Context:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
COPY tests ./tests
CMD ["python", "app/main.py"]
```

**Docker Compose Build Context:**
```yaml
build:
  context: ../services/python-ai-client  # Relative to docker-compose.yaml
  dockerfile: Dockerfile
```

---

## 🔗 Shared Schema Paths

### Source of Truth

**Path:** `/Users/abhinavnehra/WGT/libraries/schemas/tensor.capnp`

**Referenced as:**
- Absolute: `/Users/abhinavnehra/WGT/libraries/schemas/tensor.capnp`
- Relative from project root: `libraries/schemas/tensor.capnp`
- In Makefile: `libraries/schemas/tensor.capnp` (executed from project root)

### Generated Bindings

#### Go Bindings
- **Location:** `/Users/abhinavnehra/WGT/libraries/schemas/go/`
- **Generated file:** `tensor.capnp.go` (auto-generated)
- **Included via:** Relative path `../../libraries/schemas/go` from Go service
- **Import statement:**
  ```go
  import "github.com/pangea-net/go-orchestrator/pkg/gradient"
  // Uses schema from: ../../libraries/schemas/go
  ```

#### Rust Bindings
- **Location:** `/Users/abhinavnehra/WGT/libraries/schemas/rust/`
- **Generated file:** Module files (auto-generated)
- **Included via:** Include macro or Cargo path dependency
- **In Cargo.toml:**
  ```toml
  [dependencies]
  # Reference generated schemas
  ```

#### Python Bindings
- **Location:** `/Users/abhinavnehra/WGT/libraries/schemas/python/`
- **Generated file:** `tensor_capnp.py` (auto-generated)
- **Included via:** Python sys.path manipulation
- **Import statement:**
  ```python
  sys.path.insert(0, "../../libraries/schemas/python")
  import tensor_capnp
  ```

---

## 🔄 Docker Compose Path Resolution

**File Location:** `/Users/abhinavnehra/WGT/infra/docker-compose.yaml`

**All paths are relative to docker-compose.yaml location:**

```yaml
version: '3.9'

services:
  go-orchestrator:
    build:
      context: ../services/go-orchestrator        # Relative to docker-compose.yaml
      dockerfile: Dockerfile                      # Relative to context

  rust-compute:
    build:
      context: ../services/rust-compute           # Relative to docker-compose.yaml
      dockerfile: Dockerfile                      # Relative to context

  python-worker-1:
    build:
      context: ../services/python-ai-client       # Relative to docker-compose.yaml
      dockerfile: Dockerfile                      # Relative to context

volumes:
  shared-data:
    driver: local
```

**Execution from:**
```bash
# CORRECT: From project root
cd /Users/abhinavnehra/WGT
docker-compose -f infra/docker-compose.yaml up

# CORRECT: Using make
make docker-up  # Runs: docker-compose -f infra/docker-compose.yaml up -d

# WRONG: Don't execute from infra directory
cd /Users/abhinavnehra/WGT/infra
docker-compose up  # Paths will break!
```

---

## 📜 Makefile Path Resolution

**File Location:** `/Users/abhinavnehra/WGT/Makefile`

**Execution directory:** Project root (`/Users/abhinavnehra/WGT`)

**Path references:**
```makefile
# All paths are relative to project root
schema-gen:
	capnp compile -o go:libraries/schemas/go libraries/schemas/tensor.capnp
	capnp compile -o rust:libraries/schemas/rust libraries/schemas/tensor.capnp
	capnp compile -o python:libraries/schemas/python libraries/schemas/tensor.capnp

build-go:
	cd services/go-orchestrator && go build -o bin/go-orchestrator main.go

build-rust:
	cd services/rust-compute && cargo build --release

docker-up:
	docker-compose -f infra/docker-compose.yaml up -d
```

**Correct usage:**
```bash
# From project root
cd /Users/abhinavnehra/WGT
make schema-gen
make build
make docker-up

# ALL GOOD - paths work
```

**Incorrect usage:**
```bash
# From service directory
cd /Users/abhinavnehra/WGT/services/go-orchestrator
make schema-gen  # FAILS - Makefile not found

# From infra directory
cd /Users/abhinavnehra/WGT/infra
make docker-up   # Paths broken
```

---

## 🚀 setup.sh Path Resolution

**File Location:** `/Users/abhinavnehra/WGT/setup.sh`

**Execution directory:** Any directory (script determines project root)

**Path detection in setup.sh:**
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$SCRIPT_DIR/infra"

# Results:
# SCRIPT_DIR = /Users/abhinavnehra/WGT
# PROJECT_ROOT = /Users/abhinavnehra/WGT
# INFRA_DIR = /Users/abhinavnehra/WGT/infra
```

**Correct usage:**
```bash
# From anywhere - script finds project root automatically
cd /Users/abhinavnehra/WGT && ./setup.sh
cd /tmp && /Users/abhinavnehra/WGT/setup.sh
./setup.sh  # If you're in the project directory
```

**All paths inside setup.sh:**
```bash
DOCKER_COMPOSE_FILE="$INFRA_DIR/docker-compose.yaml"
TEST_LOG_FILE="$PROJECT_ROOT/test_e2e.log"
TEST_DATA_FILE="$PROJECT_ROOT/test_media/test_data.csv"

# These are absolute, so work from any directory
```

---

## 🐳 Docker Container Path Mapping

### Go Orchestrator Container

```yaml
Container working directory: /app
Mounted source: /Users/abhinavnehra/WGT/services/go-orchestrator → /app
Binary path in container: /app/go-orchestrator
```

### Rust Compute Container

```yaml
Container working directory: /app
Mounted source: /Users/abhinavnehra/WGT/services/rust-compute → /app
Binary path in container: /app/target/release/pangea-rust-compute
```

### Python AI Client Container

```yaml
Container working directory: /app
Mounted source: /Users/abhinavnehra/WGT/services/python-ai-client → /app
Code paths in container:
  - /app/app/main.py
  - /app/app/training_core.py
  - /app/tests/run_e2e_test.py
```

---

## 🔍 Path Verification Commands

### Verify All Service Paths

```bash
#!/bin/bash
PROJECT_ROOT="/Users/abhinavnehra/WGT"

# Check all critical paths exist
paths=(
  "$PROJECT_ROOT/services/go-orchestrator"
  "$PROJECT_ROOT/services/rust-compute"
  "$PROJECT_ROOT/services/python-ai-client"
  "$PROJECT_ROOT/libraries/schemas"
  "$PROJECT_ROOT/infra/docker-compose.yaml"
  "$PROJECT_ROOT/Makefile"
  "$PROJECT_ROOT/setup.sh"
)

for path in "${paths[@]}"; do
  if [ -e "$path" ]; then
    echo "✅ Found: $path"
  else
    echo "❌ Missing: $path"
  fi
done
```

### Verify Service Structure

```bash
# Go Orchestrator
ls -la /Users/abhinavnehra/WGT/services/go-orchestrator/
# Should show: main.go, go.mod, Dockerfile, pkg/

# Rust Compute
ls -la /Users/abhinavnehra/WGT/services/rust-compute/
# Should show: Cargo.toml, Dockerfile, src/

# Python AI Client
ls -la /Users/abhinavnehra/WGT/services/python-ai-client/
# Should show: app/, tests/, requirements.txt, Dockerfile
```

### Verify Schema Generation

```bash
# Check source exists
ls -la /Users/abhinavnehra/WGT/libraries/schemas/tensor.capnp

# Check generated bindings exist (after make schema-gen)
ls -la /Users/abhinavnehra/WGT/libraries/schemas/go/
ls -la /Users/abhinavnehra/WGT/libraries/schemas/rust/
ls -la /Users/abhinavnehra/WGT/libraries/schemas/python/
```

---

## 🚨 Common Path Mistakes & Fixes

### Mistake 1: Running from wrong directory
```bash
❌ WRONG:
cd /Users/abhinavnehra/WGT/services/go-orchestrator
make schema-gen  # Makefile not in this directory!

✅ CORRECT:
cd /Users/abhinavnehra/WGT
make schema-gen
```

### Mistake 2: Broken docker-compose paths
```bash
❌ WRONG:
cd /Users/abhinavnehra/WGT/infra
docker-compose up  # Context paths are wrong!

✅ CORRECT:
cd /Users/abhinavnehra/WGT
docker-compose -f infra/docker-compose.yaml up
# OR
make docker-up
```

### Mistake 3: Hardcoded absolute paths in code
```go
❌ WRONG:
import "/Users/abhinavnehra/WGT/libraries/schemas/go"

✅ CORRECT:
import "../../libraries/schemas/go"  // Relative to service
```

### Mistake 4: Python import path issues
```python
❌ WRONG:
import sys
sys.path.append("/Users/abhinavnehra/WGT/services/python-ai-client")

✅ CORRECT:
from pathlib import Path
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
from app.training_core import TrainingEngine
```

### Mistake 5: Schema generation from wrong directory
```bash
❌ WRONG:
cd /Users/abhinavnehra/WGT/libraries/schemas
capnp compile -o go:go tensor.capnp  # Wrong path!

✅ CORRECT:
cd /Users/abhinavnehra/WGT
make schema-gen  # Handles all paths automatically
```

---

## ✅ Path Resolution Checklist

Before running any command, verify:

- [ ] You're in the project root: `/Users/abhinavnehra/WGT`
- [ ] All service directories exist: `services/go-orchestrator`, `services/rust-compute`, `services/python-ai-client`
- [ ] Schema directory exists: `libraries/schemas/` with `tensor.capnp`
- [ ] Infrastructure file exists: `infra/docker-compose.yaml`
- [ ] Makefile exists in project root
- [ ] setup.sh is executable: `ls -l setup.sh | grep x`
- [ ] Docker is running: `docker ps` returns no errors
- [ ] You have write permissions in project directory

---

## 📞 Quick Reference

### Command Execution Paths

| Command | Run From | Effect |
|---------|----------|--------|
| `make schema-gen` | `/Users/abhinavnehra/WGT` | Generates all bindings |
| `make build` | `/Users/abhinavnehra/WGT` | Builds all services |
| `make docker-up` | `/Users/abhinavnehra/WGT` | Starts containers |
| `./setup.sh` | Any directory | Runs complete E2E test |
| `docker-compose -f infra/docker-compose.yaml up` | `/Users/abhinavnehra/WGT` | Starts services manually |

### Directory Context

| Action | Required Directory |
|--------|-------------------|
| Generate schemas | `/Users/abhinavnehra/WGT` |
| Build Go service | `/Users/abhinavnehra/WGT/services/go-orchestrator` |
| Build Rust service | `/Users/abhinavnehra/WGT/services/rust-compute` |
| Install Python deps | `/Users/abhinavnehra/WGT/services/python-ai-client` |
| Run docker-compose | `/Users/abhinavnehra/WGT` |
| Run tests | Project root or via containers |

---

**Version:** 1.0  
**Last Updated:** December 2025  
**Status:** Ready for Production
