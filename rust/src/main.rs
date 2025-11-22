use pangea_ces::*;
use std::sync::Arc;
use tracing::{info, error, warn};
use tracing_subscriber;
use clap::Parser;

#[derive(Parser, Debug)]
#[clap(name = "pangea-rust-node")]
#[clap(about = "Rust upload/download protocols for Pangea Net (calls Go transport layer)", long_about = None)]
struct Args {
    #[clap(subcommand)]
    command: Option<Command>,

    /// Node ID (for daemon mode)
    #[clap(short, long, default_value = "1")]
    node_id: u32,

    /// RPC server address (Cap'n Proto) - exposes upload/download to Python
    #[clap(long, default_value = "127.0.0.1:8080")]
    rpc_addr: String,

    /// Go node RPC address (for calling Go transport layer)
    #[clap(long, default_value = "127.0.0.1:8082")]
    go_addr: String,

    /// QUIC P2P listen address
    #[clap(long, default_value = "127.0.0.1:9090")]
    p2p_addr: String,

    /// DHT listen address (libp2p)
    #[clap(long, default_value = "127.0.0.1:9091")]
    dht_addr: String,

    /// Bootstrap peers for DHT (multiaddr format)
    #[clap(long)]
    bootstrap: Vec<String>,

    /// Enable verbose logging
    #[clap(short, long)]
    verbose: bool,
}

#[derive(Parser, Debug)]
enum Command {
    /// Upload a file using CES pipeline and Go transport (manual mode)
    Upload {
        /// File to upload
        #[clap(value_name = "FILE")]
        file: String,

        /// Target peer IDs (comma-separated)
        #[clap(long, value_delimiter = ',')]
        peers: Vec<u32>,
    },

    /// Download a file using CES reconstruction and Go transport (manual mode)
    Download {
        /// Output file path
        #[clap(value_name = "FILE")]
        file: String,

        /// Shard locations in format: shard_index:peer_id (comma-separated)
        #[clap(long, value_delimiter = ',')]
        shards: Vec<String>,
    },

    /// Automated upload - just provide file path, discovers peers automatically
    Put {
        /// File to upload
        #[clap(value_name = "FILE")]
        file: String,
    },

    /// Automated download - just provide file hash, handles everything
    Get {
        /// File hash
        #[clap(value_name = "HASH")]
        hash: String,

        /// Output file path (optional - uses original filename if not provided)
        #[clap(short = 'o', long)]
        output: Option<String>,
    },

    /// List all available files
    List,

    /// Search files by name pattern
    Search {
        /// Search pattern
        #[clap(value_name = "PATTERN")]
        pattern: String,
    },

    /// Get file information
    Info {
        /// File hash
        #[clap(value_name = "HASH")]
        hash: String,
    },

    /// Run as daemon (default mode - runs RPC server for Python to call)
    Daemon,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();

    // Initialize logging
    let log_level = if args.verbose { "debug" } else { "info" };
    tracing_subscriber::fmt()
        .with_env_filter(log_level)
        .init();

    // Handle commands (upload/download) or run as daemon
    match args.command {
        Some(Command::Upload { ref file, ref peers }) => {
            return handle_upload(file, peers.clone(), &args).await;
        }
        Some(Command::Download { ref file, ref shards }) => {
            return handle_download(file, shards.clone(), &args).await;
        }
        Some(Command::Put { ref file }) => {
            return handle_automated_upload(file, &args).await;
        }
        Some(Command::Get { ref hash, ref output }) => {
            return handle_automated_download(hash, output.as_deref(), &args).await;
        }
        Some(Command::List) => {
            return handle_list(&args).await;
        }
        Some(Command::Search { ref pattern }) => {
            return handle_search(pattern, &args).await;
        }
        Some(Command::Info { ref hash }) => {
            return handle_info(hash, &args).await;
        }
        Some(Command::Daemon) | None => {
            // Run as daemon (default)
        }
    }

    info!("🚀 Pangea Rust Node v{} (Upload/Download Protocol Layer)", env!("CARGO_PKG_VERSION"));
    info!("Node ID: {}", args.node_id);
    info!("Calls Go transport layer at: {}", args.go_addr);

    // Probe hardware capabilities
    let caps = capabilities::HardwareCaps::probe();
    info!("Hardware capabilities:");
    info!("  AVX2: {}", caps.has_avx2);
    info!("  NEON: {}", caps.has_neon);
    info!("  io_uring: {}", caps.has_io_uring);
    info!("  eBPF/XDP: {}", caps.has_ebpf);
    info!("  RAM: {} GB", caps.ram_gb);
    info!("  CPU cores: {}", caps.cpu_cores);

    // Initialize components
    info!("Initializing components...");

    // Node store
    let store = Arc::new(store::NodeStore::new());
    let self_node = types::Node::new(args.node_id);
    store.upsert_node(self_node).await;
    info!("✓ Node store initialized");

    // Firewall
    let firewall = Arc::new(firewall::create_adaptive_firewall(&caps));
    info!("✓ Firewall initialized (mode: {:?})", firewall.mode());

    // Allow localhost for testing
    firewall.allow_ip("127.0.0.1".parse()?).await;

    // QUIC network
    let p2p_addr: std::net::SocketAddr = args.p2p_addr.parse()?;
    let network = Arc::new(network::QuicNode::new(args.node_id, p2p_addr).await?);
    info!("✓ QUIC network initialized on {}", p2p_addr);

    // DHT node
    let bootstrap_peers: Vec<libp2p::Multiaddr> = args.bootstrap
        .iter()
        .filter_map(|s| s.parse().ok())
        .collect();
    
    let dht_port = args.dht_addr.split(':').nth(1)
        .and_then(|p| p.parse::<u16>().ok())
        .unwrap_or(9091);
    
    let mut dht = dht::DhtNode::new(dht_port, bootstrap_peers).await?;
    let dht_listen = dht::local_multiaddr(dht_port);
    dht.listen_on(dht_listen.clone())?;
    info!("✓ DHT node initialized on {}", dht_listen);

    if !args.bootstrap.is_empty() {
        dht.bootstrap()?;
        info!("✓ DHT bootstrap initiated");
    }

    // RPC server
    let rpc_addr: std::net::SocketAddr = args.rpc_addr.parse()?;
    let rpc_server = Arc::new(rpc::RpcServer::new(
        rpc_addr,
        store.clone(),
        network.clone(),
    ));
    info!("✓ RPC server initialized");

    // CES pipeline demo
    let ces_config = types::CesConfig::adaptive(&caps, 1024 * 1024, 1.0);
    let compression_level = ces_config.compression_level;
    let _pipeline = ces::CesPipeline::new(ces_config);
    info!("✓ CES pipeline initialized (compression level: {})", compression_level);

    info!("🎯 All systems operational!");
    info!("📡 Listening:");
    info!("  - RPC (Cap'n Proto): {}", rpc_addr);
    info!("  - P2P (QUIC): {}", p2p_addr);
    info!("  - DHT (libp2p): {}", dht_listen);

    // Spawn RPC server task with LocalSet
    let local = tokio::task::LocalSet::new();
    let rpc_handle = {
        let rpc = rpc_server.clone();
        local.spawn_local(async move {
            if let Err(e) = rpc.start().await {
                error!("RPC server error: {}", e);
            }
        })
    };

    // Spawn DHT event loop
    let dht_handle = tokio::spawn(async move {
        loop {
            if let Some(event) = dht.next_event().await {
                info!("DHT event: {:?}", event);
            }
        }
    });

    // Spawn QUIC accept loop
    let network_clone = network.clone();
    let accept_handle = tokio::spawn(async move {
        if let Err(e) = network_clone.accept_connection().await {
            error!("QUIC accept error: {}", e);
        }
    });

    info!("Press Ctrl+C to shutdown...");

    // Run local tasks and wait for Ctrl+C
    local.run_until(async move {
        tokio::select! {
            _ = tokio::signal::ctrl_c() => {
                info!("Shutting down...");
            }
        }
    }).await;

    // Cleanup
    rpc_handle.abort();
    dht_handle.abort();
    accept_handle.abort();

    info!("✓ Shutdown complete");
    Ok(())
}

/// Handle upload command
async fn handle_upload(file: &str, peers: Vec<u32>, args: &Args) -> anyhow::Result<()> {
    use std::path::Path;
    use pangea_ces::upload::UploadProtocol;
    use pangea_ces::go_client::GoClient;

    info!("Upload mode: {} -> peers {:?}", file, peers);
    info!("Using Go transport at: {}", args.go_addr);

    // Create Go client
    let go_addr: std::net::SocketAddr = args.go_addr.parse()?;
    let go_client = Arc::new(GoClient::new(go_addr));

    // Connect to Go node
    go_client.connect().await?;

    // Create CES pipeline
    let caps = capabilities::HardwareCaps::probe();
    let ces_config = types::CesConfig::adaptive(&caps, 1024 * 1024, 1.0);
    let ces = Arc::new(ces::CesPipeline::new(ces_config));

    // Create upload protocol
    let upload = UploadProtocol::new(ces, go_client);

    // Upload file
    let manifest = upload.upload_file(Path::new(file), peers).await?;
    info!("✅ Upload complete!");
    println!("{}", manifest);

    Ok(())
}

/// Handle download command
async fn handle_download(file: &str, shards: Vec<String>, args: &Args) -> anyhow::Result<()> {
    use std::path::Path;
    use pangea_ces::download::DownloadProtocol;
    use pangea_ces::go_client::GoClient;

    info!("Download mode: {} <- {} shards", file, shards.len());
    info!("Using Go transport at: {}", args.go_addr);

    // Parse shard locations
    let shard_locations: Vec<(usize, u32)> = shards
        .iter()
        .filter_map(|s| {
            let parts: Vec<&str> = s.split(':').collect();
            if parts.len() == 2 {
                Some((parts[0].parse().ok()?, parts[1].parse().ok()?))
            } else {
                None
            }
        })
        .collect();

    if shard_locations.is_empty() {
        anyhow::bail!("No valid shard locations provided. Format: shard_index:peer_id");
    }

    // Create Go client
    let go_addr: std::net::SocketAddr = args.go_addr.parse()?;
    let go_client = Arc::new(GoClient::new(go_addr));

    // Connect to Go node
    go_client.connect().await?;

    // Create CES pipeline
    let caps = capabilities::HardwareCaps::probe();
    let ces_config = types::CesConfig::adaptive(&caps, 1024 * 1024, 1.0);
    let ces = Arc::new(ces::CesPipeline::new(ces_config));

    // Create download protocol
    let download = DownloadProtocol::new(ces, go_client);

    // Download file
    let bytes = download.download_file(Path::new(file), shard_locations).await?;
    info!("✅ Download complete! {} bytes", bytes);

    Ok(())
}

/// Get default cache directory
fn get_cache_dir() -> String {
    std::env::var("PANGEA_CACHE_DIR")
        .unwrap_or_else(|_| format!("{}/.pangea/cache", std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string())))
}

/// Initialize DHT with bootstrap peers
async fn init_dht(args: &Args) -> Option<Arc<tokio::sync::RwLock<dht::DhtNode>>> {
    let dht_port = args.dht_addr.split(':').nth(1)
        .and_then(|p| p.parse::<u16>().ok())
        .unwrap_or(9091);
    
    let bootstrap_peers: Vec<libp2p::Multiaddr> = args.bootstrap
        .iter()
        .filter_map(|s| s.parse().ok())
        .collect();
    
    match dht::DhtNode::new(dht_port, bootstrap_peers).await {
        Ok(mut dht_node) => {
            let dht_listen = dht::local_multiaddr(dht_port);
            if let Err(e) = dht_node.listen_on(dht_listen) {
                warn!("DHT listen failed: {}", e);
                return None;
            }
            Some(Arc::new(tokio::sync::RwLock::new(dht_node)))
        }
        Err(e) => {
            warn!("DHT initialization failed: {}, continuing without DHT", e);
            None
        }
    }
}

/// Handle automated upload command
async fn handle_automated_upload(file: &str, args: &Args) -> anyhow::Result<()> {
    use std::path::Path;
    use pangea_ces::{AutomatedUploader, Cache};

    info!("🚀 Automated upload mode: {}", file);
    info!("Using Go node at: {}", args.go_addr);

    // Create Go client
    let go_addr: std::net::SocketAddr = args.go_addr.parse()?;
    let go_client = Arc::new(go_client::GoClient::new(go_addr));

    // Connect to Go node
    go_client.connect().await?;

    // Create CES pipeline
    let caps = capabilities::HardwareCaps::probe();
    let ces_config = types::CesConfig::adaptive(&caps, 1024 * 1024, 1.0);
    let ces = Arc::new(ces::CesPipeline::new(ces_config));

    // Create cache (use default location)
    let cache_dir = get_cache_dir();
    let cache = Arc::new(Cache::new(&cache_dir, 1000, 100 * 1024 * 1024)?); // 1000 entries, 100MB

    // Create node store
    let store = Arc::new(store::NodeStore::new());

    // Initialize DHT (optional)
    let dht = init_dht(args).await;

    // Create automated uploader
    let uploader = AutomatedUploader::new(ces, go_client, cache, store, dht);

    // Upload file
    let result = uploader.upload(Path::new(file)).await?;
    
    println!("\n📊 Upload Summary:");
    println!("  File hash: {}", result.file_hash);
    println!("  Shards: {}", result.shard_count);
    println!("  Distributed to: {} peer(s)", result.total_peers);
    println!("\n📝 Manifest:\n{}", result.manifest_json);

    Ok(())
}

/// Handle automated download command
async fn handle_automated_download(hash: &str, output: Option<&str>, args: &Args) -> anyhow::Result<()> {
    use std::path::PathBuf;
    use pangea_ces::{AutomatedDownloader, Cache};

    info!("🚀 Automated download mode: {}", hash);
    info!("Using Go node at: {}", args.go_addr);

    // Create Go client
    let go_addr: std::net::SocketAddr = args.go_addr.parse()?;
    let go_client = Arc::new(go_client::GoClient::new(go_addr));

    // Connect to Go node
    go_client.connect().await?;

    // Create CES pipeline
    let caps = capabilities::HardwareCaps::probe();
    let ces_config = types::CesConfig::adaptive(&caps, 1024 * 1024, 1.0);
    let ces = Arc::new(ces::CesPipeline::new(ces_config));

    // Create cache
    let cache_dir = get_cache_dir();
    let cache = Arc::new(Cache::new(&cache_dir, 1000, 100 * 1024 * 1024)?);

    // Create node store
    let store = Arc::new(store::NodeStore::new());

    // Initialize DHT (optional)
    let dht = init_dht(args).await;

    // Create automated downloader
    let downloader = AutomatedDownloader::new(ces, go_client, cache, store, dht);

    // Determine output path
    let output_path = if let Some(path) = output {
        PathBuf::from(path)
    } else {
        // Use file info to get original filename
        if let Some(info) = downloader.get_info(hash).await? {
            PathBuf::from(format!("./{}", info.file_name))
        } else {
            PathBuf::from(format!("./{}.bin", &hash[..8]))
        }
    };

    // Download file
    let result = downloader.download(hash, &output_path).await?;
    
    println!("\n📊 Download Summary:");
    println!("  File: {}", result.file_name);
    println!("  Hash: {}", result.file_hash);
    println!("  Downloaded: {} bytes", result.bytes_written);
    println!("  Shards fetched: {}", result.shards_fetched);
    println!("  Saved to: {:?}", result.output_path);

    Ok(())
}

/// Handle list command
async fn handle_list(args: &Args) -> anyhow::Result<()> {
    use pangea_ces::{AutomatedDownloader, Cache};

    info!("📋 Listing files");

    // Create minimal setup for list operation
    let go_addr: std::net::SocketAddr = args.go_addr.parse()?;
    let go_client = Arc::new(go_client::GoClient::new(go_addr));
    
    let caps = capabilities::HardwareCaps::probe();
    let ces_config = types::CesConfig::adaptive(&caps, 1024 * 1024, 1.0);
    let ces = Arc::new(ces::CesPipeline::new(ces_config));

    let cache_dir = get_cache_dir();
    let cache = Arc::new(Cache::new(&cache_dir, 1000, 100 * 1024 * 1024)?);
    
    let store = Arc::new(store::NodeStore::new());

    let downloader = AutomatedDownloader::new(ces, go_client, cache, store, None);
    
    let files = downloader.list_files().await?;

    if files.is_empty() {
        println!("No files found in cache.");
        return Ok(());
    }

    // Table column widths: 10, 30, 15, 10, 10; 4 spaces between columns
    const TABLE_SEPARATOR_LEN: usize = 10 + 30 + 15 + 10 + 10 + 4;
    println!("\n📁 Available Files ({} total):\n", files.len());
    println!("{:<10} {:<30} {:<15} {:<10} {:<10}", "Hash", "Name", "Size", "Shards", "Status");
    println!("{}", "-".repeat(TABLE_SEPARATOR_LEN));
    
    for file in files {
        let status = if file.is_available { "✅ Ready" } else { "⚠️  Partial" };
        let hash_short = if file.file_hash.chars().count() > 10 {
            file.file_hash.chars().take(10).collect::<String>()
        } else {
            file.file_hash.clone()
        };
        let name_display = if file.file_name.len() > 30 { 
            format!("{}...", &file.file_name[..27])
        } else { 
            file.file_name.clone()
        };
        println!("{:<10} {:<30} {:<15} {:<10} {:<10}", 
                 hash_short,
                 name_display,
                 format!("{} B", file.file_size),
                 file.shard_count,
                 status);
    }
    println!();

    Ok(())
}

/// Handle search command
async fn handle_search(pattern: &str, args: &Args) -> anyhow::Result<()> {
    use pangea_ces::{AutomatedDownloader, Cache};

    info!("🔍 Searching for: {}", pattern);

    let go_addr: std::net::SocketAddr = args.go_addr.parse()?;
    let go_client = Arc::new(go_client::GoClient::new(go_addr));
    
    let caps = capabilities::HardwareCaps::probe();
    let ces_config = types::CesConfig::adaptive(&caps, 1024 * 1024, 1.0);
    let ces = Arc::new(ces::CesPipeline::new(ces_config));

    let cache_dir = get_cache_dir();
    let cache = Arc::new(Cache::new(&cache_dir, 1000, 100 * 1024 * 1024)?);
    
    let store = Arc::new(store::NodeStore::new());

    let downloader = AutomatedDownloader::new(ces, go_client, cache, store, None);
    
    let files = downloader.search(pattern).await?;

    if files.is_empty() {
        println!("No files matching '{}' found.", pattern);
        return Ok(());
    }

    println!("\n🔍 Search Results for '{}' ({} found):\n", pattern, files.len());
    println!("{:<10} {:<30} {:<15} {:<10} {:<10}", "Hash", "Name", "Size", "Shards", "Status");
    println!("{}", "-".repeat(85));
    
    for file in files {
        let status = if file.is_available { "✅ Ready" } else { "⚠️  Partial" };
        let hash_short = if file.file_hash.len() > 10 { 
            &file.file_hash[..10]
        } else {
            &file.file_hash
        };
        let name_display = if file.file_name.len() > 30 { 
            format!("{}...", &file.file_name[..27])
        } else { 
            file.file_name.clone()
        };
        println!("{:<10} {:<30} {:<15} {:<10} {:<10}", 
                 hash_short,
                 name_display,
                 format!("{} B", file.file_size),
                 file.shard_count,
                 status);
    }
    println!();

    Ok(())
}

/// Handle info command
async fn handle_info(hash: &str, args: &Args) -> anyhow::Result<()> {
    use pangea_ces::{AutomatedDownloader, Cache};

    info!("ℹ️  Getting info for: {}", hash);

    let go_addr: std::net::SocketAddr = args.go_addr.parse()?;
    let go_client = Arc::new(go_client::GoClient::new(go_addr));
    
    let caps = capabilities::HardwareCaps::probe();
    let ces_config = types::CesConfig::adaptive(&caps, 1024 * 1024, 1.0);
    let ces = Arc::new(ces::CesPipeline::new(ces_config));

    let cache_dir = get_cache_dir();
    let cache = Arc::new(Cache::new(&cache_dir, 1000, 100 * 1024 * 1024)?);
    
    let store = Arc::new(store::NodeStore::new());

    let downloader = AutomatedDownloader::new(ces, go_client, cache, store, None);
    
    if let Some(info) = downloader.get_info(hash).await? {
        use chrono::{DateTime, Utc};
        let timestamp_str = DateTime::<Utc>::from_timestamp(info.timestamp, 0)
            .map(|dt| dt.format("%Y-%m-%d %H:%M:%S").to_string())
            .unwrap_or_else(|| "Unknown".to_string());
            
        println!("\n📄 File Information:");
        println!("  Name: {}", info.file_name);
        println!("  Hash: {}", info.file_hash);
        println!("  Size: {} bytes ({:.2} MB)", info.file_size, info.file_size as f64 / 1_048_576.0);
        println!("  Shards: {}", info.shard_count);
        println!("  Status: {}", if info.is_available { "✅ Available" } else { "⚠️  Partially available" });
        println!("  Timestamp: {}", timestamp_str);
        println!();
    } else {
        println!("❌ File not found: {}", hash);
    }

    Ok(())
}
