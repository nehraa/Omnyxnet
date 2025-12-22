// Include generated Cap'n Proto schema
pub mod schema_capnp {
    #![allow(warnings)]
    include!(concat!(env!("OUT_DIR"), "/schema_capnp.rs"));
}

pub mod auto_heal;
pub mod automated;
pub mod cache;
pub mod capabilities;
pub mod ces;
pub mod codecs; // Phase 1: Media codecs
pub mod compute; // Distributed Compute System
pub mod dcdn;
pub mod dht;
pub mod download;
pub mod ffi;
pub mod file_detector;
pub mod firewall;
pub mod go_client;
pub mod lookup;
pub mod metrics; // Phase 1: Performance metrics
pub mod network;
pub mod rpc;
pub mod storage;
pub mod store;
pub mod streaming; // Phase 2: Real-time voice/video streaming
pub mod types;
pub mod upload; // Distributed Content Delivery Network

// Re-export commonly used types for ease of use
pub use automated::{
    AutomatedDownloader, AutomatedUploader, DownloadResult, FileInfo, UploadResult,
};
pub use cache::{Cache, CacheStats, FileManifest};
pub use capabilities::HardwareCaps;
pub use ces::CesPipeline;
pub use codecs::{AudioConfig, AudioDecoder, AudioEncoder, VideoConfig}; // Phase 1: Media codecs
pub use dht::DhtNode;
pub use firewall::Firewall;
pub use lookup::{DiscoveryResult, LookupResult, LookupService};
pub use metrics::{LatencyTimer, MetricsTracker, PerformanceReport, ThroughputTracker}; // Phase 1: Metrics
pub use network::QuicNode;
pub use storage::StorageEngine;
pub use store::NodeStore;
pub use streaming::{
    AudioStreamReceiver, AudioStreamSender, StreamConfig, StreamPacket, StreamStats, StreamType,
    StreamingSession,
}; // Phase 2: Streaming
pub use types::{
    CesConfig, CompressionAlgorithm, ConnectionQuality, Message, Node, NodeStatus, PeerAddress,
};

// Distributed Compute System exports
pub use compute::{
    ChunkInfo, ComputeCapacity, ComputeConfig, ComputeEngine, ComputeError, ComputeExecutor,
    ComputeTask, ExecutionContext, JobManifest, MerkleTree, Metering, ResourceLimits,
    ResourceUsage, ResultVerifier, SandboxConfig, SplitStrategy, TaskResult, TaskStatus,
    VerificationMode, VerificationResult, WasmSandbox,
};

// DCDN System exports
pub use dcdn::{
    ChunkData, ChunkId, ChunkStore, DcdnConfig, FecAlgorithm, FecEngine, FecEngineConfig, FecGroup,
    P2PConfig, P2PEngine, PeerStats as DcdnPeerStats, QuicTransport, SignatureVerifier,
    StorageStats, VerificationMetrics,
};
