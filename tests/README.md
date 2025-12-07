# Test Scripts

**Version:** 0.6.0-alpha  
**Last Updated:** 2025-12-07  
**Status:** ✅ 86+ Tests Passing

> 📚 **Complete Testing Documentation:**
> - **[../docs/testing/TESTING_INDEX.md](../docs/testing/TESTING_INDEX.md)** ⭐ - Central testing hub
> - **[../docs/testing/PHASE1_TEST_SUITE.md](../docs/testing/PHASE1_TEST_SUITE.md)** - Phase 1 tests
> - **[../docs/testing/PHASE2_TEST_SUITE.md](../docs/testing/PHASE2_TEST_SUITE.md)** - Phase 2 tests  
> - **[../docs/testing/COMPUTE_TEST_SUITE.md](../docs/testing/COMPUTE_TEST_SUITE.md)** - Compute tests (86+)
> - **[../docs/TESTING_QUICK_START.md](../docs/TESTING_QUICK_START.md)** - Quick commands

> 📋 These test scripts validate functionality. For comprehensive test status, see **[testing documentation](../docs/testing/TESTING_INDEX.md)**.

## Test Organization

Tests are organized by component/feature into subdirectories:

```
tests/
├── README.md               # This file
├── communication/          # P2P communication tests (chat, voice, video)
│   ├── test_communication.sh
│   └── test_p2p_streaming.py
├── compute/                # Distributed compute tests
│   └── test_compute.sh
├── ces/                    # CES pipeline tests
│   ├── test_ces_simple.sh
│   ├── test_ces_wiring.py
│   └── test_ces_compression.py
├── streaming/              # Media streaming tests
│   ├── test_streaming.sh
│   ├── test_stream_updates.sh
│   └── test_localhost_streaming.py
├── integration/            # Full system integration tests
│   ├── test_integration.sh
│   ├── test_localhost_full.sh
│   ├── test_ffi_integration.sh
│   └── test_upload_download*.sh
├── test_all.sh             # Run all tests
├── test_go.sh              # Go-specific tests
├── test_python.sh          # Python-specific tests
├── test_rust.sh            # Rust-specific tests
└── test_phase*.sh/py       # Phase-specific tests
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
./tests/communication/test_communication.sh   # P2P chat/voice/video
```

**Compute Tests:**
```bash
./tests/compute/test_compute.sh               # Distributed compute
```

**CES Pipeline Tests:**
```bash
./tests/ces/test_ces_simple.sh                # CES pipeline wiring
```

**Streaming Tests:**
```bash
./tests/streaming/test_streaming.sh           # Media streaming
```

**Integration Tests:**
```bash
./tests/integration/test_integration.sh       # Full Go + Python connectivity
./tests/integration/test_localhost_full.sh    # Comprehensive multi-node test
./tests/integration/test_ffi_integration.sh   # Go-Rust FFI
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
./tests/integration/test_integration.sh
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

