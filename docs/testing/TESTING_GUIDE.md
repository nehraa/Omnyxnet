# Testing Documentation

**Last Updated**: November 22, 2025

## Test Structure

```
tests/
├── test_all.sh                          # Master test suite
├── test_upload_download_local.sh        # Localhost multi-node test
└── test_upload_download_cross_device.sh # Cross-device test guide
```

## Test Suite: test_all.sh

**Status**: ✅ All 4 tests passing

**Coverage**:

1. Python syntax and structure validation
2. Go build, binary, and CLI
3. Rust build and unit tests (12/12)
4. Multi-node startup (Go + Rust)

**Run**:

```bash
./tests/test_all.sh
```

## Localhost Multi-Node Testing

**File**: `tests/test_upload_download_local.sh`  
**Status**: ✅ Infrastructure complete, awaiting Python CLI

### Features

- Starts 3 nodes on same machine
- Uses `-local` flag for mDNS discovery
- No bootstrap required for localhost
- Automatic peer discovery (mDNS-based)

### Important Notes

**mDNS Status**: 
- mDNS discovery is implemented but auto-connect may not be fully working
- Nodes detect each other but may not automatically connect
- **Workaround**: For cross-device, use explicit `-peers` flag with multiaddr
- For localhost testing, nodes should discover via mDNS

**Bootstrap Flag**:
- `-peers` flag: For cross-device connections (requires bootstrap multiaddr)
- `-local` flag: For localhost testing (mDNS discovery)
- **Do NOT use `-peers` for localhost tests** - use `-local` instead

### Usage

```bash
cd /home/abhinav/Desktop/program/WGT
./tests/test_upload_download_local.sh
```

### What It Tests

- ✅ 3 nodes start successfully
- ✅ Nodes bind to different ports (18080, 18081, 18082)
- ✅ Each node gets unique peer ID
- ✅ Logs captured for debugging
- ⏳ Upload/download pending Python CLI

### Test Output

```
========================================
🧪 Upload/Download Test (Localhost)
========================================

✓ Created test file: /tmp/pangea-test-upload-download/test_file.txt
  Original hash: 79fad44265f7b555044993003381513b5d0c707e173584ce5f8e87f3ce82b2c5

Starting test nodes...
✓ Node 1 started (PID: 9857)
  Multiaddr: /ip4/127.0.0.1/tcp/35737/p2p/12D3KooW...
✓ Node 2 started (PID: 9900)
✓ Node 3 started (PID: 9936)

Waiting for peer discovery...
```

## Cross-Device Testing

**File**: `tests/test_upload_download_cross_device.sh`  
**Status**: ✅ Connection verified, upload/download pending Python CLI

### Features

- Interactive guide for 2-device testing
- Bootstrap node on Device 1
- Joining node on Device 2
- Manual multiaddr exchange

### Important Notes

**Connection Method**:
- Device 1: Runs bootstrap node (no `-peers` needed)
- Device 2: Uses `-peers` flag with Device 1's multiaddr
- Format: `/ip4/<IP>/tcp/<PORT>/p2p/<PEER_ID>`
- **Status**: ✅ Connections working reliably with IP/port/peerID

**mDNS Note**:
- mDNS is for local network discovery only
- Cross-device requires manual multiaddr exchange
- This is expected behavior and working as designed

### Usage

```bash
# On Device 1
./tests/test_upload_download_cross_device.sh
# Select option 1

# Copy the multiaddr output, then on Device 2
./tests/test_upload_download_cross_device.sh  
# Select option 2
# Paste the multiaddr when prompted
```

### Verified Working

- ✅ SSH connectivity between devices
- ✅ Bootstrap node starts and advertises
- ✅ Joining node connects successfully
- ✅ Peer-to-peer communication established

## Pending: Python CLI Integration

### What's Missing

The RPC layer is fully implemented, but there's no command-line interface yet:

```bash
# These commands don't exist yet but RPC methods are ready:
pangea upload /path/to/file
pangea download <file_hash>
```

### Current RPC Status

**Upload RPC**: ✅ Complete
- Accepts file data
- Calls Rust CES (compress/encrypt/shard)
- Distributes shards to peers
- Returns manifest

**Download RPC**: ✅ Complete
- Accepts shard locations
- Fetches via NetworkAdapter.FetchShard()
- Calls Rust CES (reconstruct/decrypt/decompress)
- Returns file data

### Testing Workaround

Until Python CLI is ready, test via:

1. **Direct RPC calls**: Use Cap'n Proto client
2. **Unit tests**: Test individual components
3. **Multi-node startup**: Verify infrastructure

## Test Results Summary

**Date**: November 22, 2025

| Component | Status | Details |
|-----------|--------|---------|
| Python validation | ✅ Pass | Syntax and structure |
| Go build | ✅ Pass | Binary 33MB |
| Rust tests | ✅ Pass | 12/12 unit tests |
| Multi-node | ✅ Pass | Go + Rust nodes |
| Localhost test | ✅ Pass | 3 nodes start |
| Cross-device | ✅ Pass | Connection works |
| Upload RPC | ✅ Complete | Awaiting CLI |
| Download RPC | ✅ Complete | Awaiting CLI |
| End-to-end | ⏳ Pending | Need Python CLI |

## Running All Tests

```bash
# Run full test suite
cd /home/abhinav/Desktop/program/WGT
./tests/test_all.sh

# Test localhost multi-node
./tests/test_upload_download_local.sh

# Check build status
cd go && go build
cd ../rust && cargo test
```

## Known Issues

1. **mDNS auto-connect**: Discovery works but auto-connect may not trigger
   - **Workaround**: Use explicit `-peers` flag for cross-device
   - **Status**: Not blocking - manual connection works

2. **Python CLI missing**: Backend ready, frontend needed
   - **Impact**: Can't test end-to-end upload/download from CLI
   - **Workaround**: Test via direct RPC calls

3. **Peer count shows 0**: Nodes start but may not show connections
   - **Cause**: mDNS auto-connect timing or implementation
   - **Status**: Non-critical for testing infrastructure

## Next Steps

1. **Implement Python CLI** (`python/cli.py`)
   - Add `upload` command
   - Add `download` command
   - Integrate with Cap'n Proto client

2. **End-to-end test**
   - Upload file from Node 1
   - Download from Node 2
   - Verify SHA256 hash match

3. **Improve mDNS** (optional)
   - Debug auto-connect timing
   - Add explicit peer connection on discovery
   - Not critical since manual connection works

## Related Documentation

- Network Adapter: `docs/networking/NETWORK_ADAPTER.md`
- Cap'n Proto Service: `docs/api/CAPNP_SERVICE.md`
- Quick Start: `QUICK_START.md` (root directory)
