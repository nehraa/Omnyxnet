# Testing Documentation Index

**Version:** 0.6.0-alpha  
**Last Updated:** 2025-12-07  
**Status:** ✅ Complete Testing Infrastructure

---

## 📋 Overview

This document serves as the central hub for all testing documentation in Pangea Net. It provides links to all test suites, guides, and resources across all project phases.

## 🎯 Quick Navigation

### For New Users
1. Start with [TESTING_QUICK_START.md](../TESTING_QUICK_START.md) - Get testing in 5 minutes
2. Read [START_HERE.md](../START_HERE.md) - Testing overview
3. Run `./scripts/setup.sh` and select option 7 (Run All Localhost Tests)

### For Developers
1. Review [TESTING_GUIDE.md](TESTING_GUIDE.md) - Comprehensive testing guide
2. Check phase-specific test suites below
3. See [Test Infrastructure](#test-infrastructure) section

### For CI/CD Integration
1. See [Automated Testing](#automated-testing) section
2. Review [Test Scripts Reference](#test-scripts-reference)
3. Check [Test Results](#current-test-status)

---

## 🧪 Test Suites by Phase

### Phase 1: Core P2P & Streaming ✅
**Status:** Complete - All tests passing  
**Documentation:** [PHASE1_TEST_SUITE.md](PHASE1_TEST_SUITE.md)

**What's Tested:**
- ✅ Brotli compression (better than Zstd for text)
- ✅ Opus audio codec (<100ms latency target, achieved 0.40ms)
- ✅ Performance metrics tracking
- ✅ Voice streaming with 10ms frames
- ✅ Large media processing (60MB video in 262ms)
- ✅ Cross-device P2P communication
- ✅ libp2p networking with NAT traversal

**Test Files:**
- `tests/test_phase1_features.sh` - Main Phase 1 test runner
- `tests/test_phase1_benchmarks.sh` - Performance benchmarking
- `tests/test_phase1_audio.py` - Audio processing integration
- `rust/tests/phase1_features_test.rs` - Rust unit tests (12 tests)
- `tests/streaming/test_streaming.sh` - Streaming protocol tests
- `tests/streaming/test_localhost_streaming.py` - Python streaming tests

**Quick Run:**
```bash
./scripts/setup.sh
# Select: 14 - Run Phase 1 Features Test
```

---

### Phase 2: ML Translation & Personalization ✅
**Status:** Framework Complete - Ready for Model Integration  
**Documentation:** [PHASE2_TEST_SUITE.md](PHASE2_TEST_SUITE.md)

**What's Tested:**
- ✅ Translation pipeline structure (ASR → NMT → TTS)
- ✅ Video lipsync pipeline components
- ✅ Federated learning framework (P2P-FL + CSM)
- ✅ Model weight serialization and compression
- ✅ Module imports and dependencies
- ✅ CPU/GPU fallback mechanisms

**Test Files:**
- `tests/test_phase2_structure.py` - Structure validation (6 tests)
- `tests/test_phase2_modules.py` - Module integration tests (8 tests)
- `python/src/ai/translation_pipeline.py` - Translation components
- `python/src/ai/video_lipsync.py` - Video lipsync components
- `python/src/ai/federated_learning.py` - FL framework

**Quick Run:**
```bash
cd tests
pytest test_phase2_structure.py -v
pytest test_phase2_modules.py -v
```

**Note:** Phase 2 has complete framework but ML models need integration. Tests validate structure and readiness.

---

### Distributed Compute System ✅
**Status:** Complete - All tests passing  
**Documentation:** [COMPUTE_TEST_SUITE.md](COMPUTE_TEST_SUITE.md)

**What's Tested:**
- ✅ WASM Sandbox with resource limits (27 Rust tests)
- ✅ CPU, memory, and time metering
- ✅ Merkle tree verification (Hash, Merkle, Redundancy)
- ✅ Split/Merge executor for data chunking
- ✅ Go task manager and scheduler (13 Go tests)
- ✅ Load balancing with worker trust scoring
- ✅ Python Job DSL (thread-safe)
- ✅ Python SDK (RPC client, preprocessing)
- ✅ End-to-end distributed computation

**Test Files:**
- `tests/compute/test_compute.sh` - Complete compute test suite (5 checks)
- `rust/src/compute/sandbox.rs` - WASM sandbox tests
- `rust/src/compute/metering.rs` - Resource metering tests
- `rust/src/compute/verification.rs` - Verification tests
- `rust/src/compute/executor.rs` - Executor tests
- `go/pkg/compute/manager_test.go` - Task manager tests
- `go/pkg/compute/scheduler_test.go` - Scheduler tests
- `tests/compute/examples/03_distributed_compute.sh` - Cross-device compute

**Quick Run:**
```bash
./scripts/setup.sh
# Select: 18 - Run Compute Tests
# Select: 3 - Distributed Compute
```

**Test Results:** 86+ tests passing (61 Rust + 13 Go + Python SDK)

---

### Integration & System Tests ✅
**Status:** Complete - All passing  
**Documentation:** See individual test files

**What's Tested:**
- ✅ Multi-language integration (Python ↔ Go ↔ Rust)
- ✅ Cap'n Proto RPC communication
- ✅ FFI bridge (Go ↔ Rust)
- ✅ CES pipeline (Compression, Encryption, Sharding)
- ✅ Upload/Download workflows
- ✅ Cross-device file transfers
- ✅ Node discovery and peer management
- ✅ Network health monitoring

**Test Files:**
- `tests/integration/test_integration.sh` - Full system integration
- `tests/integration/test_localhost_full.sh` - Comprehensive localhost test
- `tests/integration/test_ffi_integration.sh` - FFI testing
- `tests/integration/test_upload_download.sh` - File transfer tests
- `tests/integration/test_upload_download_cross_device.sh` - Cross-device transfers
- `tests/communication/test_communication.sh` - P2P communication tests
- `tests/test_rpc.py` - RPC integration tests

**Quick Run:**
```bash
./scripts/setup.sh
# Select: 7 - Run All Localhost Tests
```

---

## 📚 Testing Documentation

### Comprehensive Guides
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Complete testing guide for all phases
- **[../TESTING_QUICK_START.md](../TESTING_QUICK_START.md)** - Quick commands reference
- **[../START_HERE.md](../START_HERE.md)** - Testing overview and navigation
- **[../../tests/README.md](../../tests/README.md)** - Test directory overview

### Phase-Specific Documentation
- **[PHASE1_TEST_SUITE.md](PHASE1_TEST_SUITE.md)** - Phase 1 testing details
- **[PHASE2_TEST_SUITE.md](PHASE2_TEST_SUITE.md)** - Phase 2 testing details
- **[COMPUTE_TEST_SUITE.md](COMPUTE_TEST_SUITE.md)** - Compute system testing
- **[ALL_TESTS_REFERENCE.md](ALL_TESTS_REFERENCE.md)** - Complete test inventory

### Testing Scenarios
- **[../CROSS_DEVICE_TESTING.md](../CROSS_DEVICE_TESTING.md)** - Multi-device testing
- **[../CONTAINERIZED_TESTING.md](../CONTAINERIZED_TESTING.md)** - Docker-based testing
- **[../LIVE_TEST_GUIDE.md](../LIVE_TEST_GUIDE.md)** - Live network testing
- **[../EASY_TEST.md](../EASY_TEST.md)** - Simplified testing workflow

---

## 🔧 Test Infrastructure

### Test Scripts Reference

#### Main Test Scripts
| Script | Purpose | Command |
|--------|---------|---------|
| `setup.sh` | Interactive test menu | `./scripts/setup.sh` |
| `test_all.sh` | Run complete test suite | `./tests/test_all.sh` |
| `verify_setup.sh` | Verify installation | `./scripts/verify_setup.sh` |

#### Component Tests
| Script | Tests | Location |
|--------|-------|----------|
| `test_go.sh` | Go build and CLI | `./tests/test_go.sh` |
| `test_python.sh` | Python environment | `./tests/test_python.sh` |
| `test_rust.sh` | Rust build and tests | `./tests/test_rust.sh` |
| `test_paths.sh` | Path resolution | `./tests/test_paths.sh` |

#### Phase Tests
| Script | Phase | Location |
|--------|-------|----------|
| `test_phase1_features.sh` | Phase 1 | `./tests/test_phase1_features.sh` |
| `test_phase1_benchmarks.sh` | Phase 1 Bench | `./tests/test_phase1_benchmarks.sh` |
| `test_phase2_structure.py` | Phase 2 | `pytest tests/test_phase2_structure.py` |
| `test_phase2_modules.py` | Phase 2 | `pytest tests/test_phase2_modules.py` |

#### Compute Tests
| Script | Purpose | Location |
|--------|---------|----------|
| `test_compute.sh` | Full compute suite | `./tests/compute/test_compute.sh` |
| `03_distributed_compute.sh` | Cross-device compute | `./tests/compute/examples/03_distributed_compute.sh` |
| `04_ces_pipeline.sh` | CES pipeline | `./tests/compute/examples/04_ces_pipeline.sh` |

#### Integration Tests
| Script | Purpose | Location |
|--------|---------|----------|
| `test_integration.sh` | Full integration | `./tests/integration/test_integration.sh` |
| `test_localhost_full.sh` | Localhost full | `./tests/integration/test_localhost_full.sh` |
| `test_ffi_integration.sh` | FFI testing | `./tests/integration/test_ffi_integration.sh` |
| `test_upload_download.sh` | File transfers | `./tests/integration/test_upload_download.sh` |

#### Network Tests
| Script | Purpose | Location |
|--------|---------|----------|
| `test_communication.sh` | P2P communication | `./tests/communication/test_communication.sh` |
| `test_streaming.sh` | Streaming protocol | `./tests/streaming/test_streaming.sh` |
| `test_mdns.sh` | mDNS discovery | `./scripts/test_mdns.sh` |
| `cross_device_streaming_test.sh` | Cross-device streaming | `./scripts/cross_device_streaming_test.sh` |

---

## 📊 Current Test Status

### Overall Status: ✅ 86+ Tests Passing

#### Breakdown by Component
- **Rust Tests:** 61 passing
  - Compute engine: 27 tests
  - CES pipeline: 12 tests
  - Streaming: 12 tests
  - Integration: 7 tests
  - Phase 1: 3 tests
- **Go Tests:** 13+ passing
  - Task manager: 8 tests
  - Scheduler: 5 tests
- **Python Tests:** All passing
  - Phase 2 structure: 6 tests
  - Phase 2 modules: 8 tests
  - RPC client: Multiple tests
  - SDK tests: All passing

#### Test Coverage by Feature
| Feature | Tests | Status |
|---------|-------|--------|
| WASM Sandbox | 27 | ✅ All passing |
| Task Management | 13 | ✅ All passing |
| Streaming | 12 | ✅ All passing |
| CES Pipeline | 12 | ✅ All passing |
| Phase 2 Framework | 14 | ✅ All passing |
| Integration | 7+ | ✅ All passing |
| Phase 1 Features | 3 | ✅ All passing |

---

## 🚀 Running Tests

### Quick Test (30 seconds)
```bash
./scripts/setup.sh
# Select: 7 - Run All Localhost Tests
```

### Full Test Suite (5-10 minutes)
```bash
./tests/test_all.sh
```

### Specific Phase Tests
```bash
# Phase 1
./tests/test_phase1_features.sh

# Phase 2
pytest tests/test_phase2_structure.py tests/test_phase2_modules.py -v

# Compute System
./tests/compute/test_compute.sh
```

### Cross-Device Testing
```bash
./scripts/setup.sh
# Select: 2 - Establish Network Connection
# Follow prompts for Manager/Worker setup
```

### Integration Tests
```bash
./tests/integration/test_localhost_full.sh
```

---

## 🐛 Debugging Failed Tests

### Check Test Logs
```bash
# View recent test logs
tail -f ~/.pangea/node-*/logs/*.log

# Check specific test output
./tests/test_all.sh 2>&1 | tee test_output.log
```

### Common Issues

#### Build Failures
```bash
# Verify dependencies
./scripts/verify_setup.sh

# Clean and rebuild
cd rust && cargo clean && cargo build --release
cd go && go clean && go build
```

#### Connection Issues
```bash
# Check port availability
netstat -tuln | grep -E '8080|9081|9082'

# Test local connectivity
./scripts/check_network.sh
```

#### Permission Issues
```bash
# Fix permissions on scripts
chmod +x scripts/*.sh tests/**/*.sh

# Check library paths
echo $LD_LIBRARY_PATH
```

---

## 📈 Test Metrics

### Performance Benchmarks
- **P2P Latency:** 0.33ms average (294x better than 100ms target)
- **Voice Processing:** 10ms frame duration
- **Large File:** 60MB video in 262ms
- **Compression:** 20.87x for voice, 12.16x for data

### Test Execution Times
- **Unit Tests:** < 1 minute
- **Integration Tests:** 2-3 minutes
- **Full Suite:** 5-10 minutes
- **Cross-Device:** 3-5 minutes (after setup)

---

## 🔄 Continuous Integration

### GitHub Actions (if configured)
```yaml
# Run on every push
- Phase 1 tests
- Phase 2 structure tests
- Compute unit tests
- Integration tests
```

### Local CI Simulation
```bash
# Run all automated tests
./scripts/test_automated.sh
```

---

## 📝 Writing New Tests

### Test Guidelines
1. Follow existing test structure in respective phase directories
2. Use descriptive test names
3. Include assertions with clear messages
4. Clean up resources after tests
5. Document test purpose and expected behavior

### Test Templates
See existing tests for templates:
- Rust: `rust/tests/phase1_features_test.rs`
- Go: `go/pkg/compute/manager_test.go`
- Python: `tests/test_phase2_structure.py`
- Shell: `tests/test_phase1_features.sh`

---

## 🆘 Getting Help

### Documentation
- Check this index for relevant documentation
- Review phase-specific test suite docs
- See troubleshooting guides

### Resources
- **Main Docs:** `docs/DOCUMENTATION_INDEX.md`
- **Setup Guide:** `docs/SETUP_GUIDE.md`
- **Quick Start:** `docs/TESTING_QUICK_START.md`
- **GitHub Issues:** Report problems on GitHub

---

## ✅ Testing Checklist

Before committing changes:
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] No new warnings or errors
- [ ] Documentation updated if needed
- [ ] New tests added for new features
- [ ] Cross-device testing performed (if applicable)

---

**Version:** 0.6.0-alpha  
**Last Updated:** 2025-12-07  
**Status:** Complete and up-to-date ✅
