use async_trait::async_trait;
use std::io;
use tokio::io::AsyncWriteExt;

#[async_trait]
pub trait StorageEngine: Send + Sync {
    async fn write_block(&mut self, index: u64, data: &[u8]) -> io::Result<()>;
}

pub struct ThreadedEngine {}

impl ThreadedEngine {
    pub fn new() -> Self {
        ThreadedEngine {}
    }
}

#[async_trait]
impl StorageEngine for ThreadedEngine {
    async fn write_block(&mut self, _index: u64, _data: &[u8]) -> io::Result<()> {
        // Very small scaffold: write to a temp file sequentially
        let path = std::env::temp_dir().join("pangea_scaffold_data.bin");
        let mut f = tokio::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .await?;
        f.write_all(_data).await?;
        Ok(())
    }
}

// Optional UringEngine stub (only compiled when feature "uring" is enabled)
#[cfg(feature = "uring")]
pub mod uring {
    use super::StorageEngine;
    use async_trait::async_trait;
    use std::io;

    pub struct UringEngine {}

    impl UringEngine {
        pub fn new() -> Self {
            UringEngine {}
        }
    }

    #[async_trait]
    impl StorageEngine for UringEngine {
        async fn write_block(&mut self, _index: u64, _data: &[u8]) -> io::Result<()> {
            // Placeholder: implement tokio-uring basedwrites in a real implementation
            Ok(())
        }
    }
}
