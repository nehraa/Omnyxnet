# Containerized Testing Guide

This guide explains how to run WGT tests in Docker containers for isolated, reproducible testing.

## Overview

The WGT containerized testing suite provides:
- **Isolated environments** for testing distributed features
- **Multi-node configurations** (2-node, 3-node, multi-worker)
- **Automated test runners** with detailed reporting
- **Matrix multiplication** and network connection tests

## Quick Start

```bash
# Run quick tests (local only, no Docker)
./scripts/run_container_tests.sh --quick

# Run matrix CLI tests
./scripts/container_tests/test_matrix_cli.sh --local-only

# Run network tests
./scripts/container_tests/test_network_connection.sh

# Run full test suite (requires Docker)
./scripts/run_container_tests.sh --full
```

## Prerequisites

### For Local Tests

- Python 3.10+
- pip packages: click, pycapnp, numpy

### For Container Tests

- Docker 20.10+
- Docker Compose 2.0+ (or docker-compose 1.29+)
- 4GB+ RAM available

## Docker Compose Configurations

### 2-Node Test Environment

File: `docker-compose.test.2node.yml`

```yaml
Services:
  manager:     # Node 1 - Orchestrator
  worker:      # Node 2 - Executor
  python-cli:  # Test runner
```

```bash
# Start 2-node environment
docker-compose -f docker-compose.test.2node.yml up -d

# View logs
docker-compose -f docker-compose.test.2node.yml logs -f

# Stop environment
docker-compose -f docker-compose.test.2node.yml down
```

### 3-Node Mesh Environment

File: `docker-compose.test.3node.yml`

```yaml
Services:
  node1:  # Bootstrap node
  node2:  # Connects to node1
  node3:  # Connects to node1 and node2
```

```bash
# Start 3-node mesh
docker-compose -f docker-compose.test.3node.yml up -d

# Check mesh health
docker-compose -f docker-compose.test.3node.yml ps
```

### Multi-Node Compute Environment

File: `docker-compose.test.compute.yml`

```yaml
Services:
  manager:     # Orchestrator
  worker1:     # Worker 1
  worker2:     # Worker 2
  worker3:     # Worker 3
  test-runner: # Python test runner
```

```bash
# Start compute cluster
docker-compose -f docker-compose.test.compute.yml up -d

# Run tests
docker exec wgt-compute-test python main.py compute matrix-multiply \
    --size 50 --generate --verify --connect --host 172.30.0.10
```

## Test Scripts

### Matrix CLI Tests

Location: `scripts/container_tests/test_matrix_cli.sh`

Tests:
1. Local random matrix multiplication
2. Local file-based multiplication
3. Distributed container multiplication (if Docker available)

```bash
# Local tests only
./scripts/container_tests/test_matrix_cli.sh --local-only

# With custom matrix size
./scripts/container_tests/test_matrix_cli.sh --size 20

# Full tests (includes containers)
./scripts/container_tests/test_matrix_cli.sh
```

### Network Connection Tests

Location: `scripts/container_tests/test_network_connection.sh`

Tests:
1. Registry initialization
2. Save peer
3. Get peer
4. List peers
5. Connection status check
6. Clear registry
7. check_network.sh script

```bash
./scripts/container_tests/test_network_connection.sh
```

### Distributed Compute Tests

Location: `scripts/container_tests/test_compute_distributed.sh`

Tests:
- Small matrix (5x5)
- Medium matrix (20x20)
- Large matrix (50x50)

```bash
# 2-node test
./scripts/container_tests/test_compute_distributed.sh --nodes 2

# 3-node mesh test
./scripts/container_tests/test_compute_distributed.sh --nodes 3

# 4-node compute cluster test
./scripts/container_tests/test_compute_distributed.sh --nodes 4
```

### All Features Test

Location: `scripts/container_tests/test_all_features.sh`

Runs all tests in sequence:
1. Network Connection Tests
2. Matrix CLI Tests
3. Distributed Compute Tests
4. Python CLI Tests

```bash
# Quick mode
./scripts/container_tests/test_all_features.sh --quick

# Full mode
./scripts/container_tests/test_all_features.sh
```

## Test Runner

The main test runner orchestrates all container tests.

Location: `scripts/run_container_tests.sh`

### Options

| Option | Description |
|--------|-------------|
| `--quick` | Run quick tests only (no Docker containers) |
| `--matrix-only` | Only run matrix multiplication tests |
| `--network-only` | Only run network tests |
| `--full` | Run full test suite with all container configurations |
| `--help` | Show help message |

### Examples

```bash
# Quick local tests
./scripts/run_container_tests.sh --quick

# Matrix tests only
./scripts/run_container_tests.sh --matrix-only

# Network tests only
./scripts/run_container_tests.sh --network-only

# Full test suite
./scripts/run_container_tests.sh --full
```

### Test Reports

Reports are saved to: `~/.wgt/logs/container_tests_<timestamp>.log`

```
============================================
WGT Container Test Run
Started: Thu Dec  5 14:30:00 UTC 2025
Quick Mode: false
Full Mode: true
============================================

...

============================================
SUMMARY
============================================
Total: 5
Passed: 5
Failed: 0
Skipped: 0
Duration: 120s
Ended: Thu Dec  5 14:32:00 UTC 2025
============================================
```

## Test Coverage Matrix

| Feature | Local | 2-Node | 3-Node | Multi | Status |
|---------|-------|--------|--------|-------|--------|
| Matrix CLI (random) | ✅ | ✅ | - | - | Working |
| Matrix CLI (file) | ✅ | ✅ | - | - | Working |
| Matrix CLI (distributed) | - | ✅ | ✅ | ✅ | Working |
| Network Connection (Manager) | ✅ | ✅ | ✅ | ✅ | Working |
| Network Connection (Worker) | - | ✅ | ✅ | ✅ | Working |
| Network Registry | ✅ | ✅ | ✅ | ✅ | Working |
| mDNS Peer Discovery | ✅ | ✅ | ✅ | ✅ | Working |
| Manual Peer Override | ✅ | ✅ | ✅ | ✅ | Working |

## Troubleshooting

### Docker Not Available

```bash
# Run local tests only
./scripts/run_container_tests.sh --quick

# Or test specific features
./scripts/container_tests/test_matrix_cli.sh --local-only
```

### Container Build Fails

```bash
# Check Docker daemon
docker info

# Build containers manually
docker-compose -f docker-compose.test.2node.yml build

# Check build logs
docker-compose -f docker-compose.test.2node.yml logs manager
```

### Container Network Issues

```bash
# List networks
docker network ls

# Inspect network
docker network inspect wgt-net

# Recreate network
docker-compose -f docker-compose.test.2node.yml down
docker network prune
docker-compose -f docker-compose.test.2node.yml up -d
```

### Test Hangs

```bash
# Check container logs
docker-compose -f docker-compose.test.2node.yml logs -f

# Force stop containers
docker-compose -f docker-compose.test.2node.yml down -v --remove-orphans
```

### Port Conflicts

If ports 8080-8083 or 9081-9084 are in use:

```bash
# Find process using port
lsof -i :8080

# Kill process (with specific PID)
kill <PID>

# Or use different ports in compose file
```

## Cleanup

### Remove Test Containers

```bash
# Stop and remove all test containers
docker-compose -f docker-compose.test.2node.yml down -v
docker-compose -f docker-compose.test.3node.yml down -v
docker-compose -f docker-compose.test.compute.yml down -v
```

### Remove Test Images

```bash
# Remove WGT test images
docker rmi $(docker images | grep wgt | awk '{print $3}')
```

### Clear Test Logs

```bash
rm -rf ~/.wgt/logs/container_tests_*.log
```

## CI/CD Integration

### GitHub Actions Example

```yaml
jobs:
  container-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd python
          pip install -r requirements.txt
      
      - name: Run quick tests
        run: ./scripts/run_container_tests.sh --quick
      
      - name: Run container tests
        run: ./scripts/run_container_tests.sh --full
```

## See Also

- [CLI_MATRIX_MULTIPLY.md](CLI_MATRIX_MULTIPLY.md) - Matrix multiply CLI
- [NETWORK_CONNECTION.md](NETWORK_CONNECTION.md) - Network setup
- [TESTING_QUICK_START.md](TESTING_QUICK_START.md) - General testing guide
- [DISTRIBUTED_COMPUTE_QUICK_START.md](DISTRIBUTED_COMPUTE_QUICK_START.md) - Distributed compute
