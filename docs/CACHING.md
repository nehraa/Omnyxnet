# Caching and Lookup System - Complete Guide

## Overview

The caching and lookup system provides efficient local storage and network-wide file discovery for the Pangea Net decentralized storage network. It significantly improves performance by reducing redundant network requests and provides a powerful mechanism for locating files across the distributed network.

## Architecture

### Components

1. **Cache Module** (`rust/src/cache.rs`)
   - LRU-based shard caching
   - Persistent manifest storage
   - Automatic eviction policies
   - Cache statistics and monitoring

2. **Lookup Module** (`rust/src/lookup.rs`)
   - Local cache lookups
   - DHT-based file discovery
   - Availability checking
   - File search capabilities

3. **Integration**
   - Automatic caching during uploads
   - Cache-first downloads
   - DHT registration for uploaded files

## Cache Module

### Key Features

#### 1. Shard Caching
- **LRU (Least Recently Used) eviction**: Automatically removes oldest shards when cache is full
- **Size limits**: Configurable maximum cache size in bytes
- **Per-shard storage**: Each shard is cached independently with its file hash and index

#### 2. Manifest Storage
- **Persistent storage**: Manifests are saved to disk as JSON files
- **Automatic loading**: Manifests are loaded on node startup
- **File metadata**: Stores file name, size, shard locations, and timestamps

#### 3. Cache Statistics
- Track cache hits and misses
- Monitor total cache size
- Count cached shards and manifests

### Usage Examples

#### Creating a Cache

```rust
use pangea_rust_node::Cache;
use std::path::Path;

// Create cache with 1000 entries max, 100MB max size
let cache = Cache::new(
    Path::new("/var/cache/pangea"),
    1000,  // max entries
    100 * 1024 * 1024  // 100 MB
)?;
```

#### Caching Shards

```rust
// Store a shard
let file_hash = "abc123...";
let shard_index = 0;
let shard_data = vec![1, 2, 3, 4, 5];

cache.put_shard(file_hash, shard_index, shard_data).await?;

// Retrieve a shard
if let Some(data) = cache.get_shard(file_hash, shard_index).await {
    println!("Cache hit! Got {} bytes", data.len());
}
```

#### Managing Manifests

```rust
use pangea_rust_node::FileManifest;
use chrono::Utc;

// Create a manifest
let manifest = FileManifest {
    file_hash: "abc123...".to_string(),
    file_name: "document.pdf".to_string(),
    file_size: 1024000,
    shard_count: 10,
    shard_locations: vec![(0, 1), (1, 2), (2, 3)],
    timestamp: Utc::now().timestamp(),
    ttl: 3600,  // 1 hour TTL
};

// Cache the manifest
cache.put_manifest(manifest).await?;

// Retrieve it
if let Some(manifest) = cache.get_manifest("abc123...").await {
    println!("Found file: {}", manifest.file_name);
}
```

#### Cache Statistics

```rust
// Get cache statistics
let stats = cache.get_stats().await;
println!("Cache Stats:");
println!("  Shard hits: {}", stats.shard_hits);
println!("  Shard misses: {}", stats.shard_misses);
println!("  Total shards cached: {}", stats.total_shards_cached);
println!("  Cache size: {} bytes", stats.cache_size_bytes);
```

#### Cache Management

```rust
// List all cached files
let manifests = cache.list_manifests().await;
for manifest in manifests {
    println!("{}: {} ({} bytes)", 
        manifest.file_hash, 
        manifest.file_name,
        manifest.file_size
    );
}

// Remove a specific manifest
cache.remove_manifest("abc123...").await?;

// Clear all shards (keep manifests)
cache.clear_shards().await?;

// Clear everything
cache.clear_manifests().await?;
cache.clear_shards().await?;
```

## Lookup Module

### Key Features

#### 1. Multi-Source Lookup
- Check local cache first
- Query DHT if not in cache
- Peer-to-peer queries (future)

#### 2. Availability Checking
- Verify which shards are available
- Check if file is fully reconstructible
- Track peer online status

#### 3. File Search
- Search by file name pattern
- List all cached files
- Discover files in the network

### Usage Examples

#### Creating a Lookup Service

```rust
use pangea_rust_node::{Cache, LookupService, NodeStore};
use std::sync::Arc;

let cache = Arc::new(Cache::new("/var/cache/pangea", 1000, 100 * 1024 * 1024)?);
let store = Arc::new(NodeStore::new());
let dht = None; // Or Some(Arc::new(RwLock::new(dht_node)))

let lookup = LookupService::new(cache, dht, store);
```

#### Looking Up Files

```rust
// Lookup a file by hash
if let Some(result) = lookup.lookup_file("abc123...").await? {
    println!("File: {}", result.manifest.file_name);
    println!("Available shards: {}/{}", 
        result.available_shards, 
        result.manifest.shard_count
    );
    println!("Complete: {}", result.is_complete);
    
    // Check peer availability
    for peer in result.peer_availability {
        println!("  Shard {}: Peer {} ({})", 
            peer.shard_index,
            peer.peer_id,
            if peer.is_online { "online" } else { "offline" }
        );
    }
}
```

#### Searching Files

```rust
// Search by name pattern
let results = lookup.search_files("document").await?;
for manifest in results {
    println!("Found: {} ({})", manifest.file_name, manifest.file_hash);
}

// List all cached files
let all_files = lookup.list_cached_files().await?;
println!("Total files in cache: {}", all_files.len());
```

#### File Discovery

```rust
// Discover all files in the network
let discovered = lookup.discover_files().await?;
for file in discovered {
    println!("File: {} (source: {:?})", 
        file.file_hash,
        file.source
    );
}
```

#### Registering Files

```rust
// Register a file in DHT and cache
lookup.register_file(&manifest).await?;

// Unregister (remove from cache)
lookup.unregister_file("abc123...").await?;
```

## Integration with Upload/Download

### Upload with Caching

```rust
use pangea_rust_node::upload::UploadProtocol;

// Create upload protocol with cache
let upload = UploadProtocol::with_cache(ces, go_client, cache);

// Upload automatically caches shards and manifest
let manifest_json = upload.upload_file(
    Path::new("/path/to/file.txt"),
    vec![1, 2, 3]  // target peer IDs
).await?;

println!("Upload complete: {}", manifest_json);
```

### Download with Caching

```rust
use pangea_rust_node::download::DownloadProtocol;

// Create download protocol with cache
let download = DownloadProtocol::with_cache(ces, go_client, cache);

// Download checks cache first, then fetches from network
let bytes = download.download_file_with_hash(
    Path::new("/path/to/output.txt"),
    shard_locations,
    Some("abc123...")  // file hash for cache lookup
).await?;

println!("Downloaded {} bytes", bytes);
```

## Configuration

### Cache Configuration

```rust
// Small cache for low-resource devices
let small_cache = Cache::new(
    "/var/cache/pangea",
    100,              // 100 entries
    10 * 1024 * 1024  // 10 MB
)?;

// Large cache for high-performance nodes
let large_cache = Cache::new(
    "/var/cache/pangea",
    10000,                 // 10,000 entries
    1024 * 1024 * 1024     // 1 GB
)?;
```

### Cache Directory Structure

```
/var/cache/pangea/
├── manifests/
│   ├── abc123...json
│   ├── def456....json
│   └── ghi789....json
└── (in-memory LRU cache for shards)
```

## Performance Characteristics

### Cache Hit Rates
- **Local shards**: 0 latency (memory access)
- **Persisted manifests**: ~1-5ms (disk read)
- **Network fetch**: 10-100ms (depends on network)

### Memory Usage
- **Per shard**: Variable (depends on shard size)
- **Per manifest**: ~500 bytes (JSON metadata)
- **Cache overhead**: ~10-20% (LRU bookkeeping)

### Eviction Behavior
- LRU eviction triggers when cache size exceeds limit
- Evicts 10% extra space to reduce thrashing
- Manifests are never automatically evicted (persistent)

## Best Practices

### 1. Choose Appropriate Cache Sizes
```rust
// For desktop/server
Cache::new("/var/cache", 10000, 1024 * 1024 * 1024)?;  // 1GB

// For embedded/IoT
Cache::new("/var/cache", 100, 10 * 1024 * 1024)?;  // 10MB
```

### 2. Monitor Cache Statistics
```rust
// Periodically check cache performance
let stats = cache.get_stats().await;
let hit_rate = stats.shard_hits as f64 / 
    (stats.shard_hits + stats.shard_misses) as f64;
    
if hit_rate < 0.5 {
    println!("Warning: Low cache hit rate: {:.2}%", hit_rate * 100.0);
}
```

### 3. Clean Up Old Files
```rust
// Remove old manifests based on TTL
let manifests = cache.list_manifests().await;
let now = Utc::now().timestamp();

for manifest in manifests {
    if manifest.ttl > 0 {
        let age = now - manifest.timestamp;
        if age > manifest.ttl as i64 {
            cache.remove_manifest(&manifest.file_hash).await?;
        }
    }
}
```

### 4. Use Cache-First Download
```rust
// Always provide file hash for cache lookups
download.download_file_with_hash(
    output_path,
    shard_locations,
    Some(file_hash)  // Enable cache lookups
).await?;
```

## Troubleshooting

### High Memory Usage
- Reduce `max_entries` in Cache::new()
- Reduce `max_size_bytes` in Cache::new()
- Call `cache.clear_shards()` periodically

### Low Cache Hit Rate
- Increase cache size
- Check if files are being re-uploaded (different hashes)
- Verify cache is enabled in upload/download protocols

### Slow Manifest Lookups
- Check disk I/O performance
- Reduce number of manifests (clean up old files)
- Consider using SSD for cache directory

### Cache Corruption
- Manifests are stored as JSON for easy recovery
- Manually inspect `/var/cache/pangea/manifests/`
- Delete corrupted JSON files
- Call `cache.load_persisted_manifests()` to reload

## Advanced Topics

### Custom Eviction Policies
The current implementation uses LRU with size-based eviction. For custom policies, extend the `Cache` struct:

```rust
impl Cache {
    pub async fn custom_evict(&self, predicate: impl Fn(&str) -> bool) -> Result<()> {
        // Custom eviction logic
    }
}
```

### DHT Integration
The lookup service integrates with libp2p Kademlia DHT:

```rust
// Register file in DHT
lookup.register_file(&manifest).await?;

// DHT will propagate provider records
// Other nodes can find file via find_providers()
```

### Distributed Caching
For multi-node coordination:
- Use DHT to announce cached files
- Implement cache warming strategies
- Coordinate eviction across nodes

## API Reference

### Cache

| Method | Description |
|--------|-------------|
| `new(dir, max_entries, max_size)` | Create new cache |
| `get_shard(hash, index)` | Retrieve shard from cache |
| `put_shard(hash, index, data)` | Store shard in cache |
| `get_manifest(hash)` | Retrieve manifest |
| `put_manifest(manifest)` | Store manifest |
| `list_manifests()` | List all cached manifests |
| `get_stats()` | Get cache statistics |
| `clear_shards()` | Clear all shards |
| `clear_manifests()` | Clear all manifests |
| `remove_manifest(hash)` | Remove specific manifest |
| `load_persisted_manifests()` | Load manifests from disk |

### LookupService

| Method | Description |
|--------|-------------|
| `new(cache, dht, store)` | Create lookup service |
| `lookup_file(hash)` | Lookup file by hash |
| `discover_files()` | Discover all network files |
| `is_available(hash)` | Check if file is available |
| `list_cached_files()` | List locally cached files |
| `search_files(pattern)` | Search files by name |
| `verify_file(hash)` | Verify file integrity |
| `get_metadata(hash)` | Get file metadata |
| `register_file(manifest)` | Register file in DHT |
| `unregister_file(hash)` | Unregister file |

## Examples

### Complete Upload/Download with Caching

```rust
use pangea_rust_node::*;
use std::sync::Arc;
use std::path::Path;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Setup
    let caps = HardwareCaps::probe();
    let ces_config = CesConfig::adaptive(&caps, 8 * 1024 * 1024, 1.0);
    let ces = Arc::new(CesPipeline::new(ces_config));
    let go_addr = "127.0.0.1:8080".parse()?;
    let go_client = Arc::new(GoClient::new(go_addr));
    let cache = Arc::new(Cache::new("/var/cache/pangea", 1000, 100 * 1024 * 1024)?);
    
    // Upload with caching
    let upload = UploadProtocol::with_cache(ces.clone(), go_client.clone(), cache.clone());
    let manifest_json = upload.upload_file(
        Path::new("test.txt"),
        vec![1, 2, 3]
    ).await?;
    
    println!("Uploaded: {}", manifest_json);
    
    // Parse manifest
    let manifest: FileManifest = serde_json::from_str(&manifest_json)?;
    
    // Download with caching
    let download = DownloadProtocol::with_cache(ces, go_client, cache);
    let bytes = download.download_file_with_hash(
        Path::new("output.txt"),
        manifest.shard_locations,
        Some(&manifest.file_hash)
    ).await?;
    
    println!("Downloaded {} bytes", bytes);
    
    Ok(())
}
```

## Testing

Run cache and lookup tests:

```bash
# All tests
cargo test

# Cache tests only
cargo test cache::

# Lookup tests only
cargo test lookup::

# Specific test
cargo test test_shard_cache
```

## See Also

- [RUST.md](RUST.md) - Rust implementation overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [Upload/Download Documentation](RUST.md#upload-download-protocols)
