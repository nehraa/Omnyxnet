# Pangea Net - Complete Setup Guide

This guide covers the complete setup process from scratch, including all dependencies, builds, and testing.

## Quick Start

For the fastest setup experience:

```bash
./setup.sh
# Select option 1: Full Installation
# Then select option 7: Run All Localhost Tests
```

## System Requirements

- **OS**: Linux (Ubuntu/Debian) or macOS
- **Go**: 1.20 or later
- **Rust**: Latest stable (1.70+)
- **Python**: 3.8 or later
- **Cap'n Proto**: 0.9 or later
- **Disk Space**: ~1GB for minimal install, ~5GB for full install with AI features

## Installation Steps

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y build-essential pkg-config libssl-dev capnproto python3 python3-pip python3-venv
```

**macOS:**
```bash
brew install capnp openssl pkg-config python3
```

### 2. Install Language Tools

**Go:**
```bash
wget https://go.dev/dl/go1.24.0.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.24.0.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
```

**Rust:**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

### 3. Build All Components

The setup script handles the correct build order automatically:

```bash
./setup.sh
# Select option 1: Full Installation
```

**Build order (automatically handled):**
1. Rust library (`libpangea_ces.so`) - needed for Go FFI
2. Go node (`go/bin/go-node`)
3. Rust binary (`rust/target/release/pangea-rust-node`)
4. Python virtual environment with dependencies

### 4. Python Dependencies

Two options:

**Option A: Minimal (Recommended for testing, ~200MB)**
```bash
cd python
source .venv/bin/activate
pip install -r requirements-minimal.txt
```

**Option B: Full with AI features (~5GB)**
```bash
cd python
source .venv/bin/activate
pip install -r requirements.txt
```

## Testing

### Automated Testing

Use the setup.sh menu for comprehensive testing:

```bash
./setup.sh
```

**Menu Options:**
- **Option 7**: Run All Localhost Tests (recommended)
- **Option 8**: Run Comprehensive Localhost Test (Multi-node)
- **Option 9**: Setup Cross-Device/WAN Testing
- **Option 2-6**: Run individual component tests
- **Option 10-13**: Run specific feature tests

### Manual Testing

**Run all localhost tests:**
```bash
bash tests/test_all.sh
```

**Run individual tests:**
```bash
# Test Go
bash tests/test_go.sh

# Test Rust
bash tests/test_rust.sh

# Test Python
bash tests/test_python.sh

# Test FFI integration
bash tests/test_ffi_integration.sh

# Test upload/download
bash tests/test_upload_download_local.sh
```

### Cross-Device Testing

For testing across multiple devices or WAN:

1. **On Device 1 (Bootstrap node):**
   ```bash
   ./scripts/easy_test.sh 1
   # Note the connection info displayed
   ```

2. **On Device 2+ (Joining nodes):**
   ```bash
   ./scripts/easy_test.sh
   # Follow prompts to enter bootstrap node info
   ```

## Verifying Installation

After running the setup, verify everything is working:

```bash
# Check binaries exist
ls -lh go/bin/go-node
ls -lh rust/target/release/pangea-rust-node
ls -lh rust/target/release/libpangea_ces.so

# Check Python venv
source python/.venv/bin/activate
python -c "import capnp; print('pycapnp installed')"
deactivate

# Run quick test
bash tests/test_compilation.sh
```

## Common Issues

### Issue: "libpangea_ces.so: cannot open shared object file"

**Solution:** Set library path before running Go node:
```bash
export LD_LIBRARY_PATH="$(pwd)/rust/target/release:$LD_LIBRARY_PATH"
```

Or use the scripts which handle this automatically.

### Issue: "No module named 'capnp'"

**Solution:** Activate Python venv and install dependencies:
```bash
cd python
source .venv/bin/activate
pip install -r requirements-minimal.txt
```

### Issue: "Port already in use"

**Solution:** Stop existing nodes:
```bash
pkill -f go-node
pkill -f pangea-rust-node
```

### Issue: "Out of disk space" during Python install

**Solution:** Use minimal requirements instead:
```bash
cd python
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-minimal.txt
```

## Directory Structure

```
WGT/
├── setup.sh                    # Main setup and testing menu
├── go/
│   ├── bin/go-node            # Go binary (primary location)
│   └── go-node                # Go binary (backward compat)
├── rust/
│   └── target/release/
│       ├── pangea-rust-node   # Rust binary
│       └── libpangea_ces.so   # Rust library for FFI
├── python/
│   ├── .venv/                 # Python virtual environment
│   ├── requirements.txt       # Full requirements (with torch)
│   └── requirements-minimal.txt  # Minimal requirements (testing)
├── tests/                     # All test scripts
│   ├── test_all.sh           # Comprehensive test suite
│   ├── test_go.sh
│   ├── test_rust.sh
│   ├── test_python.sh
│   └── ...
└── scripts/
    └── easy_test.sh          # Cross-device setup helper
```

## Environment Variables

Key environment variables used:

- `LD_LIBRARY_PATH`: Path to Rust library (for Linux)
- `DYLD_LIBRARY_PATH`: Path to Rust library (for macOS)
- `PANGEA_CACHE_DIR`: Override default cache location
- `PATH`: Should include Go bin directory

## Next Steps

After successful setup:

1. **Read the architecture docs:**
   - START_HERE.md - Overview
   - QUICK_START.md - Basic usage
   - TESTING_QUICK_START.md - Testing guide
   - CROSS_DEVICE_TESTING.md - Advanced testing

2. **Try the examples:**
   ```bash
   # Start a node
   ./scripts/easy_test.sh 1
   
   # Run multi-node test
   bash tests/test_localhost_full.sh
   ```

3. **Development:**
   - Modify code in go/, rust/, or python/
   - Rebuild: `./setup.sh` → Option 1
   - Test: `./setup.sh` → Option 7

## Test Coverage

Current test results (7/10 passing):

✅ **Passing Tests:**
1. Python Component
2. Go Node
3. Rust Node
4. FFI Integration (Go-Rust)
5. Upload/Download (Local)
6. Compilation Verification
7. Multi-node Startup

⚠️ **Known Issues (pre-existing):**
8. Integration Tests - Cap'n Proto schema import issue
9. Stream Updates - Cap'n Proto schema import issue
10. CES Wiring - Cap'n Proto schema import issue

The failing tests have a common root cause (Cap'n Proto schema import) that predates this setup automation work.

## Support

For issues or questions:
- Check existing documentation in docs/
- Review test logs in /tmp/ or project root
- Use `./setup.sh` option 14/15 to view setup and test logs
