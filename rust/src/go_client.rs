use anyhow::{Context, Result};

use capnp_rpc::{rpc_twoparty_capnp, twoparty, RpcSystem};
use std::net::SocketAddr;
use std::sync::RwLock;
use tokio::net::TcpStream;
use tracing::{error, info};

use crate::schema_capnp::node_service;

/// Client for connecting to Go node's Cap'n Proto RPC
pub struct GoClient {
    addr: SocketAddr,
    client: RwLock<Option<node_service::Client>>,
}

impl GoClient {
    pub fn new(addr: SocketAddr) -> Self {
        Self { 
            addr,
            client: RwLock::new(None),
        }
    }

    /// Connect to Go node
    pub async fn connect(&self) -> Result<()> {
        info!("Connecting to Go node at {}", self.addr);
        
        // Connect to Go Cap'n Proto server
        let stream = TcpStream::connect(self.addr)
            .await
            .context("Failed to connect to Go node")?;
        
        use tokio_util::compat::{TokioAsyncReadCompatExt, TokioAsyncWriteCompatExt};
        
        let (reader, writer) = tokio::io::split(stream);
        let reader = reader.compat();
        let writer = writer.compat_write();
        
        // Set up RPC system
        let rpc_network = Box::new(twoparty::VatNetwork::new(
            reader,
            writer,
            rpc_twoparty_capnp::Side::Client,
            Default::default(),
        ));
        
        let mut rpc_system = RpcSystem::new(rpc_network, None);
        let client: node_service::Client = rpc_system.bootstrap(rpc_twoparty_capnp::Side::Server);
        
        // Spawn RPC system in background using spawn_local for non-Send futures
        tokio::task::spawn_local(async move {
            if let Err(e) = rpc_system.await {
                error!("RPC system error: {}", e);
            }
        });
        
        *self.client.write().unwrap() = Some(client);
        info!("Connected to Go node successfully");
        
        Ok(())
    }

    /// Send data to Go node for transport
    pub async fn send_data(&self, peer_id: u32, data: Vec<u8>) -> Result<bool> {
        let client = self.client.read().unwrap().as_ref()
            .context("Not connected to Go node. Call connect() first")?
            .clone();
        
        info!("Sending {} bytes to Go node for peer {}", data.len(), peer_id);
        
        let mut request = client.send_message_request();
        {
            let mut msg = request.get().get_msg()?;
            msg.set_to_peer_id(peer_id);
            msg.set_data(&data);
        }
        
        let response = request.send().promise.await?;
        let success = response.get()?.get_success();
        
        Ok(success)
    }

    /// Get connection quality for a peer
    pub async fn get_connection_quality(&self, peer_id: u32) -> Result<(f32, f32, f32)> {
        let client = self.client.read().unwrap().as_ref()
            .context("Not connected to Go node")?
            .clone();
        
        let mut request = client.get_connection_quality_request();
        request.get().set_peer_id(peer_id);
        
        let response = request.send().promise.await?;
        let quality = response.get()?.get_quality()?;
        
        Ok((
            quality.get_latency_ms(),
            quality.get_jitter_ms(),
            quality.get_packet_loss(),
        ))
    }

    /// Connect to a peer via Go node
    pub async fn connect_peer(&self, host: &str, port: u16) -> Result<(bool, f32, f32, f32)> {
        let client = self.client.read().unwrap().as_ref()
            .context("Not connected to Go node")?
            .clone();
        
        info!("Connecting to peer {}:{} via Go node", host, port);
        
        let mut request = client.connect_to_peer_request();
        {
            let mut peer = request.get().get_peer()?;
            peer.set_peer_id(0); // Will be assigned by Go
            peer.set_host(host);
            peer.set_port(port);
        }
        
        let response = request.send().promise.await?;
        let result = response.get()?;
        let success = result.get_success();
        
        if success {
            let quality = result.get_quality()?;
            Ok((
                success,
                quality.get_latency_ms(),
                quality.get_jitter_ms(),
                quality.get_packet_loss(),
            ))
        } else {
            Ok((false, 0.0, 0.0, 0.0))
        }
    }

    /// Disconnect from a peer
    pub async fn disconnect_peer(&self, peer_id: u32) -> Result<bool> {
        let client = self.client.read().unwrap().as_ref()
            .context("Not connected to Go node")?
            .clone();
        
        let mut request = client.disconnect_peer_request();
        request.get().set_peer_id(peer_id);
        
        let response = request.send().promise.await?;
        let success = response.get()?.get_success();
        
        Ok(success)
    }

    /// Get list of connected peers
    pub async fn get_connected_peers(&self) -> Result<Vec<u32>> {
        let client = self.client.read().unwrap().as_ref()
            .context("Not connected to Go node")?
            .clone();
        
        let request = client.get_connected_peers_request();
        let response = request.send().promise.await?;
        let peers_list = response.get()?.get_peers()?;
        
        let mut peers = Vec::new();
        for i in 0..peers_list.len() {
            peers.push(peers_list.get(i));
        }
        
        Ok(peers)
    }

    /// Get a specific node by ID
    pub async fn get_node(&self, node_id: u32) -> Result<Option<(u32, u32, f32, f32)>> {
        let client = self.client.read().unwrap().as_ref()
            .context("Not connected to Go node")?
            .clone();
        
        let mut request = client.get_node_request();
        request.get().get_query()?.set_node_id(node_id);
        
        let response = request.send().promise.await?;
        let node = response.get()?.get_node()?;
        
        Ok(Some((
            node.get_id(),
            node.get_status(),
            node.get_latency_ms(),
            node.get_threat_score(),
        )))
    }

    /// Get all nodes
    pub async fn get_all_nodes(&self) -> Result<Vec<(u32, u32, f32, f32)>> {
        let client = self.client.read().unwrap().as_ref()
            .context("Not connected to Go node")?
            .clone();
        
        let request = client.get_all_nodes_request();
        let response = request.send().promise.await?;
        let node_list = response.get()?.get_nodes()?.get_nodes()?;
        
        let mut nodes = Vec::new();
        for i in 0..node_list.len() {
            let node = node_list.get(i);
            nodes.push((
                node.get_id(),
                node.get_status(),
                node.get_latency_ms(),
                node.get_threat_score(),
            ));
        }
        
        Ok(nodes)
    }

    /// Update node threat score (called by AI/prediction)
    pub async fn update_node(&self, node_id: u32, latency_ms: f32, threat_score: f32) -> Result<bool> {
        let client = self.client.read().unwrap().as_ref()
            .context("Not connected to Go node")?
            .clone();
        
        let mut request = client.update_node_request();
        {
            let mut update = request.get().get_update()?;
            update.set_node_id(node_id);
            update.set_latency_ms(latency_ms);
            update.set_threat_score(threat_score);
        }
        
        let response = request.send().promise.await?;
        let success = response.get()?.get_success();
        
        Ok(success)
    }

    // UNTESTABLE: Data transfer methods below require extending the Cap'n Proto schema
    // and implementing a data storage/retrieval layer in the Go node.
    // These are stubbed for compilation but will need full implementation.

    /// Receive data from a peer (placeholder - needs schema extension)
    pub async fn receive_data(&self, _peer_id: u32) -> Result<Vec<u8>> {
        // TODO: Extend schema.capnp with:
        // receiveData @10 (peerId :UInt32) -> (data :Data);
        // Then implement in Go's capnp_service.go
        info!("receive_data called but not yet implemented in schema");
        Ok(Vec::new())
    }

    /// Get peer information (placeholder - needs schema extension)
    pub async fn get_peer_info(&self, _peer_id: u32) -> Result<Option<String>> {
        // TODO: Extend schema.capnp with:
        // getPeerInfo @11 (peerId :UInt32) -> (info :Text);
        // Then implement in Go's capnp_service.go
        info!("get_peer_info called but not yet implemented in schema");
        Ok(None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_go_client_creation() {
        let addr: SocketAddr = "127.0.0.1:8080"
            .parse()
            .expect("Hard-coded Go addr 127.0.0.1:8080 must be a valid SocketAddr");
        let client = GoClient::new(addr);
        assert_eq!(client.addr, addr);
    }
}
