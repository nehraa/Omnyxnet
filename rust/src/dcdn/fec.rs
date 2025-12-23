//! Forward Error Correction using Reed-Solomon

use crate::dcdn::types::{FecGroupId, Packet, ParityPacket};
use anyhow::{Context, Result};
use dashmap::DashMap;
use reed_solomon_erasure::galois_8::ReedSolomon;
use std::sync::Arc;

/// FEC algorithm type
#[derive(Debug, Clone, Copy)]
pub enum FecAlgorithm {
    ReedSolomon,
}

/// FEC encoding/decoding engine
pub struct FecEngine {
    /// Active FEC groups being decoded
    active_groups: DashMap<FecGroupId, FecGroup>,
    /// Default configuration
    config: Arc<FecEngineConfig>,
}

#[derive(Debug, Clone)]
pub struct FecEngineConfig {
    pub block_size: usize,
    pub parity_count: usize,
    pub algorithm: FecAlgorithm,
}

/// A group of packets being encoded or decoded together
#[derive(Debug)]
pub struct FecGroup {
    pub id: FecGroupId,
    pub data_packets: Vec<Option<Packet>>,
    pub parity_packets: Vec<ParityPacket>,
    pub received_count: usize,
    pub expected_data_count: usize,
    pub expected_parity_count: usize,
}

impl FecEngine {
    /// Create a new FEC engine
    pub fn new(config: FecEngineConfig) -> Self {
        Self {
            active_groups: DashMap::new(),
            config: Arc::new(config),
        }
    }

    /// Encode data packets into parity packets
    pub fn encode(
        &self,
        packets: &[Packet],
        config: &FecEngineConfig,
    ) -> Result<Vec<ParityPacket>> {
        if packets.is_empty() {
            anyhow::bail!("Cannot encode empty packet list");
        }

        let k = config.block_size;
        let m = config.parity_count;

        if packets.len() > k {
            anyhow::bail!("Too many packets for block size: {} > {}", packets.len(), k);
        }

        // Create Reed-Solomon encoder
        let rs = ReedSolomon::new(k, m).context("Failed to create Reed-Solomon encoder")?;

        // Prepare shards (data + parity placeholders)
        let shard_len = packets.iter().map(|p| p.data.len()).max().unwrap_or(0);
        let mut shards: Vec<Vec<u8>> = Vec::with_capacity(k + m);

        // Add data shards
        for packet in packets {
            let mut shard = packet.data.to_vec();
            // Pad to uniform size
            shard.resize(shard_len, 0);
            shards.push(shard);
        }

        // Pad with empty shards if needed
        while shards.len() < k {
            shards.push(vec![0u8; shard_len]);
        }

        // Add parity shard placeholders
        for _ in 0..m {
            shards.push(vec![0u8; shard_len]);
        }

        // Encode
        rs.encode(&mut shards)
            .context("Reed-Solomon encoding failed")?;

        // Extract parity packets
        let group_id = packets[0].group_id;
        let parity_packets = shards[k..]
            .iter()
            .enumerate()
            .map(|(idx, shard)| ParityPacket {
                group_id,
                index: idx,
                data: bytes::Bytes::copy_from_slice(shard),
            })
            .collect();

        Ok(parity_packets)
    }

    /// Decode a FEC group to recover missing packets
    pub fn decode(&self, group: &FecGroup) -> Result<Vec<Packet>> {
        let k = group.expected_data_count;
        let m = group.expected_parity_count;

        // Check if we have enough packets
        if !self.can_recover(group) {
            anyhow::bail!(
                "Insufficient packets for recovery: have {}, need {}",
                group.received_count,
                k
            );
        }

        // Create Reed-Solomon decoder
        let rs = ReedSolomon::new(k, m).context("Failed to create Reed-Solomon decoder")?;

        // Prepare shards with present flags
        let shard_len = group
            .data_packets
            .iter()
            .filter_map(|p| p.as_ref())
            .map(|p| p.data.len())
            .max()
            .unwrap_or(0);

        let mut shards: Vec<Vec<u8>> = Vec::with_capacity(k + m);
        let mut present = vec![false; k + m];

        // Add data shards
        for (idx, packet_opt) in group.data_packets.iter().enumerate() {
            if let Some(packet) = packet_opt {
                let mut shard = packet.data.to_vec();
                shard.resize(shard_len, 0);
                shards.push(shard);
                present[idx] = true;
            } else {
                shards.push(vec![0u8; shard_len]);
            }
        }

        // Add parity shards
        for (idx, parity) in group.parity_packets.iter().enumerate() {
            let mut shard = parity.data.to_vec();
            shard.resize(shard_len, 0);
            shards.push(shard);
            if idx < m {
                present[k + idx] = true;
            }
        }

        // Reconstruct missing shards
        let mut shard_options: Vec<Option<Vec<u8>>> = shards
            .into_iter()
            .zip(present.iter())
            .map(|(s, &p)| if p { Some(s) } else { None })
            .collect();

        rs.reconstruct_data(&mut shard_options)
            .context("Reed-Solomon reconstruction failed")?;

        // Extract reconstructed shards, handling possible reconstruction failures
        let mut missing_indices = Vec::new();
        shards = shard_options
            .into_iter()
            .enumerate()
            .map(|(i, opt)| {
                if let Some(shard) = opt {
                    shard
                } else {
                    missing_indices.push(i);
                    Vec::new() // Placeholder, won't be used if error is returned
                }
            })
            .collect();

        if !missing_indices.is_empty() {
            anyhow::bail!(
                "Failed to reconstruct shards at indices: {:?}",
                missing_indices
            );
        }

        // Extract recovered data packets
        let mut recovered = Vec::new();
        for (idx, packet_opt) in group.data_packets.iter().enumerate() {
            if packet_opt.is_none() {
                // This packet was missing, use recovered data
                recovered.push(Packet {
                    group_id: group.id,
                    index: idx,
                    data: bytes::Bytes::copy_from_slice(&shards[idx]),
                });
            }
        }

        Ok(recovered)
    }

    /// Check if a group has enough packets for recovery
    pub fn can_recover(&self, group: &FecGroup) -> bool {
        group.received_count >= group.expected_data_count
    }

    /// Add a packet to an active FEC group
    pub fn add_packet(&self, packet: Packet) -> Result<()> {
        let group_id = packet.group_id;

        let mut group = self.active_groups.entry(group_id).or_insert_with(|| {
            FecGroup::new(group_id, self.config.block_size, self.config.parity_count)
        });

        let idx = packet.index;
        if idx < group.data_packets.len() && group.data_packets[idx].is_none() {
            group.data_packets[idx] = Some(packet);
            group.received_count += 1;
        }

        Ok(())
    }

    /// Add a parity packet to an active FEC group
    pub fn add_parity(&self, parity: ParityPacket) -> Result<()> {
        let group_id = parity.group_id;

        let mut group = self.active_groups.entry(group_id).or_insert_with(|| {
            FecGroup::new(group_id, self.config.block_size, self.config.parity_count)
        });

        group.parity_packets.push(parity);
        group.received_count += 1;

        Ok(())
    }

    /// Get an active FEC group
    pub fn get_group(
        &self,
        group_id: &FecGroupId,
    ) -> Option<dashmap::mapref::one::Ref<FecGroupId, FecGroup>> {
        self.active_groups.get(group_id)
    }

    /// Remove a completed FEC group
    pub fn remove_group(&self, group_id: &FecGroupId) {
        self.active_groups.remove(group_id);
    }
}

impl FecGroup {
    pub fn new(id: FecGroupId, data_count: usize, parity_count: usize) -> Self {
        Self {
            id,
            data_packets: vec![None; data_count],
            parity_packets: Vec::new(),
            received_count: 0,
            expected_data_count: data_count,
            expected_parity_count: parity_count,
        }
    }

    pub fn is_complete(&self) -> bool {
        self.data_packets.iter().all(|p| p.is_some())
    }
}

impl Default for FecEngineConfig {
    fn default() -> Self {
        Self {
            block_size: 16,
            parity_count: 2,
            algorithm: FecAlgorithm::ReedSolomon,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use bytes::Bytes;

    fn create_test_packets(group_id: FecGroupId, count: usize) -> Vec<Packet> {
        (0..count)
            .map(|i| Packet {
                group_id,
                index: i,
                data: Bytes::from(vec![i as u8; 100]),
            })
            .collect()
    }

    #[test]
    fn test_encode() {
        let config = FecEngineConfig {
            block_size: 8,
            parity_count: 2,
            algorithm: FecAlgorithm::ReedSolomon,
        };
        let engine = FecEngine::new(config.clone());

        let packets = create_test_packets(FecGroupId(1), 8);
        let parity = engine.encode(&packets, &config).unwrap();

        assert_eq!(parity.len(), 2);
    }

    #[test]
    fn test_recovery() {
        let config = FecEngineConfig {
            block_size: 8,
            parity_count: 2,
            algorithm: FecAlgorithm::ReedSolomon,
        };
        let engine = FecEngine::new(config.clone());

        // Create and encode packets
        let packets = create_test_packets(FecGroupId(1), 8);
        let parity = engine.encode(&packets, &config).unwrap();

        // Simulate loss of 2 packets
        let mut group = FecGroup::new(FecGroupId(1), 8, 2);
        for (i, packet) in packets.iter().enumerate() {
            if i != 3 && i != 7 {
                // Drop packets 3 and 7
                group.data_packets[i] = Some(packet.clone());
                group.received_count += 1;
            }
        }
        group.parity_packets = parity;
        group.received_count += 2;

        // Should be able to recover
        assert!(engine.can_recover(&group));

        let recovered = engine.decode(&group).unwrap();
        assert_eq!(recovered.len(), 2);
    }
}
