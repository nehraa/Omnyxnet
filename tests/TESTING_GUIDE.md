# WGT Testing Guide

This guide maps which tests to use for different scenarios.

## Quick Reference

| What to Test | Command |
|--------------|---------|
| All local tests | `./tests/test_all.sh` |
| With container tests | `./tests/test_all.sh --with-containers` |
| Container tests only | `./tests/test_all.sh --containers-only` |
| Matrix multiply CLI | `python main.py compute matrix-multiply --generate` |
| Network connection | `./scripts/check_network.sh --status` |
| Container tests | `./scripts/run_container_tests.sh --quick` |

## Test Categories

### Component Tests

| Test | Description | Command |
|------|-------------|---------|
| Python | Python syntax and structure | `./tests/test_python.sh` |
| Go | Go build and binary | `./tests/test_go.sh` |
| Rust | Rust build and unit tests | `./tests/test_rust.sh` |
| Integration | Cross-component communication | `./tests/integration/test_integration.sh` |
| FFI | Go-Rust FFI integration | `./tests/integration/test_ffi_integration.sh` |

### Container Tests

| Test | Description | Command |
|------|-------------|---------|
| All features | Complete test suite | `./scripts/run_container_tests.sh --full` |
| Quick | Local tests only | `./scripts/run_container_tests.sh --quick` |
| Network only | Network registry tests | `./scripts/container_tests/test_network_connection.sh` |
| Matrix only | Matrix CLI tests | `./scripts/container_tests/test_matrix_cli.sh --local-only` |
| Distributed | Multi-node compute | `./scripts/container_tests/test_compute_distributed.sh --nodes 2` |

### Feature Tests

| Test | Description | Command |
|------|-------------|---------|
| Matrix multiply | Distributed matrix multiplication | `python main.py compute matrix-multiply --generate` |
| CES pipeline | Compress/Encrypt/Shard | `./tests/ces/test_ces_simple.sh` |
| Streaming | Stream updates | `./tests/streaming/test_stream_updates.sh` |
| Phase 1 | Brotli, Opus, Metrics | `./tests/test_phase1_features.sh` |

## When to Use Which Tests

### Daily Development

```bash
# Quick verification
./scripts/container_tests/test_matrix_cli.sh --local-only --size 5

# Check network registry
./scripts/container_tests/test_network_connection.sh
```

### Before Commit

```bash
# Standard test suite
./tests/test_all.sh

# With container tests
./tests/test_all.sh --with-containers
```

### Before Release

```bash
# Full test suite
./tests/test_all.sh --with-containers

# Full container tests (requires Docker)
./scripts/run_container_tests.sh --full
```

### Debugging

```bash
# Check specific component
./tests/test_go.sh
./tests/test_rust.sh
./tests/test_python.sh

# Check network status
./scripts/check_network.sh --status
./scripts/check_network.sh --test
```

## Test Directory Structure

```
tests/
├── test_all.sh              # Main test runner
├── test_go.sh               # Go component tests
├── test_python.sh           # Python component tests  
├── test_rust.sh             # Rust component tests
├── test_compilation.sh      # Build verification
├── test_phase1_features.sh  # Phase 1 features
├── TESTING_GUIDE.md         # This file
│
├── integration/             # Integration tests
│   ├── test_integration.sh
│   ├── test_ffi_integration.sh
│   ├── test_localhost_full.sh
│   └── test_upload_download_*.sh
│
├── streaming/               # Streaming tests
│   ├── test_streaming.sh
│   └── test_stream_updates.sh
│
├── ces/                     # CES pipeline tests
│   └── test_ces_simple.sh
│
├── compute/                 # Compute tests
│   └── examples/
│       ├── 03_distributed_compute.sh  # Main example
│       ├── 04_ces_pipeline.sh         # CES example
│       └── archive/                   # Deprecated scripts
│
└── communication/           # Communication tests
    └── test_communication.sh
```

## Container Test Files

```
scripts/
├── run_container_tests.sh   # Main container test runner
├── check_network.sh         # Network health check
├── network_registry.sh      # Network registry module
│
└── container_tests/         # Container test scripts
    ├── test_matrix_cli.sh
    ├── test_network_connection.sh
    ├── test_compute_distributed.sh
    └── test_all_features.sh
```

## Docker Compose Files

```
docker-compose.test.2node.yml    # 2-node (Manager + Worker)
docker-compose.test.3node.yml    # 3-node mesh
docker-compose.test.compute.yml  # Multi-node compute cluster
```

## Test Output

Test logs are saved to:
- `/tmp/test_*.log` - Component test logs
- `~/.wgt/logs/container_tests_*.log` - Container test logs
- `~/.wgt/logs/network.log` - Network connection logs

## See Also

- [docs/CONTAINERIZED_TESTING.md](../docs/CONTAINERIZED_TESTING.md) - Detailed container testing guide
- [docs/CLI_MATRIX_MULTIPLY.md](../docs/CLI_MATRIX_MULTIPLY.md) - Matrix multiply CLI reference
- [docs/NETWORK_CONNECTION.md](../docs/NETWORK_CONNECTION.md) - Network connection guide
