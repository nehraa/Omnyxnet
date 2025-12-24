# Integration: DKG + WASM Encrypted I/O Tunnel + Dual DHT

## Goal
Wire DKG (Distributed Key Generation), WASM encrypted I/O tunnel, and Dual DHT so that:
- When a file is requested, a DKG key generation is triggered (simulated for now) and file shards are encrypted before being stored or served.
- When a compute task is sent, the compute sandbox communicates via an encrypted I/O tunnel (AEAD + padding) so the host sees only ciphertext.
- Dual DHT (local mDNS and global Kademlia) behaves correctly for discovery and content lookup; tests validate local vs global behavior.

## High-level flows

### File request / storage flow
1. Client requests file by `fileID`.
2. Node service calls `dkg.RequestFileKey(fileID)` which returns an ephemeral symmetric key (simulated by deterministic key derivation in tests).
3. File is split/sharded and each shard is encrypted with the file key (AES-GCM with random nonce) and padded to constant-size blocks.
4. Encrypted shards are `Provide`d to the global DHT and optionally cached locally (Local DHT/mDNS-assisted retrieval).
5. On retrieval, the requesting node obtains shards from DHT, uses DKG to reconstruct the key (simulated) and decrypts the shards.

### Compute task flow
1. Client submits compute job with input reference(s) (could be fileID or data blob).
2. Scheduler assigns job to a worker node; before sending data, a fresh ephemeral symmetric `job_key` is derived (via `dkg.GenerateEphemeralKey()` in simulation or requested as threshold key for secure sharing).
3. Worker launches WASM sandbox and the I/O tunnel is created: data passed through `IoTunnel::encrypt(job_key)` before reaching host-visible streams.
4. WASM receives decrypted input inside sandbox and produces output. Output is encrypted by the tunnel before leaving the sandbox.

## Components & Interfaces (simulated)

### Go: `go/pkg/crypto/dkg` (simulated API)
- `func RequestFileKey(ctx context.Context, fileID string) ([]byte, error)`
- `func GenerateEphemeralKey(ctx context.Context) ([]byte, error)`
- `func ReconstructKey(ctx context.Context, shares [][]byte) ([]byte, error)`

Implementation note: For now, simulated via deterministic HKDF (seeded by fileID and node IDs) so tests remain deterministic.

### Go: DHT helpers
- `func PutEncryptedShard(ctx context.Context, dht *dht.IpfsDHT, key cid.Cid, data []byte) error`
- `func GetEncryptedShard(ctx context.Context, dht *dht.IpfsDHT, key cid.Cid) ([]byte, error)`

Use libp2p `Provide` / `FindProviders` or `PutValue` / `GetValue` in tests. 

### Rust: `compute::io_tunnel` (prototype)
- `struct IoTunnel { aead: AesGcm128, nonce_len: usize }`
- `impl IoTunnel { fn encrypt(&self, plaintext: &[u8]) -> Vec<u8>; fn decrypt(&self, ciphertext: &[u8]) -> Result<Vec<u8>> }`
- Apply padding to fixed block size (e.g., 1024 bytes) to avoid length leaks in tests.

Integration: Add an option in `WasmSandbox::execute` (simulation mode) to use a supplied `IoTunnel` to wrap input/output.

## Tests

1. Dual DHT tests (Go):
   - Start two nodes in localMode=true and assert they discover via mDNS and don't create DHT.
   - Start nodes in WAN mode and assert `dht != nil` and `Bootstrap()` is called.
   - Put an encrypted blob to DHT on one node and get it from another (global path).

2. DKG tests (Go):
   - `RequestFileKey` returns consistent key for same fileID in simulation.
   - `GenerateEphemeralKey` returns unique keys per call.

3. WASM tunnel tests (Rust):
   - Unit test for `IoTunnel` AEAD encryption/decryption and padding.
   - Integration test: `WasmSandbox` in simulation mode uses `IoTunnel` to ensure the host-visible buffer is ciphertext (assert that decrypting with wrong key fails and likely ciphertext not equal plaintext).

4. End-to-end tests (integration):
   - Simulate: request file -> DKG -> encrypt shards -> store to DHT -> fetch from another node -> reconstruct key -> decrypt and verify.
   - Submit compute job referencing file -> scheduler sends encrypted input -> worker's `WasmSandbox` processes using `IoTunnel` -> verify host sees only ciphertext on I/O paths and decrypted output matches expected after tunnel decryption.

## Migration to production
- Replace simulated DKG with real threshold crypto library.
- Escrow keys into TEE or integrate with hardware enclave for true privacy.

## Next steps
- Implement unit tests for Dual DHT behavior in `go` and prototype `dkg` package (simulated).
- Add `IoTunnel` in Rust and unit tests.
- Wire end-to-end tests and CI job.


*Document created by automation to guide implementation and tests.*
