use anyhow::{bail, Result};
use chacha20poly1305::aead::{Aead, KeyInit, OsRng};
use chacha20poly1305::{Key, XChaCha20Poly1305, XNonce};
use rand::RngCore;

const BLOCK_SIZE: usize = 1024;

/// IoTunnel provides AEAD encryption + fixed-block padding for WASM I/O
pub struct IoTunnel {
    aead: XChaCha20Poly1305,
}

impl IoTunnel {
    /// Create a new tunnel from a 32-byte key
    pub fn new(key: &[u8]) -> Result<Self> {
        if key.len() != 32 {
            bail!("key must be 32 bytes")
        }
        let aead = XChaCha20Poly1305::new(Key::from_slice(key));
        Ok(Self { aead })
    }

    /// Encrypt with nonce prefix + ciphertext. Pads to multiple of BLOCK_SIZE using length-prefix.
    pub fn encrypt(&self, plaintext: &[u8]) -> Result<Vec<u8>> {
        // Prepare buffer with length prefix
        let mut buf = Vec::new();
        let len = plaintext.len() as u64;
        buf.extend_from_slice(&len.to_le_bytes());
        buf.extend_from_slice(plaintext);
        // Add zero padding to next block
        let pad_len = (BLOCK_SIZE - (buf.len() % BLOCK_SIZE)) % BLOCK_SIZE;
        buf.extend(std::iter::repeat_n(0u8, pad_len));

        // Generate nonce
        let mut nonce_bytes = [0u8; 24];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = XNonce::from_slice(&nonce_bytes);

        let ciphertext = self.aead.encrypt(nonce, buf.as_ref())?;

        // Result = nonce || ciphertext
        let mut out = Vec::with_capacity(nonce_bytes.len() + ciphertext.len());
        out.extend_from_slice(&nonce_bytes);
        out.extend_from_slice(&ciphertext);
        Ok(out)
    }

    /// Decrypt data produced by encrypt()
    pub fn decrypt(&self, ciphertext_with_nonce: &[u8]) -> Result<Vec<u8>> {
        if ciphertext_with_nonce.len() < 24 {
            bail!("ciphertext too short")
        }
        let (nonce_bytes, ciphertext) = ciphertext_with_nonce.split_at(24);
        let nonce = XNonce::from_slice(nonce_bytes);
        let plaintext = self.aead.decrypt(nonce, ciphertext.as_ref())?;
        // Remove padding and read length prefix
        if plaintext.len() < 8 {
            bail!("plaintext too small for length prefix")
        }
        let mut len_bytes = [0u8; 8];
        len_bytes.copy_from_slice(&plaintext[..8]);
        let len = u64::from_le_bytes(len_bytes) as usize;
        if plaintext.len() < 8 + len {
            bail!("invalid length in plaintext")
        }
        let result = plaintext[8..8 + len].to_vec();
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tunnel_roundtrip() {
        let mut key = [0u8; 32];
        rand::thread_rng().fill_bytes(&mut key);

        let tunnel = IoTunnel::new(&key).expect("new tunnel");
        let plain = b"hello secret data";

        let c = tunnel.encrypt(plain).expect("encrypt");
        assert!(c != plain);

        let p = tunnel.decrypt(&c).expect("decrypt");
        assert_eq!(p.as_slice(), plain);
    }
}
