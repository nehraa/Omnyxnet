use anyhow::Result;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::TcpListener;
use tracing::{error, info};

use crate::network::QuicNode;
use crate::store::NodeStore;
use crate::types::{ConnectionQuality, Node, PeerAddress};

/// RPC server using Cap'n Proto
pub struct RpcServer {
    addr: SocketAddr,
    store: Arc<NodeStore>,
    network: Arc<QuicNode>,
}

impl RpcServer {
    pub fn new(addr: SocketAddr, store: Arc<NodeStore>, network: Arc<QuicNode>) -> Self {
        Self {
            addr,
            store,
            network,
        }
    }

    /// Start the RPC server
    pub async fn start(&self) -> Result<()> {
        let listener = TcpListener::bind(self.addr).await?;
        info!("RPC server listening on {}", self.addr);

        loop {
            match listener.accept().await {
                Ok((stream, addr)) => {
                    info!("RPC connection from {}", addr);

                    let store = self.store.clone();
                    let network = self.network.clone();

                    // Spawn on the current task using tokio::task::spawn_local
                    // Or handle inline for simplicity
                    tokio::task::spawn_local(async move {
                        if let Err(e) = handle_rpc_connection(stream, store, network).await {
                            error!("RPC connection error: {}", e);
                        }
                    });
                }
                Err(e) => {
                    error!("Failed to accept RPC connection: {}", e);
                }
            }
        }
    }
}

/// Handle a single RPC connection
async fn handle_rpc_connection(
    stream: tokio::net::TcpStream,
    store: Arc<NodeStore>,
    network: Arc<QuicNode>,
) -> Result<()> {
    use capnp_rpc::{rpc_twoparty_capnp, twoparty, RpcSystem};
    use tokio_util::compat::{TokioAsyncReadCompatExt, TokioAsyncWriteCompatExt};

    // Set up Cap'n Proto RPC with compat layer
    let (reader, writer) = tokio::io::split(stream);
    let reader = reader.compat();
    let writer = writer.compat_write();

    let rpc_network = Box::new(twoparty::VatNetwork::new(
        reader,
        writer,
        rpc_twoparty_capnp::Side::Server,
        Default::default(),
    ));

    // Create service implementation
    let _service_impl = NodeServiceImpl::new(store, network);

    // TODO: Bootstrap with actual service implementation
    // For now, this is a placeholder that accepts connections
    let rpc_system = RpcSystem::new(rpc_network, None);

    info!("RPC system initialized");

    // Run the RPC system
    rpc_system.await?;

    Ok(())
}

/// Simplified RPC service implementation (without full Cap'n Proto codegen)
/// In production, this would be generated from schema.capnp
pub struct NodeServiceImpl {
    store: Arc<NodeStore>,
    network: Arc<QuicNode>,
}

impl NodeServiceImpl {
    pub fn new(store: Arc<NodeStore>, network: Arc<QuicNode>) -> Self {
        Self { store, network }
    }

    /// Get a specific node
    pub async fn get_node(&self, node_id: u32) -> Option<Node> {
        self.store.get_node(node_id).await
    }

    /// Get all nodes
    pub async fn get_all_nodes(&self) -> Vec<Node> {
        self.store.get_all_nodes().await
    }

    /// Update node
    pub async fn update_node(
        &self,
        node_id: u32,
        latency_ms: f32,
        threat_score: f32,
    ) -> Result<bool> {
        if let Some(_node) = self.store.get_node(node_id).await {
            self.store.update_latency(node_id, latency_ms).await?;
            self.store
                .update_threat_score(node_id, threat_score)
                .await?;
            Ok(true)
        } else {
            Ok(false)
        }
    }

    /// Connect to peer
    pub async fn connect_to_peer(&self, peer: PeerAddress) -> Result<(bool, ConnectionQuality)> {
        match self.network.connect_to_peer(peer.clone()).await {
            Ok(quality) => Ok((true, quality)),
            Err(e) => {
                error!("Failed to connect to peer {}: {}", peer.peer_id, e);
                Ok((false, ConnectionQuality::default()))
            }
        }
    }

    /// Send message
    pub async fn send_message(&self, peer_id: u32, data: Vec<u8>) -> Result<bool> {
        match self.network.send_message(peer_id, data.into()).await {
            Ok(_) => Ok(true),
            Err(e) => {
                error!("Failed to send message to peer {}: {}", peer_id, e);
                Ok(false)
            }
        }
    }

    /// Get connection quality
    pub async fn get_connection_quality(&self, peer_id: u32) -> Option<ConnectionQuality> {
        self.network.get_connection_quality(peer_id).await
    }

    /// Disconnect peer
    pub async fn disconnect_peer(&self, peer_id: u32) -> Result<bool> {
        self.network.disconnect_peer(peer_id).await?;
        Ok(true)
    }

    /// Get connected peers
    pub async fn get_connected_peers(&self) -> Vec<u32> {
        self.network.get_connected_peers().await
    }
}
