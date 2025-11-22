use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use anyhow::Result;
use tracing::info;

use crate::types::{Node, NodeStatus};

/// Thread-safe node storage
pub struct NodeStore {
    nodes: Arc<RwLock<HashMap<u32, Node>>>,
}

impl NodeStore {
    pub fn new() -> Self {
        Self {
            nodes: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Add or update a node
    pub async fn upsert_node(&self, node: Node) {
        let mut nodes = self.nodes.write().await;
        nodes.insert(node.id, node);
    }

    /// Get a node by ID
    pub async fn get_node(&self, id: u32) -> Option<Node> {
        let nodes = self.nodes.read().await;
        nodes.get(&id).cloned()
    }

    /// Get all nodes
    pub async fn get_all_nodes(&self) -> Vec<Node> {
        let nodes = self.nodes.read().await;
        nodes.values().cloned().collect()
    }

    /// Update node latency
    pub async fn update_latency(&self, node_id: u32, latency_ms: f32) -> Result<()> {
        let mut nodes = self.nodes.write().await;
        if let Some(node) = nodes.get_mut(&node_id) {
            node.update_latency(latency_ms);
            info!("Updated latency for node {}: {}ms", node_id, latency_ms);
        }
        Ok(())
    }

    /// Update node threat score
    pub async fn update_threat_score(&self, node_id: u32, threat_score: f32) -> Result<()> {
        let mut nodes = self.nodes.write().await;
        if let Some(node) = nodes.get_mut(&node_id) {
            node.update_threat_score(threat_score);
            info!("Updated threat score for node {}: {}", node_id, threat_score);
        }
        Ok(())
    }

    /// Update packet loss
    pub async fn update_packet_loss(&self, node_id: u32, packet_loss: f32) -> Result<()> {
        let mut nodes = self.nodes.write().await;
        if let Some(node) = nodes.get_mut(&node_id) {
            node.update_packet_loss(packet_loss);
        }
        Ok(())
    }

    /// Remove a node
    pub async fn remove_node(&self, id: u32) {
        let mut nodes = self.nodes.write().await;
        nodes.remove(&id);
    }

    /// Get nodes by status
    pub async fn get_nodes_by_status(&self, status: NodeStatus) -> Vec<Node> {
        let nodes = self.nodes.read().await;
        nodes.values()
            .filter(|n| n.status == status)
            .cloned()
            .collect()
    }

    /// Get healthy nodes (Active status with good health score)
    pub async fn get_healthy_nodes(&self, min_health: f32) -> Vec<Node> {
        let nodes = self.nodes.read().await;
        nodes.values()
            .filter(|n| n.status == NodeStatus::Active && n.health_score() >= min_health)
            .cloned()
            .collect()
    }
}

impl Default for NodeStore {
    fn default() -> Self {
        Self::new()
    }
}
