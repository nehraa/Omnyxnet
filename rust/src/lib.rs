// Include generated Cap'n Proto schema
pub mod schema_capnp {
    #![allow(warnings)]
    include!(concat!(env!("OUT_DIR"), "/schema_capnp.rs"));
}

pub mod capabilities;
pub mod storage;
pub mod types;
pub mod network;
pub mod dht;
pub mod ces;
pub mod codecs;  // Phase 1: Media codecs
pub mod metrics; // Phase 1: Performance metrics
pub mod streaming; // Phase 2: Real-time voice/video streaming
pub mod store;
pub mod rpc;
pub mod firewall;
pub mod go_client;
pub mod upload;
pub mod download;
pub mod cache;
pub mod lookup;
pub mod ffi;
pub mod auto_heal;
pub mod file_detector;
pub mod automated;
pub mod compute; // Distributed Compute System
pub mod dcdn;    // Distributed Content Delivery Network

// Re-export commonly used types for ease of use
pub use capabilities::HardwareCaps;
pub use storage::StorageEngine;
pub use types::{Node, NodeStatus, PeerAddress, Message, ConnectionQuality, CesConfig, CompressionAlgorithm};
pub use network::QuicNode;
pub use dht::DhtNode;
pub use ces::CesPipeline;
pub use codecs::{AudioConfig, AudioEncoder, AudioDecoder, VideoConfig};  // Phase 1: Media codecs
pub use metrics::{MetricsTracker, LatencyTimer, ThroughputTracker, PerformanceReport};  // Phase 1: Metrics
pub use streaming::{StreamConfig, StreamType, StreamingSession, AudioStreamSender, AudioStreamReceiver, StreamPacket, StreamStats};  // Phase 2: Streaming
pub use store::NodeStore;
pub use firewall::Firewall;
pub use cache::{Cache, FileManifest, CacheStats};
pub use lookup::{LookupService, LookupResult, DiscoveryResult};
pub use automated::{AutomatedUploader, AutomatedDownloader, UploadResult, DownloadResult, FileInfo};

// Distributed Compute System exports
pub use compute::{
    ComputeEngine, ComputeConfig, ComputeTask, TaskResult, TaskStatus,
    JobManifest, ChunkInfo, VerificationMode, SplitStrategy,
    ComputeError, ComputeCapacity,
    WasmSandbox, SandboxConfig,
    ResourceLimits, ResourceUsage, Metering,
    MerkleTree, ResultVerifier, VerificationResult,
    ComputeExecutor, ExecutionContext,
};

// DCDN System exports
pub use dcdn::{
    DcdnConfig, ChunkId, ChunkData, ChunkStore, StorageStats,
    FecEngine, FecEngineConfig, FecAlgorithm, FecGroup,
    P2PEngine, P2PConfig, PeerStats as DcdnPeerStats,
    QuicTransport, SignatureVerifier, VerificationMetrics,
};
