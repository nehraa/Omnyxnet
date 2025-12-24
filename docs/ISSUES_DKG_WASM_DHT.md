# Follow-up Issues: DKG + WASM Encrypted I/O Tunnel + Dual DHT

These are follow-up tasks to move from the current simulated prototype to production ready components.

1. Replace simulated DKG with production threshold crypto
   - Integrate and evaluate libraries (e.g., `dfinity/dkg`, `libthreshold`)
   - Add tests for share distribution, key rotation, and recovery
   - Security review and audit (third-party)

2. Host-proof WASM secrets (TEE integration)
   - Evaluate SGX/SEV or remote attestation approaches
   - Design key escrow and attestation flows
   - Add CI tests for attestation (if hardware/emulator available)

3. Harden IoTunnel
   - Add replay protection, per-job nonces, explicit associated data
   - Implement constant-time operations and side-channel mitigations
   - Add fuzz tests and KATs (known-answer tests)

4. Full network shard retrieval via DHT
   - Implement `Provide` + `FetchShard` for full host data exchange
   - Add content-based sharding CID scheme and discovery tests
   - Add end-to-end tests using docker-compose to run multi-node mesh

5. Documentation & Compliance
   - Update `Req&design` docs with threat model and limitation notes
   - Add deployment checklist (key management, TEE requirements)

If you want, I can open GitHub issues for these and create milestone tracking.
