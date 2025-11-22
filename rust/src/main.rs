use pangea_ces::*;
use std::sync::Arc;
use tracing::{info, error};
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
    /// Upload a file using CES pipeline and Go transport
    Upload {
        /// File to upload
        #[clap(value_name = "FILE")]
        file: String,

        /// Target peer IDs (comma-separated)
        #[clap(long, value_delimiter = ',')]
        peers: Vec<u32>,
    },

    /// Download a file using CES reconstruction and Go transport
    Download {
        /// Output file path
        #[clap(value_name = "FILE")]
        file: String,

        /// Shard locations in format: shard_index:peer_id (comma-separated)
        #[clap(long, value_delimiter = ',')]
        shards: Vec<String>,
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
