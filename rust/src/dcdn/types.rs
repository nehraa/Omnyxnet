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
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Signature(pub [u8; 64]);

/// Ed25519 public key
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct PublicKey(pub [u8; 32]);

/// Chunk metadata and data
#[derive(Debug, Clone)]
pub struct ChunkData {
    pub id: ChunkId,
    pub sequence: u64,
    pub timestamp: Instant,
    pub source_peer: PeerId,
    pub signature: Signature,
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
#[derive(Debug, Clone, Default)]
pub struct PeerStats {
    pub uploaded_bytes: u64,
    pub downloaded_bytes: u64,
    pub last_interaction: Option<Instant>,
    pub reliability_score: f32,
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
