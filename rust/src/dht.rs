use anyhow::{Result, Context};
use libp2p::{
    kad::{self, store::MemoryStore, Mode, Record, RecordKey},
    swarm::{NetworkBehaviour, SwarmEvent, Swarm},
    identify, noise, ping, tcp, PeerId, Multiaddr,
};
use std::time::Duration;
use tracing::{info, warn, debug};

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

        let behaviour = PangeaBehaviour { kad, identify, ping };

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

        self.swarm.behaviour_mut().kad.put_record(record, kad::Quorum::One)
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
        self.swarm.behaviour_mut().kad.start_providing(key)
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
