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

// Re-export commonly used types for ease of use
pub use capabilities::HardwareCaps;
pub use storage::StorageEngine;
pub use types::{Node, NodeStatus, PeerAddress, Message, ConnectionQuality, CesConfig};
pub use network::QuicNode;
pub use dht::DhtNode;
pub use ces::CesPipeline;
pub use store::NodeStore;
pub use firewall::Firewall;
pub use cache::{Cache, FileManifest, CacheStats};
pub use lookup::{LookupService, LookupResult, DiscoveryResult};
pub use automated::{AutomatedUploader, AutomatedDownloader, UploadResult, DownloadResult, FileInfo};
