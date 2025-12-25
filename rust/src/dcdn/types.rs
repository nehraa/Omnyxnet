//! Core data types for DCDN system

use bytes::Bytes;
use serde::{Deserialize, Serialize};
use std::time::Instant;

/// Unique identifier for a chunk
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ChunkId(pub u64);

/// Unique identifier for a peer in the network
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct PeerId(pub u64);

/// Unique identifier for a FEC group
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct FecGroupId(pub u64);

/// Ed25519 signature for chunk verification
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Signature(pub [u8; 64]);

/// Ed25519 public key
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct PublicKey(pub [u8; 32]);

/// Chunk metadata and data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChunkData {
    pub id: ChunkId,
    pub sequence: u64,
    /// Unix timestamp in milliseconds for proper serialization and TTL logic
    #[serde(with = "timestamp_serde")]
    pub timestamp: Instant,
    pub source_peer: PeerId,
    #[serde(with = "signature_serde")]
    pub signature: Signature,
    #[serde(with = "bytes_serde")]
    pub data: Bytes,
    pub fec_group: Option<FecGroupId>,
}

/// Statistics for chunk storage
#[derive(Debug, Clone, Default)]
pub struct StorageStats {
    pub size_bytes: usize,
    pub chunk_count: usize,
    pub evictions_total: u64,
    pub hits_total: u64,
    pub misses_total: u64,
}

/// Peer statistics for P2P engine
#[derive(Debug, Clone)]
pub struct PeerStats {
    pub uploaded_bytes: u64,
    pub downloaded_bytes: u64,
    pub last_interaction: Option<Instant>,
    pub reliability_score: f32,
}

impl Default for PeerStats {
    fn default() -> Self {
        Self {
            uploaded_bytes: 0,
            downloaded_bytes: 0,
            last_interaction: None,
            // Initialize to 1.0 so new peers can be unchoked through regular algorithm
            reliability_score: 1.0,
        }
    }
}

/// Network packet for transmission
#[derive(Debug, Clone)]
pub struct Packet {
    pub group_id: FecGroupId,
    pub index: usize,
    pub data: Bytes,
}

/// Parity packet for FEC
#[derive(Debug, Clone)]
pub struct ParityPacket {
    pub group_id: FecGroupId,
    pub index: usize,
    pub data: Bytes,
}

impl ChunkId {
    pub fn new(id: u64) -> Self {
        ChunkId(id)
    }
}

impl PeerId {
    pub fn new(id: u64) -> Self {
        PeerId(id)
    }
}

impl FecGroupId {
    pub fn new(id: u64) -> Self {
        FecGroupId(id)
    }
}

impl Signature {
    pub fn from_bytes(bytes: [u8; 64]) -> Self {
        Signature(bytes)
    }
}

impl PublicKey {
    pub fn from_bytes(bytes: [u8; 32]) -> Self {
        PublicKey(bytes)
    }
}

// Serde helper for Signature
mod signature_serde {
    use super::Signature;
    use serde::{Deserialize, Deserializer, Serializer};

    pub fn serialize<S>(sig: &Signature, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_bytes(&sig.0)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Signature, D::Error>
    where
        D: Deserializer<'de>,
    {
        let bytes = <Vec<u8>>::deserialize(deserializer)?;
        if bytes.len() != 64 {
            return Err(serde::de::Error::custom("signature must be 64 bytes"));
        }
        let mut arr = [0u8; 64];
        arr.copy_from_slice(&bytes);
        Ok(Signature(arr))
    }
}

// Serde helper for Bytes
mod bytes_serde {
    use bytes::Bytes;
    use serde::{Deserialize, Deserializer, Serializer};

    pub fn serialize<S>(bytes: &Bytes, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_bytes(bytes)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Bytes, D::Error>
    where
        D: Deserializer<'de>,
    {
        let vec = <Vec<u8>>::deserialize(deserializer)?;
        Ok(Bytes::from(vec))
    }
}

// Serde helper for Instant (serializes as Unix timestamp in milliseconds)
mod timestamp_serde {
    use serde::{Deserialize, Deserializer, Serializer};
    use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

    // Store the program start time to convert between Instant and SystemTime
    lazy_static::lazy_static! {
        static ref PROGRAM_START: (Instant, SystemTime) = (Instant::now(), SystemTime::now());
    }

    pub fn serialize<S>(instant: &Instant, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let elapsed = instant.duration_since(PROGRAM_START.0);
        let system_time = PROGRAM_START.1 + elapsed;
        let timestamp_ms = system_time
            .duration_since(UNIX_EPOCH)
            .map_err(|e| serde::ser::Error::custom(format!("Time error: {}", e)))?
            .as_millis() as u64;
        serializer.serialize_u64(timestamp_ms)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Instant, D::Error>
    where
        D: Deserializer<'de>,
    {
        let timestamp_ms = u64::deserialize(deserializer)?;
        let system_time = UNIX_EPOCH + Duration::from_millis(timestamp_ms);
        let elapsed_since_start = system_time
            .duration_since(PROGRAM_START.1)
            .unwrap_or(Duration::ZERO);
        Ok(PROGRAM_START.0 + elapsed_since_start)
    }
}
