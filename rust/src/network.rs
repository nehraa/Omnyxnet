use anyhow::{Result, Context};
use quinn::{Endpoint, ServerConfig, ClientConfig, Connection};
use rustls::pki_types::{CertificateDer, PrivateKeyDer};
use std::sync::Arc;
use std::net::SocketAddr;
use std::collections::HashMap;
use tokio::sync::{RwLock, mpsc};
use tracing::{info, warn, debug};
use bytes::Bytes;

use crate::types::{PeerAddress, ConnectionQuality};

/// QUIC-based P2P network node
pub struct QuicNode {
    _node_id: u32,
    endpoint: Endpoint,
    connections: Arc<RwLock<HashMap<u32, Connection>>>,
    _message_tx: mpsc::UnboundedSender<(u32, Bytes)>,
    quality_metrics: Arc<RwLock<HashMap<u32, ConnectionQuality>>>,
}

impl QuicNode {
    /// Create a new QUIC node
    pub async fn new(node_id: u32, bind_addr: SocketAddr) -> Result<Self> {
        let (cert, key) = generate_self_signed_cert()?;
        
        let server_config = configure_server(cert.clone(), key)?;
        let endpoint = Endpoint::server(server_config, bind_addr)?;
        
        info!("QUIC node {} listening on {}", node_id, bind_addr);

        let (message_tx, _message_rx) = mpsc::unbounded_channel();

        Ok(Self {
            _node_id: node_id,
            endpoint,
            connections: Arc::new(RwLock::new(HashMap::new())),
            _message_tx: message_tx,
            quality_metrics: Arc::new(RwLock::new(HashMap::new())),
        })
    }

    /// Connect to a peer
    pub async fn connect_to_peer(&self, peer: PeerAddress) -> Result<ConnectionQuality> {
        let addr: SocketAddr = format!("{}:{}", peer.host, peer.port)
            .parse()
            .context("Invalid peer address")?;

        info!("Connecting to peer {} at {}", peer.peer_id, addr);

        let client_config = configure_client()?;
        let connecting = self.endpoint.connect_with(client_config, addr, "localhost")?;
        
        let start = std::time::Instant::now();
        let conn = connecting.await.context("Failed to connect to peer")?;
        let latency = start.elapsed().as_millis() as f32;

        // Store connection
        self.connections.write().await.insert(peer.peer_id, conn.clone());

        let quality = ConnectionQuality {
            latency_ms: latency,
            jitter_ms: 0.0,
            packet_loss: 0.0,
        };

        self.quality_metrics.write().await.insert(peer.peer_id, quality.clone());

        // Start ping task for this connection
        self.start_ping_task(peer.peer_id, conn);

        info!("Connected to peer {} with {}ms latency", peer.peer_id, latency);
        Ok(quality)
    }

    /// Send a message to a peer
    pub async fn send_message(&self, peer_id: u32, data: Bytes) -> Result<()> {
        let connections = self.connections.read().await;
        let conn = connections.get(&peer_id)
            .context("Peer not connected")?;

        let mut send_stream = conn.open_uni().await?;
        send_stream.write_all(&data).await?;
        send_stream.finish()?;

        debug!("Sent {} bytes to peer {}", data.len(), peer_id);
        Ok(())
    }

    /// Disconnect from a peer
    pub async fn disconnect_peer(&self, peer_id: u32) -> Result<()> {
        let mut connections = self.connections.write().await;
        if let Some(conn) = connections.remove(&peer_id) {
            conn.close(0u32.into(), b"Disconnecting");
            info!("Disconnected from peer {}", peer_id);
        }
        Ok(())
    }

    /// Get connection quality for a peer
    pub async fn get_connection_quality(&self, peer_id: u32) -> Option<ConnectionQuality> {
        self.quality_metrics.read().await.get(&peer_id).cloned()
    }

    /// Get list of connected peer IDs
    pub async fn get_connected_peers(&self) -> Vec<u32> {
        self.connections.read().await.keys().copied().collect()
    }

    /// Start background ping task for latency measurement
    fn start_ping_task(&self, peer_id: u32, conn: Connection) {
        let quality_metrics = self.quality_metrics.clone();
        
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(5));
            let mut last_latency = 0.0f32;

            loop {
                interval.tick().await;

                // Send ping
                let start = std::time::Instant::now();
                match conn.open_uni().await {
                    Ok(mut stream) => {
                        if stream.write_all(b"PING").await.is_ok() && stream.finish().is_ok() {
                            let latency = start.elapsed().as_millis() as f32;
                            
                            // Calculate jitter
                            let jitter = if last_latency > 0.0 {
                                (latency - last_latency).abs()
                            } else {
                                0.0
                            };

                            let mut metrics = quality_metrics.write().await;
                            if let Some(quality) = metrics.get_mut(&peer_id) {
                                quality.latency_ms = latency;
                                quality.jitter_ms = quality.jitter_ms * 0.8 + jitter * 0.2;
                            }

                            last_latency = latency;
                            debug!("Ping to peer {}: {}ms", peer_id, latency);
                        }
                    }
                    Err(e) => {
                        warn!("Failed to ping peer {}: {}", peer_id, e);
                        break;
                    }
                }
            }
        });
    }

    /// Accept incoming connections (call this in a loop)
    pub async fn accept_connection(&self) -> Result<()> {
        while let Some(conn) = self.endpoint.accept().await {
            let connecting = conn.await?;
            info!("Accepted connection from {:?}", connecting.remote_address());
            
            // TODO: Implement peer ID exchange and register connection
            // For now, we just accept the connection
        }
        Ok(())
    }
}

/// Generate self-signed certificate for QUIC
fn generate_self_signed_cert() -> Result<(CertificateDer<'static>, PrivateKeyDer<'static>)> {
    let cert = rcgen::generate_simple_self_signed(vec!["localhost".to_string()])?;
    let key = PrivateKeyDer::Pkcs8(cert.key_pair.serialize_der().into());
    let cert_der = CertificateDer::from(cert.cert);
    Ok((cert_der, key))
}

/// Configure QUIC server
fn configure_server(cert: CertificateDer<'static>, key: PrivateKeyDer<'static>) -> Result<ServerConfig> {
    let mut server_config = ServerConfig::with_single_cert(vec![cert], key)?;
    
    let transport_config = Arc::get_mut(&mut server_config.transport)
        .context("Failed to get mutable transport config")?;
    
    transport_config.max_concurrent_uni_streams(1000u32.into());
    transport_config.max_idle_timeout(Some(std::time::Duration::from_secs(60).try_into()?));

    Ok(server_config)
}

/// Configure QUIC client with insecure certificate validation (for testing)
fn configure_client() -> Result<ClientConfig> {
    let crypto = rustls::ClientConfig::builder()
        .dangerous()
        .with_custom_certificate_verifier(Arc::new(SkipServerVerification))
        .with_no_client_auth();

    let mut client_config = ClientConfig::new(Arc::new(
        quinn::crypto::rustls::QuicClientConfig::try_from(crypto)?
    ));

    // Configure transport
    let mut transport = quinn::TransportConfig::default();
    transport.max_idle_timeout(Some(std::time::Duration::from_secs(60).try_into()?));
    client_config.transport_config(Arc::new(transport));

    Ok(client_config)
}

/// Skip server certificate verification (for testing only!)
#[derive(Debug)]
struct SkipServerVerification;

impl rustls::client::danger::ServerCertVerifier for SkipServerVerification {
    fn verify_server_cert(
        &self,
        _end_entity: &CertificateDer<'_>,
        _intermediates: &[CertificateDer<'_>],
        _server_name: &rustls::pki_types::ServerName<'_>,
        _ocsp_response: &[u8],
        _now: rustls::pki_types::UnixTime,
    ) -> Result<rustls::client::danger::ServerCertVerified, rustls::Error> {
        Ok(rustls::client::danger::ServerCertVerified::assertion())
    }

    fn verify_tls12_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn verify_tls13_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        vec![
            rustls::SignatureScheme::RSA_PKCS1_SHA256,
            rustls::SignatureScheme::ECDSA_NISTP256_SHA256,
            rustls::SignatureScheme::ED25519,
        ]
    }
}
