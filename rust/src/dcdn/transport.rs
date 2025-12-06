//! QUIC transport layer for chunk delivery

use crate::dcdn::types::{ChunkData, PeerId};
use crate::dcdn::config::QuicConfig;
use anyhow::{Context, Result};
use dashmap::DashMap;
use quinn::{Connection, Endpoint, ServerConfig};
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::Mutex;

/// Handle to a QUIC connection
pub type ConnectionHandle = Arc<Connection>;

/// QUIC transport manager
pub struct QuicTransport {
    endpoint: Arc<Mutex<Option<Endpoint>>>,
    active_connections: DashMap<PeerId, Connection>,
    config: Arc<QuicConfig>,
}

impl QuicTransport {
    /// Create a new QUIC transport manager
    pub fn new(config: QuicConfig) -> Self {
        Self {
            endpoint: Arc::new(Mutex::new(None)),
            active_connections: DashMap::new(),
            config: Arc::new(config),
        }
    }

    /// Start listening on the given address
    pub async fn listen(&self, addr: SocketAddr) -> Result<()> {
        let server_config = Self::create_server_config(&self.config)?;
        let endpoint = Endpoint::server(server_config, addr)
            .context("Failed to create QUIC endpoint")?;

        let mut ep = self.endpoint.lock().await;
        *ep = Some(endpoint);

        Ok(())
    }

    /// Connect to a peer
    pub async fn connect(&self, peer_id: PeerId, peer_addr: SocketAddr) -> Result<ConnectionHandle> {
        // Check if already connected
        if let Some(conn) = self.active_connections.get(&peer_id) {
            return Ok(Arc::new(conn.clone()));
        }

        let endpoint = self.endpoint.lock().await;
        let endpoint = endpoint.as_ref()
            .context("Endpoint not initialized")?;

        let conn = endpoint.connect(peer_addr, "localhost")
            .context("Failed to initiate connection")?
            .await
            .context("Connection failed")?;

        self.active_connections.insert(peer_id, conn.clone());

        Ok(Arc::new(conn))
    }

    /// Accept an incoming connection
    pub async fn accept(&self) -> Result<(PeerId, Connection)> {
        let endpoint = self.endpoint.lock().await;
        let endpoint = endpoint.as_ref()
            .context("Endpoint not initialized")?;

        let conn = endpoint.accept().await
            .context("No incoming connection")?
            .await
            .context("Failed to accept connection")?;

        // Derive peer ID from TLS certificate using peer identity
        let peer_id = Self::derive_peer_id_from_connection(&conn)?;

        self.active_connections.insert(peer_id, conn.clone());

        Ok((peer_id, conn))
    }
    
    /// Derive a peer ID from the TLS certificate of a QUIC connection
    fn derive_peer_id_from_connection(conn: &Connection) -> Result<PeerId> {
        use sha2::{Sha256, Digest};
        
        // Get the peer's certificate chain
        if let Some(peer_certs) = conn.peer_identity() {
            // Get the DER-encoded certificate data
            if let Some(cert_der) = peer_certs.downcast_ref::<Vec<rustls::pki_types::CertificateDer>>() {
                if !cert_der.is_empty() {
                    // Hash the certificate to derive a deterministic peer ID
                    let mut hasher = Sha256::new();
                    hasher.update(&cert_der[0]);
                    let hash = hasher.finalize();
                    
                    // Use first 8 bytes of hash as peer ID
                    let mut id_bytes = [0u8; 8];
                    id_bytes.copy_from_slice(&hash[..8]);
                    let peer_id = u64::from_be_bytes(id_bytes);
                    
                    return Ok(PeerId::new(peer_id));
                }
            }
        }
        
        // Fallback: If no certificate available (e.g., server-only auth),
        // use connection stable_id which is deterministic per connection
        let stable_id = conn.stable_id();
        Ok(PeerId::new(stable_id as u64))
    }

    /// Send a chunk over a connection
    pub async fn send_chunk(&self, conn: &ConnectionHandle, chunk: &ChunkData) -> Result<()> {
        let mut send_stream = conn.open_uni().await
            .context("Failed to open stream")?;

        // Serialize chunk (simplified)
        let data = bincode::serialize(chunk)
            .context("Failed to serialize chunk")?;

        send_stream.write_all(&data).await
            .context("Failed to write chunk data")?;

        send_stream.finish()
            .context("Failed to finish stream")?;

        Ok(())
    }

    /// Receive a chunk from a connection
    pub async fn receive_chunk(&self, conn: &ConnectionHandle) -> Result<ChunkData> {
        let mut recv_stream = conn.accept_uni().await
            .context("Failed to accept stream")?;

        // Use configurable max_chunk_size from QuicConfig
        let data = recv_stream.read_to_end(self.config.max_chunk_size).await
            .context("Failed to read chunk data")?;

        let chunk: ChunkData = bincode::deserialize(&data)
            .context("Failed to deserialize chunk")?;

        Ok(chunk)
    }

    /// Get active connection for a peer
    pub fn get_connection(&self, peer_id: &PeerId) -> Option<ConnectionHandle> {
        self.active_connections.get(peer_id).map(|c| Arc::new(c.clone()))
    }

    /// Close connection to a peer
    pub fn close_connection(&self, peer_id: &PeerId) {
        if let Some((_, conn)) = self.active_connections.remove(peer_id) {
            conn.close(0u32.into(), b"connection closed");
        }
    }

    /// Get number of active connections
    pub fn connection_count(&self) -> usize {
        self.active_connections.len()
    }

    /// Create server configuration
    fn create_server_config(config: &QuicConfig) -> Result<ServerConfig> {
        let cert = rcgen::generate_simple_self_signed(vec!["localhost".into()])
            .context("Failed to generate certificate")?;
        let cert_der = cert.cert.der().to_vec();
        let key_der = cert.key_pair.serialize_der();

        let priv_key = rustls::pki_types::PrivateKeyDer::try_from(key_der)
            .map_err(|e| anyhow::anyhow!("Failed to parse private key: {}", e))?;
        let cert_chain = vec![rustls::pki_types::CertificateDer::from(cert_der)];

        let mut server_config = ServerConfig::with_single_cert(cert_chain, priv_key)
            .context("Failed to create server config")?;

        let mut transport_config = quinn::TransportConfig::default();
        transport_config.max_concurrent_uni_streams(
            quinn::VarInt::from_u64(config.max_streams_per_connection).unwrap_or(quinn::VarInt::from_u32(256))
        );
        transport_config.max_idle_timeout(Some(
            quinn::IdleTimeout::try_from(std::time::Duration::from_millis(config.idle_timeout_ms))
                .unwrap_or(quinn::IdleTimeout::from(quinn::VarInt::from_u32(30000)))
        ));
        
        // Apply congestion control algorithm
        match config.congestion_algorithm {
            crate::dcdn::config::CongestionAlgo::BBR => {
                // BBR is not directly available in quinn, use default (CUBIC-like)
                // Note: quinn's default congestion controller is NewReno-based
            }
            crate::dcdn::config::CongestionAlgo::CUBIC => {
                // CUBIC is the default-like behavior in quinn
            }
        }
        
        // Note: GSO (Generic Segmentation Offload) is enabled at the Endpoint level,
        // not in TransportConfig. It's handled by the OS and quinn automatically uses it if available.

        server_config.transport_config(Arc::new(transport_config));

        Ok(server_config)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dcdn::types::{ChunkId, Signature};
    use bytes::Bytes;
    use std::time::Instant;

    fn create_test_chunk() -> ChunkData {
        ChunkData {
            id: ChunkId(1),
            sequence: 1,
            timestamp: Instant::now(),
            source_peer: PeerId(1),
            signature: Signature([0u8; 64]),
            data: Bytes::from(vec![1, 2, 3, 4, 5]),
            fec_group: None,
        }
    }

    #[tokio::test]
    async fn test_transport_creation() {
        let config = QuicConfig {
            max_concurrent_connections: 100,
            max_streams_per_connection: 256,
            congestion_algorithm: crate::dcdn::config::CongestionAlgo::BBR,
            enable_gso: true,
            idle_timeout_ms: 30000,
        };

        let transport = QuicTransport::new(config);
        assert_eq!(transport.connection_count(), 0);
    }

    #[tokio::test]
    async fn test_listen() {
        let config = QuicConfig {
            max_concurrent_connections: 100,
            max_streams_per_connection: 256,
            congestion_algorithm: crate::dcdn::config::CongestionAlgo::BBR,
            enable_gso: true,
            idle_timeout_ms: 30000,
        };

        let transport = QuicTransport::new(config);
        let addr: SocketAddr = "127.0.0.1:0".parse().unwrap();
        
        // Should be able to start listening
        let result = transport.listen(addr).await;
        assert!(result.is_ok());
    }
}
