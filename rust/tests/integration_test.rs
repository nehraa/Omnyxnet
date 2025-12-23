use pangea_ces::*;

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[tokio::test]
    async fn test_node_store() {
        let store = store::NodeStore::new();

        // Create and insert node
        let node = types::Node::new(1);
        store.upsert_node(node.clone()).await;

        // Retrieve node
        let retrieved = store.get_node(1).await.unwrap();
        assert_eq!(retrieved.id, 1);

        // Update latency
        store.update_latency(1, 50.0).await.unwrap();
        let updated = store.get_node(1).await.unwrap();
        assert_eq!(updated.latency_ms, 50.0);

        // Update threat score
        store.update_threat_score(1, 0.9).await.unwrap();
        let updated = store.get_node(1).await.unwrap();
        assert_eq!(updated.status, types::NodeStatus::Dead);
    }

    #[tokio::test]
    async fn test_health_scoring() {
        let mut node = types::Node::new(1);

        // Perfect health
        node.latency_ms = 10.0;
        node.jitter_ms = 1.0;
        node.packet_loss = 0.0;
        assert!(node.health_score() > 0.9);

        // Bad health
        node.latency_ms = 600.0;
        node.jitter_ms = 60.0;
        node.packet_loss = 0.6;
        assert!(node.health_score() < 0.5);
    }

    #[tokio::test]
    async fn test_firewall() {
        let firewall = firewall::Firewall::default();
        let ip: std::net::IpAddr = "127.0.0.1".parse().unwrap();

        // Initially blocked
        assert!(!firewall.is_allowed(ip).await);

        // Allow
        firewall.allow_ip(ip).await;
        assert!(firewall.is_allowed(ip).await);

        // Block again
        firewall.block_ip(ip).await;
        assert!(!firewall.is_allowed(ip).await);
    }

    #[test]
    fn test_capabilities_probe() {
        let caps = capabilities::HardwareCaps::probe();

        assert!(caps.cpu_cores > 0);
        assert!(caps.ram_gb > 0);

        // At least one should be false (not all systems have everything)
        println!(
            "Capabilities: {:?}",
            (
                caps.has_avx2,
                caps.has_neon,
                caps.has_io_uring,
                caps.has_ebpf
            )
        );
    }

    #[test]
    fn test_ces_config_adaptive() {
        let caps = capabilities::HardwareCaps::probe();
        let config = types::CesConfig::adaptive(&caps, 1024 * 1024, 1.0);

        assert!(config.chunk_size > 0);
        assert!(config.shard_count > 0);
        assert!(config.parity_count > 0);
        assert!(config.compression_level > 0);
    }

    #[tokio::test]
    async fn test_quic_network_creation() {
        let addr = "127.0.0.1:0".parse().unwrap(); // Random port
        let result = network::QuicNode::new(1, addr).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_dht_node_creation() {
        let result = dht::DhtNode::new(0, vec![]).await; // Random port
        assert!(result.is_ok());
    }
}
