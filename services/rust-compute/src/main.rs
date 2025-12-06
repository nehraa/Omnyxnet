mod data_processing;

use anyhow::Result;
use clap::Parser;
use log::info;
use std::net::SocketAddr;
use tokio::net::TcpListener;

use data_processing::Preprocessor;

#[derive(Parser, Debug)]
#[command(name = "Pangea Rust Compute Core")]
#[command(about = "High-performance distributed compute core for Pangea Net", long_about = None)]
struct Args {
    /// Node ID for this compute instance
    #[arg(short, long, default_value = "1")]
    id: u32,

    /// RPC server listen address
    #[arg(short, long, default_value = "0.0.0.0:9090")]
    listen: String,

    /// Orchestrator address for RPC connections
    #[arg(short, long, default_value = "go-orchestrator:8080")]
    orchestrator: String,

    /// Number of worker threads for data processing
    #[arg(short, long, default_value = "4")]
    workers: usize,

    /// Data chunk size for batch processing
    #[arg(short, long, default_value = "32")]
    chunk_size: usize,

    /// Enable verbose logging
    #[arg(short, long)]
    verbose: bool,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    // Initialize logging
    let log_level = if args.verbose { "debug" } else { "info" };
    env_logger::builder()
        .filter_level(log_level.parse().unwrap())
        .init();

    info!("🚀 Pangea Rust Compute Core starting");
    info!("   Node ID: {}", args.id);
    info!("   Listen: {}", args.listen);
    info!("   Orchestrator: {}", args.orchestrator);
    info!("   Workers: {}", args.workers);
    info!("   Chunk size: {}", args.chunk_size);

    // Create preprocessor
    let preprocessor = Preprocessor::new(args.workers, args.chunk_size);
    info!("✅ Data preprocessor initialized");

    // Setup TCP listener
    let addr: SocketAddr = args.listen.parse()?;
    let listener = TcpListener::bind(&addr).await?;
    info!("📡 RPC server listening on {}", addr);

    // Main server loop
    loop {
        let (socket, peer_addr) = listener.accept().await?;
        info!("✅ New connection from {}", peer_addr);
        
        // In production, handle the connection with Cap'n Proto RPC
        tokio::spawn(async move {
            if let Err(e) = handle_connection(socket).await {
                log::error!("Connection error: {}", e);
            }
        });
    }
}

/// Handle incoming RPC connections
async fn handle_connection(mut socket: tokio::net::TcpStream) -> Result<()> {
    use tokio::io::AsyncReadExt;
    
    let mut buffer = vec![0; 1024];
    let n = socket.read(&mut buffer).await?;
    info!("📨 Received {} bytes", n);
    
    Ok(())
}
