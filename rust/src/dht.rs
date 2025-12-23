use anyhow::{Context, Result};
use libp2p::{
    identify,
    kad::{self, store::MemoryStore, Mode, Record, RecordKey},
    noise, ping,
    swarm::{NetworkBehaviour, Swarm, SwarmEvent},
    tcp, Multiaddr, PeerId,
};
use std::{
    collections::HashMap,
    sync::Arc,
    time::Duration,
};
use futures::future::{select, Either};
use tokio::{sync::RwLock, time::sleep};
use tracing::{debug, info, warn};

#[derive(NetworkBehaviour)]
pub struct PangeaBehaviour {
    pub kad: kad::Behaviour<MemoryStore>,
    pub identify: identify::Behaviour,
    pub ping: ping::Behaviour,
}

pub struct DhtNode {
    swarm: Swarm<PangeaBehaviour>,
    peer_id: PeerId,
    #[allow(dead_code)]
    bootstrap_peers: Vec<Multiaddr>,
}

impl DhtNode {
    /// Create a new DHT node
    pub async fn new(_port: u16, bootstrap_peers: Vec<Multiaddr>) -> Result<Self> {
        // Generate keypair
        let local_key = libp2p::identity::Keypair::generate_ed25519();
        let peer_id = PeerId::from(local_key.public());

        info!("DHT node initialized with PeerId: {}", peer_id);

        // Create Kademlia DHT
        let protocol_id = libp2p::StreamProtocol::new("/pangea/kad/1.0.0");
        let mut kad_config = kad::Config::new(protocol_id);
        kad_config.set_query_timeout(Duration::from_secs(60));

        let store = MemoryStore::new(peer_id);
        let mut kad = kad::Behaviour::with_config(peer_id, store, kad_config);

        // Set DHT to server mode
        kad.set_mode(Some(Mode::Server));

        // Add bootstrap peers
        for addr in &bootstrap_peers {
            kad.add_address(&peer_id, addr.clone());
        }

        // Create identify protocol
        let identify = identify::Behaviour::new(identify::Config::new(
            "/pangea/1.0.0".to_string(),
            local_key.public(),
        ));

        // Create ping protocol
        let ping = ping::Behaviour::new(ping::Config::new());

        let behaviour = PangeaBehaviour {
            kad,
            identify,
            ping,
        };

        // Build the swarm
        let swarm = libp2p::SwarmBuilder::with_existing_identity(local_key)
            .with_tokio()
            .with_tcp(
                tcp::Config::default(),
                noise::Config::new,
                libp2p::yamux::Config::default,
            )?
            .with_behaviour(|_key| behaviour)?
            .with_swarm_config(|c| c.with_idle_connection_timeout(Duration::from_secs(60)))
            .build();

        Ok(Self {
            swarm,
            peer_id,
            bootstrap_peers,
        })
    }

    /// Start listening on a specific address
    pub fn listen_on(&mut self, addr: Multiaddr) -> Result<()> {
        self.swarm.listen_on(addr.clone())?;
        info!("DHT node listening on {}", addr);
        Ok(())
    }

    /// Bootstrap the DHT by connecting to bootstrap peers
    pub fn bootstrap(&mut self) -> Result<()> {
        if let Err(e) = self.swarm.behaviour_mut().kad.bootstrap() {
            warn!("DHT bootstrap failed: {}", e);
        } else {
            info!("DHT bootstrap initiated");
        }
        Ok(())
    }

    /// Put a record in the DHT
    pub fn put_record(&mut self, key: Vec<u8>, value: Vec<u8>) -> Result<()> {
        let record = Record {
            key: RecordKey::new(&key),
            value,
            publisher: Some(self.peer_id),
            expires: None,
        };

        self.swarm
            .behaviour_mut()
            .kad
            .put_record(record, kad::Quorum::One)
            .context("Failed to put record")?;

        debug!("Put record with key: {:?}", key);
        Ok(())
    }

    /// Get a record from the DHT
    pub fn get_record(&mut self, key: Vec<u8>) -> Result<()> {
        let key = RecordKey::new(&key);
        self.swarm.behaviour_mut().kad.get_record(key);
        debug!("Requested record with key");
        Ok(())
    }

    /// Find providers for a given file hash
    pub fn find_providers(&mut self, file_hash: Vec<u8>) -> Result<()> {
        let key = RecordKey::new(&file_hash);
        self.swarm.behaviour_mut().kad.get_providers(key);
        debug!("Finding providers for file hash");
        Ok(())
    }

    /// Start providing a file (announce that this node has a shard)
    pub fn start_providing(&mut self, file_hash: Vec<u8>) -> Result<()> {
        let key = RecordKey::new(&file_hash);
        self.swarm
            .behaviour_mut()
            .kad
            .start_providing(key)
            .context("Failed to start providing")?;
        info!("Started providing file");
        Ok(())
    }

    /// Get the PeerId of this node
    pub fn peer_id(&self) -> &PeerId {
        &self.peer_id
    }

    /// Process swarm events (call this in a loop)
    pub async fn next_event(&mut self) -> Option<SwarmEvent<PangeaBehaviourEvent>> {
        use futures::StreamExt;
        self.swarm.next().await
    }

    /// Connect to a peer
    pub fn dial(&mut self, addr: Multiaddr) -> Result<()> {
        self.swarm.dial(addr.clone())?;
        info!("Dialing peer at {}", addr);
        Ok(())
    }

    /// Get list of connected peers
    pub fn connected_peers(&self) -> Vec<PeerId> {
        self.swarm.connected_peers().copied().collect()
    }
}

/// Helper to parse multiaddrs from strings
pub fn parse_multiaddr(s: &str) -> Result<Multiaddr> {
    s.parse().context("Failed to parse multiaddr")
}

/// Create a local multiaddr for testing
pub fn local_multiaddr(port: u16) -> Multiaddr {
    format!("/ip4/127.0.0.1/tcp/{}", port)
        .parse()
        .expect("Hard-coded local multiaddr must be valid; check dht::local_multiaddr()")
}

/// In-memory dual DHT facade that issues parallel queries against a fast "local"
/// table and a slower "global" table, returning the first successful hit.
#[derive(Clone, Default)]
pub struct DualDht {
    local: Arc<RwLock<HashMap<Vec<u8>, Vec<u8>>>>,
    global: Arc<RwLock<HashMap<Vec<u8>, Vec<u8>>>>,
    local_latency: Duration,
    global_latency: Duration,
}

impl DualDht {
    /// Create a new dual DHT with configurable simulated latency for local/global caches.
    pub fn new(local_latency: Duration, global_latency: Duration) -> Self {
        Self {
            local: Arc::new(RwLock::new(HashMap::new())),
            global: Arc::new(RwLock::new(HashMap::new())),
            local_latency,
            global_latency,
        }
    }

    /// Insert a value into both local and global tables.
    pub async fn put(&self, key: Vec<u8>, value: Vec<u8>) {
        {
            let mut l = self.local.write().await;
            l.insert(key.clone(), value.clone());
        }
        {
            let mut g = self.global.write().await;
            g.insert(key, value);
        }
    }

    /// Insert only into the local cache (e.g., recent accesses).
    pub async fn put_local(&self, key: Vec<u8>, value: Vec<u8>) {
        let mut l = self.local.write().await;
        l.insert(key, value);
    }

    /// Insert only into the global table (network source of truth).
    pub async fn put_global(&self, key: Vec<u8>, value: Vec<u8>) {
        let mut g = self.global.write().await;
        g.insert(key, value);
    }

    /// Query both local and global tables in parallel, returning the first hit.
    pub async fn get_first(&self, key: &[u8]) -> Option<Vec<u8>> {
        let key_vec = key.to_vec();
        let local = self.local.clone();
        let global = self.global.clone();
        let local_latency = self.local_latency;
        let global_latency = self.global_latency;

        let local_key = key_vec.clone();
        let local_fut = async move {
            sleep(local_latency).await;
            local.read().await.get(&local_key).cloned()
        };

        let global_fut = async move {
            sleep(global_latency).await;
            global.read().await.get(&key_vec).cloned()
        };

        match select(Box::pin(local_fut), Box::pin(global_fut)).await {
            Either::Left((local_res, pending_global)) => {
                if local_res.is_some() {
                    local_res
                } else {
                    pending_global.await
                }
            }
            Either::Right((global_res, pending_local)) => {
                if global_res.is_some() {
                    global_res
                } else {
                    pending_local.await
                }
            }
        }
    }
}

#[cfg(test)]
mod dual_tests {
    use super::DualDht;
    use std::time::Duration;

    #[tokio::test]
    async fn returns_local_first_when_available() {
        let dual = DualDht::new(Duration::from_millis(5), Duration::from_millis(50));
        dual.put_local(b"key".to_vec(), b"local".to_vec()).await;
        dual.put_global(b"key".to_vec(), b"global".to_vec()).await;

        let res = dual.get_first(b"key").await;
        assert_eq!(res.unwrap(), b"local".to_vec());
    }

    #[tokio::test]
    async fn falls_back_to_global_when_local_missing() {
        let dual = DualDht::new(Duration::from_millis(5), Duration::from_millis(10));
        dual.put_global(b"key".to_vec(), b"global".to_vec()).await;

        let res = dual.get_first(b"key").await;
        assert_eq!(res.unwrap(), b"global".to_vec());
    }

    #[tokio::test]
    async fn returns_none_when_not_found() {
        let dual = DualDht::new(Duration::from_millis(1), Duration::from_millis(1));
        let res = dual.get_first(b"missing").await;
        assert!(res.is_none());
    }
}
