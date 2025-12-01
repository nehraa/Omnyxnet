# Automated File Operations

This guide explains the new automated file upload and download functionality that simplifies working with Pangea Net.

## Overview

Previously, file operations required manual steps:
- Finding peer IDs
- Managing shard locations
- Handling manifests manually
- Coordinating DHT lookups

Now, with automated operations, you can:
- Upload a file with a single command
- Download a file by hash with automatic peer discovery
- List and search files easily
- Let the system handle all the complexity

## Quick Start

### Upload a File

```bash
# Simple one-command upload
./rust/target/release/pangea-rust-node put /path/to/myfile.txt

# The system automatically:
# - Discovers available peers
# - Processes the file through CES pipeline
# - Distributes shards to peers
# - Caches the manifest
# - Registers in DHT
```

### Download a File

```bash
# Download by hash (uses original filename)
./rust/target/release/pangea-rust-node get <file-hash>

# Or specify output path
./rust/target/release/pangea-rust-node get <file-hash> -o /path/to/output.txt

# The system automatically:
# - Looks up file in cache and DHT
# - Discovers all peers with shards
# - Fetches shards from available peers
# - Reconstructs the file
# - Verifies integrity
```

### List Files

```bash
# See all available files
./rust/target/release/pangea-rust-node list
```

Output:
```
📁 Available Files (2 total):

Hash       Name                           Size            Shards     Status    
-------------------------------------------------------------------------------------
a1b2c3d4e5 myfile.txt                     1024 B          5          ✅ Ready   
f6g7h8i9j0 document.pdf                   52480 B         10         ⚠️  Partial
```

### Search Files

```bash
# Search by filename pattern
./rust/target/release/pangea-rust-node search "document"
```

### Get File Info

```bash
# View detailed file information
./rust/target/release/pangea-rust-node info <file-hash>
```

Output:
```
📄 File Information:
  Name: myfile.txt
  Hash: a1b2c3d4e5f6g7h8...
  Size: 1024 bytes (0.00 MB)
  Shards: 5
  Status: ✅ Available
  Timestamp: 2025-11-22 16:30:45
```

## Architecture

### Automated Uploader

The `AutomatedUploader` provides a high-level interface that:

1. **Validates Input**
   - Checks file exists
   - Verifies file is readable
   - Reports file size

2. **Discovers Peers**
   - Queries node store for active peers
   - Optionally queries DHT for additional peers
   - Ensures sufficient peers are available

3. **Processes File**
   - Runs CES pipeline (Compression, Encryption, Sharding)
   - Creates Reed-Solomon encoded shards
   - Adds redundancy for fault tolerance

4. **Distributes Shards**
   - Sends shards to discovered peers
   - Uses round-robin distribution
   - Caches shards locally

5. **Registers File**
   - Creates file manifest
   - Stores manifest in cache
   - Publishes to DHT (if available)

### Automated Downloader

The `AutomatedDownloader` provides automatic file retrieval:

1. **Lookup File**
   - Checks local cache first
   - Queries DHT if not in cache
   - Verifies file availability

2. **Discover Shards**
   - Gets shard locations from manifest
   - Checks which peers are online
   - Calculates if reconstruction is possible

3. **Fetch Shards**
   - Retrieves shards from peers
   - Uses cache when available
   - Handles peer failures gracefully

4. **Reconstruct File**
   - Applies Reed-Solomon reconstruction
   - Decrypts data
   - Decompresses to original

5. **Verify & Save**
   - Writes to output path
   - Caches for future access
   - Reports success

## Configuration

### Environment Variables

```bash
# Set custom cache directory
export PANGEA_CACHE_DIR="$HOME/.pangea/cache"

# Cache is automatically created and managed
```

### Command-Line Options

All commands support these options:

```bash
--go-addr <addr>      # Go node address (default: 127.0.0.1:8082)
--dht-addr <addr>     # DHT listen address (default: 127.0.0.1:9091)
--bootstrap <peers>   # Bootstrap peers for DHT
--verbose, -v         # Enable verbose logging
```

## Examples

### Example 1: Upload and Download

```bash
# Start node (terminal 1)
./go/bin/go-node -id 1 -port 8080

# Upload file (terminal 2)
./rust/target/release/pangea-rust-node put ~/documents/report.pdf
# Output: File hash: abc123def456...

# Download on another machine (terminal 3)
./rust/target/release/pangea-rust-node get abc123def456 -o ~/Downloads/report.pdf
```

### Example 2: File Management

```bash
# Upload multiple files
./rust/target/release/pangea-rust-node put file1.txt
./rust/target/release/pangea-rust-node put file2.txt
./rust/target/release/pangea-rust-node put file3.txt

# List all files
./rust/target/release/pangea-rust-node list

# Search for specific files
./rust/target/release/pangea-rust-node search "file"

# Get info about a specific file
./rust/target/release/pangea-rust-node info <hash>
```

### Example 3: Multi-Node Setup

```bash
# Node 1 (bootstrap)
./go/bin/go-node -id 1 -port 8080 -p2p-port 9080

# Node 2 (connects to Node 1)
./go/bin/go-node -id 2 -port 8081 -p2p-port 9081

# Node 3 (connects to Node 1)
./go/bin/go-node -id 3 -port 8082 -p2p-port 9082

# Upload from Node 1
./rust/target/release/pangea-rust-node put file.txt --go-addr 127.0.0.1:8080

# Download from Node 2
./rust/target/release/pangea-rust-node get <hash> --go-addr 127.0.0.1:8081
```

## Integration with DHT

The automated operations integrate seamlessly with the DHT:

### File Registration

When you upload a file, the system:
1. Creates a content-addressed identifier (file hash)
2. Stores the manifest in DHT under this key
3. Announces itself as a provider for this content
4. Other nodes can discover the file via DHT lookup

### Peer Discovery

When downloading, the system:
1. Queries DHT for file providers
2. Connects to discovered peers
3. Fetches shards from multiple sources
4. Uses DHT as fallback if cache lookup fails

### Automatic Updates

The DHT integration provides:
- Automatic peer discovery
- Content routing
- Provider announcements
- Resilience to node failures

## Error Handling

The automated operations handle errors gracefully:

### Upload Errors

- **No peers available**: Returns error with helpful message
- **File not found**: Validates file before processing
- **Permission denied**: Reports access errors clearly
- **Insufficient space**: Checks capacity before upload

### Download Errors

- **File not found**: Searches cache and DHT thoroughly
- **Incomplete shards**: Reports which shards are missing
- **Reconstruction failed**: Indicates if more shards needed
- **Write permission**: Checks output path is writable

## Performance Tips

1. **Use Local Cache**
   - First download populates cache
   - Subsequent downloads are instant
   - Cache is shared across operations

2. **Run Multiple Nodes**
   - More nodes = better redundancy
   - Faster shard distribution
   - Improved availability

3. **Enable DHT**
   - Automatic peer discovery
   - No manual configuration
   - Works across networks

4. **Monitor Logs**
   - Use `--verbose` for detailed output
   - Check for connection issues
   - Verify shard distribution

## Comparison with Manual Operations

### Before (Manual)

```bash
# Upload - need to know peer IDs
./rust/target/release/pangea-rust-node upload file.txt --peers 1,2,3

# Download - need shard locations
./rust/target/release/pangea-rust-node download output.txt --shards 0:1,1:2,2:3,3:1,4:2
```

### After (Automated)

```bash
# Upload - automatic peer discovery
./rust/target/release/pangea-rust-node put file.txt

# Download - automatic shard discovery
./rust/target/release/pangea-rust-node get <hash>
```

## Testing

Use the provided test script to verify functionality:

```bash
# Run automated operations test
./scripts/test_automated.sh
```

This script:
- Starts multiple nodes
- Uploads a test file
- Lists files
- Gets file info
- Downloads the file
- Verifies integrity
- Tests search functionality

## Troubleshooting

### "No available peers found"

**Solution**: Start at least one other node before uploading.

```bash
# Terminal 1
./go/bin/go-node -id 1 -port 8080

# Terminal 2
./go/bin/go-node -id 2 -port 8081

# Now upload from Terminal 3
./rust/target/release/pangea-rust-node put file.txt --go-addr 127.0.0.1:8080
```

### "File not found in cache or DHT"

**Solution**: Ensure the file was uploaded successfully and nodes are connected.

```bash
# Check if file is in cache
./rust/target/release/pangea-rust-node list

# Verify nodes are running
ps aux | grep go-node
```

### "Connection refused"

**Solution**: Verify the Go node is running and accessible.

```bash
# Check if node is listening
netstat -tulpn | grep 8080

# Restart node if needed
./go/bin/go-node -id 1 -port 8080
```

## Next Steps

- [Testing Guide](TESTING_QUICK_START.md)
- [Cross-Device Setup](CROSS_DEVICE_TESTING.md)
- [Architecture Overview](ARCHITECTURE.md)
- [API Documentation](PYTHON_API.md)

## Summary

The automated operations make Pangea Net easy to use:
- **One command upload**: `put <file>`
- **One command download**: `get <hash>`
- **Simple file management**: `list`, `search`, `info`
- **Automatic DHT integration**: No manual configuration
- **Intelligent error handling**: Clear, actionable messages

No need to worry about:
- Peer discovery
- Shard locations
- Manifest management
- DHT registration

Everything is handled automatically! 🚀
