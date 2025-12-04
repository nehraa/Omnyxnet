# Test Scripts

**Version:** 0.3.0-alpha  
**Last Updated:** 2025-12-04

> 📋 These test scripts validate local functionality. For comprehensive test status, see [../VERSION.md](../VERSION.md).

## Test Organization

Tests are organized by component/feature:

```
tests/
├── README.md           # This file
├── communication/      # P2P communication tests (chat, voice, video)
├── compute/            # Distributed compute and CES pipeline tests
├── integration/        # Full system integration tests
├── streaming/          # Media streaming tests
├── test_all.sh         # Run all tests
├── test_go.sh          # Go-specific tests
├── test_python.sh      # Python-specific tests
├── test_rust.sh        # Rust-specific tests
└── ...
```

## Quick Start

### Run All Tests
```bash
# Via setup.sh (recommended - interactive menu)
./scripts/setup.sh

# Or run all tests directly
./tests/test_all.sh
```

### Run Specific Test Categories

**Communication Tests:**
```bash
./tests/test_communication.sh   # P2P chat/voice/video
```

**Compute Tests:**
```bash
./tests/test_compute.sh         # Distributed compute
./tests/test_ces_simple.sh      # CES pipeline wiring
./tests/test_ffi_integration.sh # Go-Rust FFI
```

**Streaming Tests:**
```bash
./tests/test_streaming.sh       # Media streaming
```

**Integration Tests:**
```bash
./tests/test_integration.sh     # Full Go + Python connectivity
./tests/test_localhost_full.sh  # Comprehensive multi-node test
```

## Golden Rule Architecture

All tests follow the Golden Rule:
- **Go**: All networking (libp2p, TCP, UDP)
- **Rust**: Files, memory, CES pipeline
- **Python**: AI and CLI management

## Running Tests

### Path Resolution Tests
```bash
./tests/test_paths.sh
```

Tests that all paths work correctly from any directory.

### Go Tests
```bash
./tests/test_go.sh
```

Tests: Build compilation, binary creation, help command, port availability.

### Python Tests
```bash
./tests/test_python.sh
```

Tests: Python version, dependencies, module structure, syntax validation, CLI.

### Rust Tests
```bash
./tests/test_rust.sh
```

Tests: Cargo build, FFI library, CES pipeline.

### Full Integration Test
```bash
./tests/test_integration.sh
```

Full system test with Go + Python connectivity:
1. Builds Go node
2. Starts Go node on localhost:8080
3. Tests Python connecting via Cap'n Proto RPC
4. Tests all RPC methods
5. Cleans up automatically

## Live Testing

For interactive live testing with real P2P connections:

```bash
./scripts/live_test.sh
```

This starts a Go node with libp2p and provides options for:
1. 💬 Live Chat
2. 🎤 Live Voice
3. 🎥 Live Video (TCP)
4. 🎥 Live Video (UDP)

## Notes

- All scripts use absolute paths - work from any directory
- Python uses `utils.paths` module to find project root
- Schema paths are automatically resolved

