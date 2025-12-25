//! Threshold Distributed Key Generation (t-of-n) helpers.
//!
//! This module provides a small, self-contained implementation of Shamir-style
//! secret sharing over GF(256) to support t-of-n key distribution. It is used
//! when shard holders need to derive per-recipient encryption material without
//! exposing the original secret.

use rand::{rngs::OsRng, RngCore};
use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum DkgError {
    #[error("threshold must be between 1 and 255 and <= share_count")]
    InvalidThreshold,
    #[error("duplicate share indices are not allowed")]
    DuplicateShare,
    #[error("insufficient shares to reconstruct secret")]
    InsufficientShares,
    #[error("cannot invert zero in GF(256)")]
    NonInvertible,
}

/// A single share (x, y) in GF(256) space.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Share {
    pub x: u8,
    pub data: Vec<u8>,
}

/// Generate `share_count` shares with a reconstruction threshold of `threshold`.
///
/// The secret may be any byte string. Shares are independent and can be
/// distributed to shard holders; any `threshold` distinct shares are sufficient
/// to reconstruct the secret.
pub fn generate_shares(
    secret: &[u8],
    threshold: u8,
    share_count: u8,
) -> Result<Vec<Share>, DkgError> {
    if threshold == 0 || threshold > share_count {
        return Err(DkgError::InvalidThreshold);
    }

    // Pre-generate random coefficients for each byte position.
    let mut rng = OsRng;
    let mut shares = Vec::with_capacity(share_count as usize);

    for x in 1..=share_count {
        shares.push(Share {
            x,
            data: vec![0u8; secret.len()],
        });
    }

    for (idx, &secret_byte) in secret.iter().enumerate() {
        // Polynomial: a0 = secret_byte, a1..a_{t-1} random
        let mut coeffs = vec![secret_byte];
        for _ in 1..threshold {
            coeffs.push(rng.next_u32() as u8);
        }

        // Evaluate polynomial at each x
        for share in &mut shares {
            let mut y = 0u8;
            let mut power = 1u8; // x^0
            for &c in &coeffs {
                y = gf_add(y, gf_mul(c, power));
                power = gf_mul(power, share.x);
            }
            share.data[idx] = y;
        }
    }

    Ok(shares)
}

/// Reconstruct the secret from any `threshold` distinct shares.
pub fn reconstruct_secret(shares: &[Share], threshold: u8) -> Result<Vec<u8>, DkgError> {
    if threshold == 0 || threshold > shares.len() as u8 {
        return Err(DkgError::InsufficientShares);
    }

    // Ensure x values are unique
    {
        let mut seen = std::collections::HashSet::new();
        for s in shares.iter().take(threshold as usize) {
            if !seen.insert(s.x) {
                return Err(DkgError::DuplicateShare);
            }
        }
    }

    let secret_len = shares.first().map(|s| s.data.len()).unwrap_or(0);

    let mut result = vec![0u8; secret_len];

    for (byte_idx, result_byte) in result.iter_mut().enumerate().take(secret_len) {
        let mut acc = 0u8;

        for (j, share_j) in shares.iter().take(threshold as usize).enumerate() {
            let mut num = 1u8;
            let mut den = 1u8;

            for (k, share_k) in shares.iter().take(threshold as usize).enumerate() {
                if j == k {
                    continue;
                }
                num = gf_mul(num, share_k.x);
                den = gf_mul(den, gf_add(share_j.x, share_k.x));
            }

            let den_inv = gf_inv(den)?;
            let lagrange_at_zero = gf_mul(num, den_inv);
            acc = gf_add(acc, gf_mul(lagrange_at_zero, share_j.data[byte_idx]));
        }

        *result_byte = acc;
    }

    Ok(result)
}

// ---------- GF(256) helpers (AES polynomial 0x1B) ----------

#[inline]
fn gf_add(a: u8, b: u8) -> u8 {
    a ^ b
}

fn gf_mul(mut a: u8, mut b: u8) -> u8 {
    let mut p = 0u8;
    for _ in 0..8 {
        if b & 1 != 0 {
            p ^= a;
        }
        let hi_bit_set = a & 0x80;
        a <<= 1;
        if hi_bit_set != 0 {
            a ^= 0x1b;
        }
        b >>= 1;
    }
    p
}

fn gf_pow(mut base: u8, mut exp: u8) -> u8 {
    let mut res = 1u8;
    while exp > 0 {
        if exp & 1 != 0 {
            res = gf_mul(res, base);
        }
        base = gf_mul(base, base);
        exp >>= 1;
    }
    res
}

fn gf_inv(a: u8) -> Result<u8, DkgError> {
    if a == 0 {
        return Err(DkgError::NonInvertible);
    }
    // a^(254) in GF(256) gives multiplicative inverse
    Ok(gf_pow(a, 254))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_secret_sharing() {
        let secret = b"distributed-key-material";
        let shares = generate_shares(secret, 3, 5).expect("generate shares");

        // Reconstruct from first 3
        let recovered = reconstruct_secret(&shares[..3], 3).expect("reconstruct");
        assert_eq!(secret.to_vec(), recovered);

        // Reconstruct from a different subset
        let recovered = reconstruct_secret(&shares[1..4], 3).expect("reconstruct subset");
        assert_eq!(secret.to_vec(), recovered);
    }

    #[test]
    fn detects_duplicate_share_indices() {
        let secret = b"dup-check";
        let mut shares = generate_shares(secret, 2, 3).expect("generate shares");
        shares[1].x = shares[0].x;
        let err = reconstruct_secret(&shares[..2], 2).unwrap_err();
        assert_eq!(err, DkgError::DuplicateShare);
    }

    #[test]
    fn requires_enough_shares() {
        let secret = b"small";
        let shares = generate_shares(secret, 3, 3).expect("generate shares");
        let err = reconstruct_secret(&shares[..2], 3).unwrap_err();
        assert_eq!(err, DkgError::InsufficientShares);
    }
}
