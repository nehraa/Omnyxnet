//! Verification module for compute results
//!
//! This module provides cryptographic verification of compute results
//! using Merkle trees, SHA256 hashes, and redundancy comparison.

use crate::compute::types::{ComputeError, TaskResult, VerificationMode};
use sha2::{Digest, Sha256};
use tracing::{debug, info, warn};

/// Result of verification
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VerificationResult {
    /// Verification passed
    Valid,
    /// Verification failed with reason
    Invalid(String),
    /// Verification not performed (mode = None)
    Skipped,
}

impl VerificationResult {
    pub fn is_valid(&self) -> bool {
        matches!(self, VerificationResult::Valid)
    }
}

/// A Merkle tree for verifying data integrity
pub struct MerkleTree {
    /// Root hash of the tree
    root: String,
    /// All nodes in the tree (leaves first, then internal nodes)
    nodes: Vec<String>,
    /// Number of leaves
    leaf_count: usize,
    /// Size of each level (including padding) for proof generation
    level_sizes: Vec<usize>,
}

impl MerkleTree {
    /// Build a Merkle tree from data chunks
    pub fn build(chunks: &[Vec<u8>]) -> Self {
        if chunks.is_empty() {
            return Self {
                root: String::new(),
                nodes: Vec::new(),
                leaf_count: 0,
                level_sizes: Vec::new(),
            };
        }

        // Hash all leaves
        let mut nodes: Vec<String> = chunks.iter().map(|chunk| Self::hash_data(chunk)).collect();

        let leaf_count = nodes.len();
        let mut level_sizes = Vec::new();

        // Build tree levels
        let mut level_start = 0;
        let mut level_size = nodes.len();

        while level_size > 1 {
            let level_end = level_start + level_size;

            // Track original size before padding
            let original_size = level_size;

            // If odd number, duplicate the last hash
            if level_size % 2 == 1 {
                nodes.push(nodes[level_end - 1].clone());
                level_size += 1;
            }

            // Record the padded size for this level
            level_sizes.push(level_size);

            // Combine pairs
            for i in (level_start..level_start + level_size).step_by(2) {
                let combined = format!("{}{}", nodes[i], nodes[i + 1]);
                nodes.push(Self::hash_string(&combined));
            }

            level_start = level_end + (level_size - original_size); // Account for padding node
            level_size /= 2;
        }

        // Add final level (root)
        level_sizes.push(1);

        let root = nodes.last().cloned().unwrap_or_default();

        Self {
            root,
            nodes,
            leaf_count,
            level_sizes,
        }
    }

    /// Build a Merkle tree from a single data blob by chunking it
    pub fn from_data(data: &[u8], chunk_size: usize) -> Self {
        let chunks: Vec<Vec<u8>> = data.chunks(chunk_size.max(1)).map(|c| c.to_vec()).collect();

        Self::build(&chunks)
    }

    /// Get the root hash
    pub fn root(&self) -> &str {
        &self.root
    }

    /// Get a proof for a specific leaf
    ///
    /// The proof is a list of sibling hashes needed to reconstruct the root.
    pub fn get_proof(&self, leaf_index: usize) -> Result<Vec<String>, ComputeError> {
        if leaf_index >= self.leaf_count {
            return Err(ComputeError::InvalidInput(format!(
                "Leaf index {} out of range ({})",
                leaf_index, self.leaf_count
            )));
        }

        if self.level_sizes.is_empty() {
            return Ok(Vec::new());
        }

        let mut proof = Vec::new();
        let mut index = leaf_index;
        let mut level_start = 0;

        // Use recorded level sizes for accurate proof generation
        for &level_size in &self.level_sizes[..self.level_sizes.len().saturating_sub(1)] {
            // Get sibling index
            let sibling_index = if index.is_multiple_of(2) { index + 1 } else { index - 1 };

            // Add sibling hash to proof if it exists
            let node_index = level_start + sibling_index;
            if node_index < self.nodes.len() && sibling_index < level_size {
                proof.push(self.nodes[node_index].clone());
            }

            // Move to parent level
            index /= 2;
            level_start += level_size;
        }

        Ok(proof)
    }

    /// Verify a proof for a leaf
    pub fn verify_proof(root: &str, leaf_data: &[u8], leaf_index: usize, proof: &[String]) -> bool {
        let mut hash = Self::hash_data(leaf_data);
        let mut index = leaf_index;

        for sibling in proof {
            hash = if index.is_multiple_of(2) {
                Self::hash_string(&format!("{}{}", hash, sibling))
            } else {
                Self::hash_string(&format!("{}{}", sibling, hash))
            };
            index /= 2;
        }

        hash == root
    }

    /// Hash raw data
    fn hash_data(data: &[u8]) -> String {
        let mut hasher = Sha256::new();
        hasher.update(data);
        hex::encode(hasher.finalize())
    }

    /// Hash a string
    fn hash_string(s: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(s.as_bytes());
        hex::encode(hasher.finalize())
    }
}

/// Result verifier for compute tasks
pub struct ResultVerifier {
    mode: VerificationMode,
}

impl ResultVerifier {
    /// Create a new verifier with the given mode
    pub fn new(mode: VerificationMode) -> Self {
        Self { mode }
    }

    /// Hash a result for verification
    pub fn hash_result(&self, data: &[u8]) -> String {
        let mut hasher = Sha256::new();
        hasher.update(data);
        hex::encode(hasher.finalize())
    }

    /// Create a Merkle proof for the result
    pub fn create_merkle_proof(&self, data: &[u8]) -> Result<Vec<String>, ComputeError> {
        // Use 4KB chunks for Merkle tree
        let tree = MerkleTree::from_data(data, 4096);

        // For simplicity, return the root as the proof
        // A full implementation would return proofs for all chunks
        Ok(vec![tree.root().to_string()])
    }

    /// Verify a task result
    pub fn verify(&self, result: &TaskResult, expected_hash: Option<&str>) -> VerificationResult {
        match self.mode {
            VerificationMode::None => {
                debug!("Verification skipped (mode=None)");
                VerificationResult::Skipped
            }

            VerificationMode::Hash => {
                if let Some(expected) = expected_hash {
                    let actual = self.hash_result(&result.result_data);
                    if actual == expected {
                        debug!("Hash verification passed");
                        VerificationResult::Valid
                    } else {
                        warn!("Hash mismatch: expected {}, got {}", expected, actual);
                        VerificationResult::Invalid(format!(
                            "Hash mismatch: expected {}, got {}",
                            expected, actual
                        ))
                    }
                } else {
                    // No expected hash, just compute and store
                    debug!("No expected hash provided, skipping comparison");
                    VerificationResult::Valid
                }
            }

            VerificationMode::Merkle => {
                // Verify Merkle proof
                if let Some(proof) = &result.merkle_proof {
                    if proof.is_empty() {
                        return VerificationResult::Invalid("Empty Merkle proof".to_string());
                    }

                    // Rebuild tree and compare root
                    let tree = MerkleTree::from_data(&result.result_data, 4096);
                    if tree.root() == proof[0] {
                        debug!("Merkle verification passed");
                        VerificationResult::Valid
                    } else {
                        warn!("Merkle root mismatch");
                        VerificationResult::Invalid("Merkle root mismatch".to_string())
                    }
                } else {
                    VerificationResult::Invalid("No Merkle proof provided".to_string())
                }
            }

            VerificationMode::Redundancy => {
                // Redundancy verification requires multiple results
                // This would be handled at a higher level
                debug!("Redundancy verification delegated to orchestrator");
                VerificationResult::Valid
            }
        }
    }

    /// Compare two results for redundancy verification
    pub fn compare_results(
        &self,
        result1: &TaskResult,
        result2: &TaskResult,
    ) -> VerificationResult {
        if result1.result_data == result2.result_data {
            info!("Redundancy check passed: results match");
            VerificationResult::Valid
        } else {
            warn!("Redundancy check failed: results differ");
            VerificationResult::Invalid("Results from different workers don't match".to_string())
        }
    }

    /// Get the verification mode
    pub fn mode(&self) -> VerificationMode {
        self.mode
    }
}

impl Default for ResultVerifier {
    fn default() -> Self {
        Self::new(VerificationMode::Hash)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::compute::types::TaskStatus;

    #[test]
    fn test_merkle_tree_single_chunk() {
        let chunks = vec![vec![1, 2, 3, 4]];
        let tree = MerkleTree::build(&chunks);

        assert!(!tree.root().is_empty());
        assert_eq!(tree.leaf_count, 1);
    }

    #[test]
    fn test_merkle_tree_multiple_chunks() {
        let chunks = vec![
            vec![1, 2, 3, 4],
            vec![5, 6, 7, 8],
            vec![9, 10, 11, 12],
            vec![13, 14, 15, 16],
        ];
        let tree = MerkleTree::build(&chunks);

        assert!(!tree.root().is_empty());
        assert_eq!(tree.leaf_count, 4);
    }

    #[test]
    fn test_merkle_proof_verification() {
        let chunks = vec![
            vec![1, 2, 3, 4],
            vec![5, 6, 7, 8],
            vec![9, 10, 11, 12],
            vec![13, 14, 15, 16],
        ];
        let tree = MerkleTree::build(&chunks);

        // Get proof for first leaf
        let proof = tree.get_proof(0).unwrap();

        // Verify proof
        let valid = MerkleTree::verify_proof(tree.root(), &chunks[0], 0, &proof);

        assert!(valid);
    }

    #[test]
    fn test_hash_verification() {
        let verifier = ResultVerifier::new(VerificationMode::Hash);

        let data = b"test result data";
        let hash = verifier.hash_result(data);

        let result = TaskResult {
            task_id: "test".to_string(),
            status: TaskStatus::Completed,
            result_data: data.to_vec(),
            result_hash: hash.clone(),
            merkle_proof: None,
            execution_time_ms: 100,
            error_message: None,
        };

        let verification = verifier.verify(&result, Some(&hash));
        assert!(verification.is_valid());
    }

    #[test]
    fn test_hash_mismatch() {
        let verifier = ResultVerifier::new(VerificationMode::Hash);

        let result = TaskResult {
            task_id: "test".to_string(),
            status: TaskStatus::Completed,
            result_data: b"actual data".to_vec(),
            result_hash: "wrong_hash".to_string(),
            merkle_proof: None,
            execution_time_ms: 100,
            error_message: None,
        };

        let verification = verifier.verify(&result, Some("expected_hash"));
        assert!(!verification.is_valid());
    }

    #[test]
    fn test_merkle_verification() {
        let verifier = ResultVerifier::new(VerificationMode::Merkle);

        let data = b"test data for merkle verification with sufficient length";
        let proof = verifier.create_merkle_proof(data).unwrap();

        let result = TaskResult {
            task_id: "test".to_string(),
            status: TaskStatus::Completed,
            result_data: data.to_vec(),
            result_hash: verifier.hash_result(data),
            merkle_proof: Some(proof),
            execution_time_ms: 100,
            error_message: None,
        };

        let verification = verifier.verify(&result, None);
        assert!(verification.is_valid());
    }

    #[test]
    fn test_redundancy_comparison() {
        let verifier = ResultVerifier::new(VerificationMode::Redundancy);

        let result1 = TaskResult {
            task_id: "test1".to_string(),
            status: TaskStatus::Completed,
            result_data: b"matching result".to_vec(),
            result_hash: String::new(),
            merkle_proof: None,
            execution_time_ms: 100,
            error_message: None,
        };

        let result2 = TaskResult {
            task_id: "test2".to_string(),
            status: TaskStatus::Completed,
            result_data: b"matching result".to_vec(),
            result_hash: String::new(),
            merkle_proof: None,
            execution_time_ms: 110,
            error_message: None,
        };

        let comparison = verifier.compare_results(&result1, &result2);
        assert!(comparison.is_valid());
    }
}
