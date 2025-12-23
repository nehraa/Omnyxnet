# IMPLEMENTATION_GUIDE.md

**Version**: 1.0  
**Date**: December 23, 2025  
**Status**: Technical specification for engineers

---

## Tech Stack

### Core Languages
- **Rust**: Core networking, encryption, storage
- **Go**: Node orchestration, libp2p integration, DCDN
- **Python**: CLI management, AI/ML training, testing
- **TypeScript/React**: Web UI (future v1.0+)
- **Swift/Kotlin**: Mobile apps (iOS/Android)

### Key Libraries

**Cryptography**
- `rustls` (TLS handshake)
- `aes-gcm` (AES-256-GCM encryption)
- `ed25519-dalek` (Ed25519 signatures)
- `x25519-dalek` (Key agreement)
- `aws-lc-rs` (PQ crypto, v0.7+)

**Networking**
- `libp2p` (peer-to-peer)
- `tokio` (async runtime)
- `quinn` (QUIC transport)
- `capnproto` (RPC serialization)
- `tor-client` (Tor integration)

**Storage**
- `rocksdb` (local node storage)
- `parking_lot` (lock-free concurrent structures)
- Custom DHT (Kademlia variant)

**ML/AI**
- `tch-rs` (PyTorch bindings)
- `ndarray` (numerical computing)
- `serde` (serialization)

---

## Milestone Breakdown

### v0.6 MVP (Weeks 1-12)

#### Week 1-2: Project Setup
- [ ] Repository structure (Rust workspace, Python/Go modules)
- [ ] CI/CD pipeline (GitHub Actions, cargo test, clippy)
- [ ] Dependency management (Cargo.toml SemVer ranges)
- [ ] Development environment (Docker Compose for local testing)

#### Week 3-6: Smartwatch Integration
- [ ] iOS HealthKit adapter (vitals streaming)
- [ ] Android Health Connect adapter (vitals streaming)
- [ ] Local ML inference (mood model)
- [ ] Gesture recognition (gyroscope → commands)
- [ ] Battery optimization (<2% drain/hour)

**Deliverable**: iOS + Android beta with smartwatch vitals + mood rec

#### Week 4-6: Core P2P Networking
- [ ] libp2p setup (Noise handshake, mDNS discovery)
- [ ] Ed25519 keypair generation (persistent node identity)
- [ ] Connection pooling + keep-alive
- [ ] Error handling + retry logic
- [ ] Basic logging/metrics

**Deliverable**: Two nodes can connect and exchange messages

#### Week 7-10: Communication Features
- [ ] VOIP: Opus codec, peer-routed, audio streaming
- [ ] Chat: Message encryption (Double Ratchet), offline queue, receipts
- [ ] Tor integration: SOCKS5 proxy toggle, IP verification
- [ ] End-to-end encryption: AES-256-GCM keys derived + stored locally
- [ ] Message persistence (local SQLite, not cloud)

**Deliverable**: VOIP + chat fully functional, Tor optional

#### Week 8-12: File Storage + DHT
- [ ] Dual DHT implementation
  - Local DHT (regional cache, TTL 30 days)
  - Global DHT (network truth, TTL 2 months)
  - Parallel query threads
- [ ] CES Pipeline
  - Compress: `zstd` (target 2x ratio)
  - Encrypt: AES-256-GCM (client-side)
  - Shard: Reed-Solomon 8+2 (via `reed-solomon` crate)
- [ ] BitTorrent-style caching (auto-seed on download)
- [ ] Bootstrap nodes (2-3 VPS, health checks)
- [ ] Centralized fallback (archive server, last resort)

**Deliverable**: Files stored/retrieved with DHT + caching, MVP complete

#### Week 10-12: Testing + Polish
- [ ] Unit tests (90%+ coverage)
- [ ] Integration tests (2-node local network)
- [ ] E2E tests (real devices: iPhone + Android + desktop)
- [ ] Performance benchmarks (latency, throughput)
- [ ] Security audit (internal)
- [ ] UI/UX polish (first-run wizard, onboarding)

**Deliverable**: MVP ready for beta launch (100 testers)

---

### v0.7 Security (Weeks 13-16)

#### Week 13-14: Cargo.toml Audit
- [ ] Review all dependencies (`cargo tree`)
- [ ] Convert pinned `=x.y.z` to ranges `^x.y`
- [ ] Document any pins in `CARGO_PINS.md`
- [ ] Add CI job: weekly freshness tests
- [ ] Run `cargo audit` in CI

**Deliverable**: SemVer-compliant Cargo.toml + CI validation

#### Week 14-15: Node Health ML
- [ ] Implement health score formula
  ```
  score = (uptime_pct × 0.4) + (latency_inv × 0.3) + (availability × 0.3)
  ```
- [ ] DHT ping aggregation (every 5 min)
- [ ] ML inference (on receptor nodes)
- [ ] Auto-blacklist (scores <30)
- [ ] Telemetry (no PII)

**Deliverable**: Node health scoring in real-time

#### Week 15-16: Post-Quantum Crypto
- [ ] Evaluate aws-lc-rs + rustls-post-quantum
- [ ] Implement X25519 + ML-KEM hybrid
- [ ] Update handshake (Noise protocol)
- [ ] Test latency (<200ms target)
- [ ] Security audit

**Deliverable**: PQ crypto hybrid ready for production

---

### v0.8 Storage + Legal (Weeks 17-22)

#### Week 17-18: DKG (Distributed Key Generation)
- [ ] Implement threshold cryptography (t-of-n)
- [ ] Key share generation + distribution
- [ ] Key reconstruction (any t shares)
- [ ] Key rotation logic

**Deliverable**: DKG ready for shared data (post-MVP)

#### Week 18-19: View-Only Mode
- [ ] Node mode selection (Full vs View-Only)
- [ ] Restricted features (comms only for view-only)
- [ ] Seed participation (lightweight)
- [ ] Legal clarity in UI

**Deliverable**: Two-tier node mode with legal disclaimers

#### Week 19-20: IP Rotation + Certificate Proof
- [ ] Node IP change detection
- [ ] Proof generation: `(old_ip, new_ip, sig, cert)`
- [ ] Peer verification logic
- [ ] Seamless reconnection (<2s downtime)

**Deliverable**: IP rotation working transparently

#### Week 20-22: Cold Data Archiving + Legal TOS
- [ ] Local DHT 30-day cleanup
- [ ] Global DHT 2-month TTL
- [ ] Archive fallback (centralized)
- [ ] Legal TOS (README + first-run modal)
- [ ] Operator liability table
- [ ] Multi-jurisdiction notes

**Deliverable**: Legal framework + cold data archiving

---

### v0.9 Distributed Compute (Weeks 23-30)

#### Week 23-24: WASM + Encrypted I/O Tunnel
- [ ] WASM sandbox setup (wasmer or wasmtime)
- [ ] Separate decrypt key per job
- [ ] Encrypted I/O tunnel (TLS + padding)
- [ ] Host isolation testing

**Deliverable**: WASM with encrypted tunnel, host can't see plaintext

#### Week 25-26: Job Scheduler
- [ ] Job submission RPC
- [ ] Health-ranked node selection
- [ ] Retry + exponential backoff
- [ ] Queue with ETA + capacity feedback

**Deliverable**: Job scheduler fully functional

#### Week 27-28: Re-replication Automation
- [ ] Shard availability monitoring
- [ ] Trigger at 20% loss
- [ ] Auto-select healthy targets
- [ ] Encrypted shard copy

**Deliverable**: Re-replication transparent to user

#### Week 29-30: Testing + Benchmarks
- [ ] 50-node cluster simulation
- [ ] Fault injection (25% failure)
- [ ] Performance benchmarks
- [ ] Load testing (job queue saturation)

**Deliverable**: v0.9 ready, compute MVP complete

---

### v1.0 Full Suite (Weeks 31-40)

#### Week 31-35: Decentralized YouTube-Like
- [ ] Content discovery DHT
- [ ] Peer-routed video streams
- [ ] VP9/AV1 codecs
- [ ] Creator metadata (name, bio, avatar)

**Deliverable**: YouTube-like prototype on 50 nodes

#### Week 35-37: Decentralized Email
- [ ] Encrypted mailboxes
- [ ] Address book (DHT)
- [ ] Spam filtering (reputation-based)
- [ ] IMAP compatibility layer

**Deliverable**: Email MVP ready

#### Week 37-39: Office Suite
- [ ] CRDT-based docs
- [ ] Real-time multiplayer sheets
- [ ] Export (ODT, PDF)
- [ ] Import (Google Docs)

**Deliverable**: Collaborative docs working

#### Week 39-40: Integration + SLAs
- [ ] 50+ node integration tests
- [ ] Enterprise SLAs (uptime guarantees)
- [ ] Audit logs + compliance
- [ ] Full security audit

**Deliverable**: v1.0 ready, all features stable

---

## Code Organization

```
pangea-net/
├── rust/
│   ├── src/
│   │   ├── crypto/         (AES-GCM, Ed25519, X25519)
│   │   ├── dht/            (Kademlia DHT + local DHT)
│   │   ├── storage/        (RocksDB, shard management)
│   │   ├── messaging/      (Noise protocol, Double Ratchet)
│   │   ├── dcdn/           (QUIC, Reed-Solomon FEC)
│   │   ├── wasm/           (Sandbox, encrypted tunnel)
│   │   └── main.rs         (Node entry point)
│   ├── Cargo.toml
│   └── tests/
├── go/
│   ├── cmd/
│   │   └── pangea-node/    (libp2p wrapper, bootstrap)
│   ├── pkg/
│   │   ├── rpc/            (gRPC/Capn Proto)
│   │   └── health/         (Node health scoring)
│   └── go.mod
├── python/
│   ├── src/
│   │   ├── cli/            (Command-line interface)
│   │   ├── ml/             (Mood recommendation, health scoring)
│   │   └── test/           (Integration tests)
│   └── requirements.txt
├── mobile/
│   ├── ios/                (Swift + HealthKit)
│   ├── android/            (Kotlin + Health Connect)
│   └── shared/             (Shared logic)
├── docs/
│   ├── ROADMAP.md
│   ├── PRODUCT_VISION.md
│   ├── THREAT_MODEL.md
│   ├── LEGAL.md
│   └── API.md
├── .github/
│   └── workflows/
│       ├── ci.yml          (Tests + clippy + audit)
│       ├── security.yml    (CodeQL, SAST)
│       └── deploy.yml      (Release pipeline)
└── docker-compose.yml      (Local dev environment)
```

---

## Testing Strategy

### Unit Tests (90%+ Coverage)
```
cargo test --lib
python -m pytest src/
```

### Integration Tests
```
docker-compose up -d
# 2-node local network
# Test DHT, messaging, file sharing
```

### E2E Tests
```
# Real devices: iPhone, Android, macOS
# Smartwatch integration
# VOIP/chat end-to-end
# File storage round-trip
```

### Load Testing
```
# 50-node simulation
# 100 concurrent jobs
# 25% node churn (offline/online cycling)
# Measure latency, throughput, availability
```

---

## Security Checklist

- [ ] All crypto via audited libraries (rustls, aes-gcm, ed25519)
- [ ] No hardcoded secrets (keys generated, stored locally)
- [ ] No PII in logs (anonymize IPs, message content)
- [ ] Input validation on all RPCs
- [ ] Constant-time comparisons for crypto
- [ ] No buffer overflows (Rust memory safety)
- [ ] HTTPS/TLS for all transport
- [ ] Regular dependency updates (`cargo update` weekly)
- [ ] Security audit pre-launch (v0.6)
- [ ] Bug bounty program (v1.0+)

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| VOIP latency (LAN) | <150ms | E2E |
| VOIP latency (WAN) | <300ms | May include Tor |
| Chat message latency | <500ms | E2E, ack receipt |
| File upload speed | >10 MB/s | Local network |
| DHT query (local) | <10ms | 95th percentile |
| DHT query (global) | <100ms | 95th percentile |
| Node startup | <5s | From cold start |
| Memory per node | <500MB | Typical usage |
| CPU utilization | <20% | Idle + background sync |
| Disk I/O | <100 IOPS | Average |

---

## Deployment

### Development
```bash
cd rust
cargo build --debug
cargo run -- --config dev.toml
```

### Testing
```bash
docker-compose up -d
# Runs 3 nodes locally
cargo test --all
python -m pytest
```

### Beta Release
```bash
cargo build --release
# Push Docker image to registry
# Deploy 2-3 bootstrap nodes on AWS/DO
```

### Production (v1.0+)
```bash
# Kubernetes deployment
# HA setup (3+ nodes)
# Monitoring + alerting
# Auto-scaling based on network load
```

---

## Monitoring & Telemetry

**What We Track** (Privacy-first):
- Node uptime (per node ID, anonymized)
- DHT query latency (percentiles)
- Message throughput (counts only, no content)
- Job completion rates (stats only)

**What We Don't Track**:
- User identities
- Message content
- File contents
- IP addresses (except your own node)

**Tools**:
- Prometheus (metrics scraping)
- Grafana (dashboards)
- ELK stack (logs, no PII)
- Jaeger (distributed tracing)

---

## Release Process

1. **Git workflow**:
   - Main branch: stable releases
   - Dev branch: active development
   - Feature branches: per PR

2. **Version tagging**: `v0.6.0`, `v0.6.1`, etc.

3. **Changelog**: Keep CHANGELOG.md updated

4. **GitHub Releases**: Draft release notes + binaries

5. **Mobile**: TestFlight (iOS), Play Store (Android)

6. **Docker Hub**: Publish `pangea-net:v0.6.0`

---

**Owner**: Pangea Net Development Team  
**Last Updated**: December 23, 2025
