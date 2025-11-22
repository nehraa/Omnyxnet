# Cap'n Proto Service Documentation

**File**: `go/capnp_service.go`  
**Last Updated**: November 22, 2025  
**Status**: ✅ Upload & Download Fully Wired

## Overview

The Cap'n Proto Service implements the RPC interface for Pangea Net node communication. It provides methods for file upload, download, and node management.

## Key RPC Methods

### Upload Method

**Status**: ✅ Fully Implemented  
**Location**: Lines 579-700

**Flow**:
1. Receives file data from client
2. Calls Rust CES pipeline: Compress → Encrypt → Shard (Reed-Solomon 8+4)
3. Distributes shards to connected peers via NetworkAdapter
4. Returns manifest with shard locations

**Code Structure**:
```go
func (s *CapnpService) Upload(call pangea.NodeService_upload) error {
    // 1. Read file data from request
    // 2. Call CES process: s.ces.Process(data)
    // 3. Distribute shards to peers
    // 4. Return manifest
}
```

**Recent Changes** (Nov 22, 2025):
- Integrated with Rust CES FFI for actual compression/encryption/sharding
- Shard distribution via NetworkAdapter.SendMessage()
- No longer a placeholder

### Download Method

**Status**: ✅ Fully Implemented  
**Location**: Lines 702-779

**Flow**:
1. Receives shard locations from manifest
2. Fetches shards from peers using `NetworkAdapter.FetchShard()`
3. Checks minimum required shards (8 of 12 for Reed-Solomon)
4. Calls Rust CES reconstruct: Unshard → Decrypt → Decompress
5. Returns reconstructed file data

**Code Structure**:
```go
func (s *CapnpService) Download(call pangea.NodeService_download) error {
    // 1. Parse shard locations
    // 2. Fetch shards via network.FetchShard(peerID, shardIndex)
    // 3. Verify minimum shard count (need 8 of 12)
    // 4. Call CES reconstruct
    // 5. Return data
}
```

**Recent Changes** (Nov 22, 2025):
- **Removed**: "TODO: Implement actual shard fetching" placeholder
- **Added**: Actual shard fetching loop calling `s.network.FetchShard()`
- **Added**: Minimum shard count validation (8 required for Reed-Solomon)
- **Integrated**: Rust CES reconstruct for decryption/decompression

## FetchShard Protocol

**Request Format**:
- Byte 0: Request type (0x01 for shard fetch)
- Bytes 1-4: Shard index (uint32, big-endian)

**Response**:
- Raw shard data (up to 1MB per shard)

**Error Handling**:
- Returns error if peer unreachable
- Returns error if shard not found
- Continues fetching other shards on individual failures

## Shard Distribution

### Reed-Solomon Encoding
- **Data shards**: 8
- **Parity shards**: 4
- **Total**: 12 shards
- **Minimum required**: 8 shards (any 8 of 12 can reconstruct)

### Distribution Strategy
Currently distributes shards round-robin to connected peers. Future enhancements could include:
- Geographic distribution
- Redundancy optimization
- Load balancing

## Integration Points

### NetworkAdapter
- `SendMessage()`: Distributes shards during upload
- `FetchShard()`: Retrieves shards during download
- `GetConnectedPeers()`: Gets available storage peers

### CES Pipeline (Rust FFI)
- `Process()`: Upload compression/encryption/sharding
- `Reconstruct()`: Download unsharding/decryption/decompression

## Testing

**Current Status**: Backend fully implemented, awaiting Python CLI

### Test Coverage
- ✅ Unit tests pass (Rust CES: 12/12)
- ✅ Go builds successfully
- ✅ Multi-node startup verified
- ⏳ End-to-end testing pending Python CLI

### Manual Testing
```bash
# Start 3 nodes for testing
./tests/test_upload_download_local.sh
```

## Known Limitations

1. **No Python CLI yet**: RPC methods work but no command-line interface
2. **Shard storage**: Peers receive shards but storage layer needs verification
3. **No manifest persistence**: Manifests not saved to disk yet

## Future Enhancements

- [ ] Python CLI for `pangea upload <file>` and `pangea download <hash>`
- [ ] Persistent shard storage on peers
- [ ] Manifest database/cache
- [ ] Partial download support
- [ ] Download progress tracking
- [ ] Bandwidth throttling

## Related Files

- `go/network_adapter.go` - Network layer for shard transfer
- `rust/src/ces.rs` - CES pipeline implementation
- `go/ces_ffi.go` - FFI bridge to Rust
- `tests/test_upload_download_local.sh` - Integration test
