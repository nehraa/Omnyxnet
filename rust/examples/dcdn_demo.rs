//! DCDN Demo - Interactive demonstration of DCDN functionality
//!
//! This demo shows:
//! - ChunkStore operations with automatic eviction
//! - FEC encoding and recovery
//! - P2P bandwidth allocation with tit-for-tat
//! - Ed25519 signature verification
//! - Complete chunk lifecycle

use bytes::Bytes;
use ed25519_dalek::{Signer, SigningKey};
use pangea_ces::dcdn::*;
use std::time::{Duration, Instant};

fn main() {
    println!("\n🌐 DCDN System Demo");
    println!("{}", "=".repeat(60));

    demo_storage();
    demo_fec();
    demo_p2p();
    demo_verification();
    demo_integration();

    println!("\n✅ All demos completed successfully!");
}

fn demo_storage() {
    println!("\n📦 1. ChunkStore Demo (Lock-free Ring Buffer)");
    println!("{}", "-".repeat(60));

    // Create store with 5 chunk capacity, 60s TTL
    let store = ChunkStore::new(5, Duration::from_secs(60));
    println!("✓ Created ChunkStore with capacity: 5 chunks");

    // Insert some chunks
    for i in 1..=7 {
        let chunk = create_demo_chunk(i, 1024);
        store.insert(chunk).unwrap();
        println!("  → Inserted chunk {}", i);
    }

    // First 2 chunks should be evicted (ring buffer overflow)
    println!("\n  Checking eviction (ring buffer wraps after 5):");
    for i in 1..=7 {
        if store.get(&ChunkId::new(i)).is_some() {
            println!("    ✓ Chunk {} present", i);
        } else {
            println!("    ✗ Chunk {} evicted", i);
        }
    }

    let stats = store.stats();
    println!("\n  📊 Stats:");
    println!("    - Chunks stored: {}", stats.chunk_count);
    println!("    - Total size: {} bytes", stats.size_bytes);
    println!("    - Evictions: {}", stats.evictions_total);
    println!("    - Cache hits: {}", stats.hits_total);
}

fn demo_fec() {
    println!("\n🔧 2. FEC Engine Demo (Reed-Solomon Recovery)");
    println!("{}", "-".repeat(60));

    let config = FecEngineConfig {
        block_size: 8,
        parity_count: 2,
        algorithm: FecAlgorithm::ReedSolomon,
    };
    let engine = FecEngine::new(config.clone());
    println!("✓ Created FEC engine (k=8 data, m=2 parity)");

    // Create 8 data packets
    let packets: Vec<Packet> = (0..8)
        .map(|i| Packet {
            group_id: FecGroupId::new(1),
            index: i,
            data: Bytes::from(vec![i as u8; 100]),
        })
        .collect();

    // Encode to generate parity
    let parity = engine.encode(&packets, &config).unwrap();
    println!("✓ Encoded 8 packets → {} parity packets", parity.len());

    // Simulate packet loss (lose 2 packets)
    let mut group = FecGroup::new(FecGroupId::new(1), 8, 2);
    for (i, packet) in packets.iter().enumerate() {
        if i != 3 && i != 7 {
            // Drop packets 3 and 7
            group.data_packets[i] = Some(packet.clone());
            group.received_count += 1;
        } else {
            println!("  ✗ Packet {} lost", i);
        }
    }
    group.parity_packets = parity;
    group.received_count += 2;

    println!("\n  Recovery attempt:");
    if engine.can_recover(&group) {
        let recovered = engine.decode(&group).unwrap();
        println!(
            "  ✓ Successfully recovered {} lost packets!",
            recovered.len()
        );
    } else {
        println!("  ✗ Cannot recover (insufficient packets)");
    }
}

fn demo_p2p() {
    println!("\n🔄 3. P2P Engine Demo (Tit-for-Tat Bandwidth Allocation)");
    println!("{}", "-".repeat(60));

    let config = P2PConfig {
        max_upload_mbps: 100,
        max_download_mbps: 100,
        unchoke_interval_seconds: 10,
        regular_unchoke_count: 3,
        optimistic_unchoke_count: 1,
    };
    let engine = P2PEngine::new(config);
    println!("✓ Created P2P engine (100 Mbps up/down)");

    // Add 10 peers with varying statistics
    println!("\n  Adding 10 peers with varying contributions:");
    for i in 1..=10 {
        let peer_id = PeerId::new(i);
        engine.add_peer(peer_id);

        // Simulate data transfer (higher ID = more data)
        let downloaded = i * 1_000_000; // MB
        let uploaded = i * 500_000; // MB/2
        engine.update_downloaded(peer_id, downloaded);
        engine.update_uploaded(peer_id, uploaded);

        println!(
            "    Peer {}: ↓ {} MB, ↑ {} MB",
            i,
            downloaded / 1_000_000,
            uploaded / 1_000_000
        );
    }

    // Run unchoke algorithm
    let unchoked = tokio::runtime::Runtime::new().unwrap().block_on(async {
        engine.update_unchoke_set().await.unwrap();
        engine.get_unchoked_peers().await
    });

    println!("\n  🎯 Unchoked peers (receiving data):");
    for peer in &unchoked {
        println!("    ✓ Peer {} unchoked", peer.0);
    }
    println!("\n  Algorithm: Top 3 by score (0.7×↓ + 0.3×↑) + 1 optimistic");
}

fn demo_verification() {
    println!("\n🔐 4. Signature Verification Demo (Ed25519)");
    println!("{}", "-".repeat(60));

    let verifier = SignatureVerifier::new();

    // Create a keypair
    let signing_key = SigningKey::from_bytes(&[42u8; 32]);
    let verifying_key = signing_key.verifying_key();

    println!("✓ Generated Ed25519 keypair");
    println!(
        "  Public key: {}...{}",
        hex::encode(&verifying_key.to_bytes()[..4]),
        hex::encode(&verifying_key.to_bytes()[28..])
    );

    // Add trusted key
    let peer_id = PeerId::new(1);
    verifier.add_trusted_key(peer_id, PublicKey::from_bytes(verifying_key.to_bytes()));
    println!("✓ Added trusted key for peer 1");

    // Create and sign a chunk
    let data = Bytes::from(vec![1, 2, 3, 4, 5]);
    let signature = signing_key.sign(&data);

    let chunk = ChunkData {
        id: ChunkId::new(1),
        sequence: 1,
        timestamp: Instant::now(),
        source_peer: peer_id,
        signature: Signature::from_bytes(signature.to_bytes()),
        data,
        fec_group: None,
    };

    // Verify
    println!("\n  Verifying chunk signature:");
    match verifier.verify(&chunk) {
        Ok(true) => println!("  ✓ Signature valid!"),
        Ok(false) => println!("  ✗ Signature invalid"),
        Err(e) => println!("  ✗ Verification error: {}", e),
    }

    let (total, success, failed, _) = verifier.get_metrics();
    println!("\n  📊 Verification metrics:");
    println!("    - Total: {}", total);
    println!("    - Success: {}", success);
    println!("    - Failed: {}", failed);
}

fn demo_integration() {
    println!("\n🔗 5. Integration Demo (Complete Chunk Lifecycle)");
    println!("{}", "-".repeat(60));

    // Setup all components
    let store = ChunkStore::new(10, Duration::from_secs(60));
    let verifier = SignatureVerifier::new();

    let signing_key = SigningKey::from_bytes(&[42u8; 32]);
    let verifying_key = signing_key.verifying_key();
    let peer_id = PeerId::new(1);

    verifier.add_trusted_key(peer_id, PublicKey::from_bytes(verifying_key.to_bytes()));

    println!("✓ All components initialized");

    // Create, sign, store, retrieve, verify
    println!("\n  Complete lifecycle:");

    let data = Bytes::from(vec![0xDE, 0xAD, 0xBE, 0xEF]);
    let signature = signing_key.sign(&data);

    let chunk = ChunkData {
        id: ChunkId::new(1),
        sequence: 1,
        timestamp: Instant::now(),
        source_peer: peer_id,
        signature: Signature::from_bytes(signature.to_bytes()),
        data: data.clone(),
        fec_group: None,
    };

    println!("  1. ✓ Created chunk (4 bytes)");

    store.insert(chunk.clone()).unwrap();
    println!("  2. ✓ Stored chunk in ring buffer");

    let retrieved = store.get(&ChunkId::new(1)).unwrap();
    println!("  3. ✓ Retrieved chunk from storage");

    let verified = verifier.verify(&retrieved).unwrap();
    assert!(verified);
    println!("  4. ✓ Verified Ed25519 signature");

    assert_eq!(retrieved.data, data);
    println!("  5. ✓ Data integrity confirmed");

    println!("\n  🎉 Complete lifecycle successful!");
}

fn create_demo_chunk(id: u64, size: usize) -> ChunkData {
    let data = Bytes::from(vec![id as u8; size]);
    let signing_key = SigningKey::from_bytes(&[42u8; 32]);
    let signature = signing_key.sign(&data);

    ChunkData {
        id: ChunkId::new(id),
        sequence: id,
        timestamp: Instant::now(),
        source_peer: PeerId::new(1),
        signature: Signature::from_bytes(signature.to_bytes()),
        data,
        fec_group: Some(FecGroupId::new(1)),
    }
}
