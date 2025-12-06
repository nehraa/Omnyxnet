//! DCDN (Distributed Content Delivery Network) Module
//!
//! This module implements a distributed CDN system for video streaming with:
//! - QUIC-based transport for low-latency packet delivery
//! - Reed-Solomon FEC for packet recovery
//! - P2P mesh with tit-for-tat incentives
//! - Ed25519 signature verification for content authenticity
//! - Lock-free ring buffer for chunk storage
//!
//! Based on design specification in dcdn_design_spec.txt

pub mod types;
pub mod transport;
pub mod storage;
pub mod fec;
pub mod p2p;
pub mod verifier;
pub mod config;

pub use types::*;
pub use transport::QuicTransport;
pub use storage::ChunkStore;
pub use types::StorageStats;
pub use fec::{FecEngine, FecEngineConfig, FecAlgorithm, FecGroup};
pub use p2p::{P2PEngine, P2PConfig};
pub use verifier::{SignatureVerifier, VerificationMetrics};
pub use config::DcdnConfig;
