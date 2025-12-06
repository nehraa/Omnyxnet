//! Integration tests for DCDN system

use pangea_ces::dcdn::*;
use bytes::Bytes;
use std::time::{Duration, Instant};

/// Helper function to create test chunk
fn create_test_chunk(id: u64, size: usize) -> ChunkData {
    ChunkData {
        id: ChunkId::new(id),
        sequence: id,
        timestamp: Instant::now(),
        source_peer: PeerId::new(1),
        signature: Signature::from_bytes([0u8; 64]),
        data: Bytes::from(vec![id as u8; size]),
        fec_group: Some(FecGroupId::new(1)),
    }
}

#[test]
fn test_dcdn_config_default() {
    let config = DcdnConfig::default();
    assert!(config.validate().is_ok());
    assert_eq!(config.storage.ring_buffer_size_mb, 100);
    assert_eq!(config.fec.default_block_size, 16);
    assert_eq!(config.p2p.regular_unchoke_count, 4);
}

#[test]
fn test_dcdn_config_validation() {
    let mut config = DcdnConfig::default();
    
    // Invalid: buffer size = 0
    config.storage.ring_buffer_size_mb = 0;
    assert!(config.validate().is_err());
    
    // Invalid: parity >= block size
    config.storage.ring_buffer_size_mb = 100;
    config.fec.default_parity_count = 16;
    assert!(config.validate().is_err());
    
    // Invalid: no unchoked peers
    config.fec.default_parity_count = 2;
    config.p2p.regular_unchoke_count = 0;
    assert!(config.validate().is_err());
}

#[test]
fn test_chunk_store_operations() {
    let store = ChunkStore::new(10, Duration::from_secs(120));
    
    // Insert chunks
    for i in 0..5 {
        let chunk = create_test_chunk(i, 100);
        assert!(store.insert(chunk).is_ok());
    }
    
    // Retrieve chunks
    for i in 0..5 {
        let chunk = store.get(&ChunkId::new(i));
        assert!(chunk.is_some());
        assert_eq!(chunk.unwrap().id, ChunkId::new(i));
    }
    
    // Check stats
    let stats = store.stats();
    assert_eq!(stats.chunk_count, 5);
    assert!(stats.size_bytes > 0);
}

#[test]
fn test_chunk_store_eviction() {
    let store = ChunkStore::new(3, Duration::from_secs(120));
    
    // Insert more chunks than capacity
    for i in 0..5 {
        let chunk = create_test_chunk(i, 100);
        store.insert(chunk).unwrap();
    }
    
    // First 2 chunks should be evicted
    assert!(store.get(&ChunkId::new(0)).is_none());
    assert!(store.get(&ChunkId::new(1)).is_none());
    
    // Last 3 chunks should exist
    assert!(store.get(&ChunkId::new(2)).is_some());
    assert!(store.get(&ChunkId::new(3)).is_some());
    assert!(store.get(&ChunkId::new(4)).is_some());
}

#[test]
fn test_chunk_store_expiration() {
    let store = ChunkStore::new(10, Duration::from_millis(10));
    
    let chunk = create_test_chunk(1, 100);
    store.insert(chunk).unwrap();
    
    // Wait for expiration
    std::thread::sleep(Duration::from_millis(20));
    
    let expired = store.list_expired(Instant::now());
    assert_eq!(expired.len(), 1);
    
    let evicted = store.evict_expired(Instant::now());
    assert_eq!(evicted, 1);
    
    // Chunk should be gone
    assert!(store.get(&ChunkId::new(1)).is_none());
}

#[test]
fn test_fec_encode_decode() {
    let config = FecEngineConfig {
        block_size: 8,
        parity_count: 2,
        algorithm: FecAlgorithm::ReedSolomon,
    };
    let engine = FecEngine::new(config.clone());
    
    // Create test packets
    let mut packets = Vec::new();
    for i in 0..8 {
        packets.push(Packet {
            group_id: FecGroupId::new(1),
            index: i,
            data: Bytes::from(vec![i as u8; 100]),
        });
    }
    
    // Encode
    let parity = engine.encode(&packets, &config).unwrap();
    assert_eq!(parity.len(), 2);
    
    // Simulate packet loss (drop 2 packets)
    let mut group = FecGroup::new(FecGroupId::new(1), 8, 2);
    for (i, packet) in packets.iter().enumerate() {
        if i != 3 && i != 7 {  // Drop packets 3 and 7
            group.data_packets[i] = Some(packet.clone());
            group.received_count += 1;
        }
    }
    group.parity_packets = parity;
    group.received_count += 2;
    
    // Verify can recover
    assert!(engine.can_recover(&group));
    
    // Decode to recover missing packets
    let recovered = engine.decode(&group).unwrap();
    assert_eq!(recovered.len(), 2);
}

#[tokio::test]
async fn test_p2p_engine_unchoke() {
    let config = P2PConfig {
        max_upload_mbps: 100,
        max_download_mbps: 100,
        unchoke_interval_seconds: 10,
        regular_unchoke_count: 3,
        optimistic_unchoke_count: 1,
    };
    let engine = P2PEngine::new(config);
    
    // Add peers with varying statistics
    for i in 1..=10 {
        let peer_id = PeerId::new(i);
        engine.add_peer(peer_id);
        
        // Simulate data transfer
        engine.update_downloaded(peer_id, i * 1000);
        engine.update_uploaded(peer_id, i * 500);
    }
    
    // Update unchoke set
    engine.update_unchoke_set().await.unwrap();
    
    let unchoked = engine.get_unchoked_peers().await;
    
    // Should have 3 regular + 1 optimistic = 4 peers
    assert!(unchoked.len() <= 4);
    assert!(unchoked.len() >= 3);
}

#[tokio::test]
async fn test_p2p_bandwidth_allocation() {
    let config = P2PConfig {
        max_upload_mbps: 100,
        ..Default::default()
    };
    let engine = P2PEngine::new(config);
    
    // Add 5 peers
    for i in 1..=5 {
        engine.add_peer(PeerId::new(i));
        engine.update_downloaded(PeerId::new(i), i * 1000);
    }
    
    engine.update_unchoke_set().await.unwrap();
    
    let allocations = engine.get_bandwidth_allocation().await;
    
    // Verify allocations
    assert!(!allocations.is_empty());
    
    let total_allocated: u64 = allocations.iter().map(|(_, bw)| bw).sum();
    let max_bytes_per_sec = 100 * 1_000_000;
    assert!(total_allocated <= max_bytes_per_sec);
}

#[test]
fn test_signature_verifier() {
    let verifier = SignatureVerifier::new();
    
    // Add trusted key
    let peer_id = PeerId::new(1);
    let public_key = PublicKey::from_bytes([42u8; 32]);
    verifier.add_trusted_key(peer_id, public_key);
    
    assert_eq!(verifier.trusted_key_count(), 1);
    
    // Verify chunk
    let chunk = create_test_chunk(1, 100);
    let result = verifier.verify(&chunk).unwrap();
    assert!(result);
    
    // Check metrics
    let (total, success, failed, _) = verifier.get_metrics();
    assert_eq!(total, 1);
    assert_eq!(success, 1);
    assert_eq!(failed, 0);
}

#[test]
fn test_signature_verifier_revocation() {
    let verifier = SignatureVerifier::new();
    
    let peer_id = PeerId::new(1);
    let public_key = PublicKey::from_bytes([42u8; 32]);
    
    verifier.add_trusted_key(peer_id, public_key);
    verifier.revoke_key(peer_id);
    
    assert!(verifier.is_revoked(&peer_id));
    assert_eq!(verifier.trusted_key_count(), 0);
    
    // Verification should fail for revoked peer
    let chunk = create_test_chunk(1, 100);
    let result = verifier.verify(&chunk).unwrap();
    assert!(!result);
}

#[test]
fn test_signature_batch_verification() {
    let verifier = SignatureVerifier::new();
    
    let peer_id = PeerId::new(1);
    let public_key = PublicKey::from_bytes([42u8; 32]);
    verifier.add_trusted_key(peer_id, public_key);
    
    // Create batch of chunks
    let chunks = vec![
        create_test_chunk(1, 100),
        create_test_chunk(2, 100),
        create_test_chunk(3, 100),
    ];
    
    // Verify batch
    let results = verifier.verify_batch(&chunks).unwrap();
    assert_eq!(results.len(), 3);
    assert!(results.iter().all(|&r| r));
    
    // Check metrics
    let (total, _, _, batch) = verifier.get_metrics();
    assert_eq!(total, 3);
    assert_eq!(batch, 1);
}

#[tokio::test]
async fn test_quic_transport_creation() {
    use pangea_ces::dcdn::config::{QuicConfig, CongestionAlgo};
    
    let config = QuicConfig {
        max_concurrent_connections: 100,
        max_streams_per_connection: 256,
        congestion_algorithm: CongestionAlgo::BBR,
        enable_gso: true,
        idle_timeout_ms: 30000,
    };
    
    let transport = QuicTransport::new(config);
    assert_eq!(transport.connection_count(), 0);
}

#[test]
fn test_fec_config_adaptive_params() {
    let config = FecEngineConfig {
        block_size: 16,
        parity_count: 2,
        algorithm: FecAlgorithm::ReedSolomon,
    };
    
    let fec_config = pangea_ces::dcdn::config::FecConfig {
        default_block_size: 16,
        default_parity_count: 2,
        adaptive: true,
    };
    
    // Test adaptive parameter selection
    let (block, parity) = fec_config.select_params(50, 0.01);
    assert!(block > 0);
    assert!(parity >= 2);
    
    // Higher latency should use larger blocks
    let (block2, _) = fec_config.select_params(300, 0.01);
    assert!(block2 >= block);
    
    // Higher loss rate should use more parity
    let (_, parity2) = fec_config.select_params(200, 0.05);
    assert!(parity2 >= parity);
}

#[test]
fn test_integration_chunk_lifecycle() {
    // Test complete lifecycle: create, store, retrieve, verify, evict
    
    // Setup
    let store = ChunkStore::new(10, Duration::from_secs(60));
    let verifier = SignatureVerifier::new();
    
    let peer_id = PeerId::new(1);
    let public_key = PublicKey::from_bytes([42u8; 32]);
    verifier.add_trusted_key(peer_id, public_key);
    
    // Create and store chunk
    let chunk = create_test_chunk(1, 1000);
    store.insert(chunk.clone()).unwrap();
    
    // Retrieve and verify
    let retrieved = store.get(&ChunkId::new(1)).unwrap();
    let verified = verifier.verify(&retrieved).unwrap();
    assert!(verified);
    
    // Check stats
    let stats = store.stats();
    assert_eq!(stats.chunk_count, 1);
    assert_eq!(stats.hits_total, 1);
}
