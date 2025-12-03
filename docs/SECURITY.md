# Security Guidelines

**Version:** 0.6.0-alpha  
**Last Updated:** 2025-12-03

## Table of Contents

1. [CES Encryption Key Management](#ces-encryption-key-management)
2. [Distributed Compute Security](#distributed-compute-security)
3. [Security Audit Results](#security-audit-results-v060)

---

## Distributed Compute Security

### WASM Sandbox Isolation

The distributed compute system executes untrusted code in a secure WASM sandbox:

#### Resource Limits

```rust
// Default resource limits
pub struct ResourceLimits {
    max_memory_bytes: u64,      // 256 MB default
    max_cpu_cycles: u64,        // 1 billion cycles
    max_execution_time_ms: u64, // 30 seconds
    max_stack_bytes: u64,       // 1 MB stack
}
```

#### Sandbox Guarantees

- **No Network Access:** WASM modules cannot make network calls
- **No File System Access:** WASM modules cannot read or write files
- **Memory Isolation:** Each task runs in isolated linear memory
- **CPU Metering:** Execution is interrupted when limits are exceeded
- **No System Calls:** WASI is restricted to pure computation

### Verification Modes

The system supports multiple verification modes for result integrity:

1. **Hash Verification:** SHA256 hash of results compared
2. **Merkle Tree Verification:** Cryptographic proof of data integrity
3. **Redundancy Verification:** Same task runs on multiple workers, results compared

### Trust Scoring

Workers build reputation through successful task completion:

```go
// Trust score updated after each task
if success {
    worker.trustScore = oldScore*0.9 + 0.1  // Increase trust
} else {
    worker.trustScore = oldScore*0.9 + 0.0  // Decrease trust
}
```

### Thread Safety

- **Python Job DSL:** Uses thread-local storage for concurrent job definitions
- **Go Manager:** Mutex protection for all shared state access
- **Rust Compute:** No shared mutable state between tasks

---

## Security Audit Results (v0.6.0)

### Fixed Issues

| Issue | Component | Resolution |
|-------|-----------|------------|
| Race condition in `delegateJob` | Go | Proper goroutine closure captures |
| Race condition in `executeChunk` | Go | Mutex lock for state access |
| Thread-unsafe Job builder | Python | Thread-local storage |
| Merkle proof padding logic | Rust | Track level sizes during build |

### Remaining Considerations

| Area | Status | Notes |
|------|--------|-------|
| WASM Sandbox | ⚠️ Simulation | Wasmtime integration pending |
| Worker Authentication | ⚠️ Future | No secure key exchange yet |
| Rate Limiting | ⚠️ Future | No per-worker rate limits |

---

## CES Encryption Key Management

## CES Encryption Key Management

The WGT system uses XChaCha20-Poly1305 encryption for data protection in the CES (Compression, Encryption, Sharding) pipeline. Proper key management is **critical** for production deployments.

### Overview

The system provides two approaches for key management:

1. **Explicit Key Management** (Recommended for Production)
2. **Environment Variable Key** (Suitable for Testing/Development)

### Production: Explicit Key Management

For production use, **always use explicit key management** via the `ces_new_with_key()` FFI function or `NewCESPipelineWithKey()` Go wrapper.

#### Rust FFI Example:
```rust
// Generate or retrieve your encryption key (32 bytes)
let encryption_key: [u8; 32] = /* your key management logic */;

// Create pipeline with explicit key
let pipeline = ces_new_with_key(compression_level, encryption_key.as_ptr());
```

#### Go Example:
```go
// Generate or retrieve your encryption key (32 bytes)
var encryptionKey [32]byte
// ... populate key from secure source ...

// Create pipeline with explicit key
pipeline := NewCESPipelineWithKey(compressionLevel, encryptionKey)
```

### Development/Testing: Environment Variable

For development and testing, you can use the `CES_ENCRYPTION_KEY` environment variable:

```bash
# Generate a random 32-byte key (hex-encoded, 64 characters)
export CES_ENCRYPTION_KEY=$(openssl rand -hex 32)

# Now ces_new() will use this key automatically
./pangea-go
```

**Important:** All processes that need to share encrypted data must use the same key.

### Key Requirements

- **Length:** Exactly 32 bytes (256 bits)
- **Format:** 
  - FFI: Raw bytes (`*const c_uchar`)
  - Environment Variable: Hex-encoded string (64 characters)
- **Randomness:** Use cryptographically secure random number generators
- **Storage:** Never hardcode keys in source code or commit them to version control

### Key Generation Examples

#### Generate Key (Command Line)
```bash
# Using OpenSSL
openssl rand -hex 32

# Using Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

#### Generate Key (Go)
```go
import "crypto/rand"

var key [32]byte
_, err := rand.Read(key[:])
if err != nil {
    panic(err)
}
```

#### Generate Key (Rust)
```rust
use rand::RngCore;

let mut key = [0u8; 32];
rand::thread_rng().fill_bytes(&mut key);
```

### Security Best Practices

1. **Never Hardcode Keys:** Do not hardcode encryption keys in source code
2. **Key Rotation:** Implement key rotation policies for long-term deployments
3. **Secure Storage:** Store keys in secure key management systems (e.g., HashiCorp Vault, AWS KMS)
4. **Access Control:** Limit access to encryption keys to authorized processes only
5. **Audit Logging:** Log key access and usage for security auditing
6. **Backup Keys:** Securely backup keys to prevent data loss
7. **Environment Separation:** Use different keys for development, staging, and production

### Multi-Tenant Scenarios

For multi-tenant deployments where different users/organizations need isolated data:

1. Use **separate encryption keys per tenant**
2. Create a new pipeline instance for each tenant with their specific key
3. Implement secure key derivation from a master secret if needed

```go
import (
    "crypto/sha256"
    "golang.org/x/crypto/hkdf"
    "io"
)

// Example: Per-tenant key derivation using HKDF (PROPER IMPLEMENTATION)
func getTenantKey(tenantID string, masterSecret []byte) ([32]byte, error) {
    var key [32]byte
    
    // Use HKDF (HMAC-based Key Derivation Function) - RFC 5869
    // This is the CORRECT way to derive keys
    info := []byte("ces-pipeline-" + tenantID)
    salt := []byte("wgt-ces-v1") // Use a unique salt per application/version
    
    kdf := hkdf.New(sha256.New, masterSecret, salt, info)
    if _, err := io.ReadFull(kdf, key[:]); err != nil {
        return key, err
    }
    
    return key, nil
}

// Create pipeline with tenant-specific key
tenantKey, err := getTenantKey(tenantID, masterSecret)
if err != nil {
    panic(err)
}
pipeline := NewCESPipelineWithKey(compressionLevel, tenantKey)
```

### Migration from Fixed Key

If you're migrating from the old fixed-key implementation:

1. **Generate new keys** for all environments
2. **Re-encrypt existing data** with new keys
3. **Update deployment configurations** to use new key management
4. **Verify** that all services can reconstruct data correctly

### Warnings and Limitations

⚠️ **WARNING:** The `ces_new()` function without explicit key management should **NOT** be used in production unless:
- The `CES_ENCRYPTION_KEY` environment variable is properly set
- All processes that need to share data use the same environment variable
- You understand the security implications

⚠️ **CRITICAL:** If `ces_new()` is called without `CES_ENCRYPTION_KEY` set:
- A random key is generated for that process
- Data cannot be reconstructed by other processes
- Data cannot be reconstructed after process restart
- This is **only suitable for ephemeral testing**

### Testing Your Key Management

Verify your key management implementation:

```go
// Test: Same key should allow reconstruction
key := [32]byte{ /* your key */ }

// Process data with first pipeline
pipeline1 := NewCESPipelineWithKey(3, key)
shards, err := pipeline1.Process(testData)
pipeline1.Close()

// Reconstruct with second pipeline using same key
pipeline2 := NewCESPipelineWithKey(3, key)
reconstructed, err := pipeline2.Reconstruct(shards, present)
pipeline2.Close()

// Verify data matches
if !bytes.Equal(testData, reconstructed) {
    panic("Key management failed: data mismatch")
}
```

### Support

For security concerns or questions about key management:
- Review this document thoroughly
- Check the inline documentation in `rust/src/ffi.rs`
- Open an issue with the `security` label (do not include sensitive information)

---

**Remember:** Proper encryption key management is not optional—it's essential for data security and integrity.
