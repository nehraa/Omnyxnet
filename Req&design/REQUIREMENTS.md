# Pangea Net - Complete Requirements Specification

**Version**: 1.0  
**Date**: December 23, 2025  
**Status**: Master requirements document extracted from all design docs

---

## Table of Contents
1. [MVP v0.6 Requirements](#mvp-v06-requirements)
2. [v0.7 Security Requirements](#v07-security-requirements)
3. [v0.8 Storage & Legal Requirements](#v08-storage--legal-requirements)
4. [v0.9 Distributed Compute Requirements](#v09-distributed-compute-requirements)
5. [v1.0 Full Suite Requirements](#v10-full-suite-requirements)
6. [Cross-Cutting Requirements](#cross-cutting-requirements)

---

## MVP v0.6 Requirements

### Phase 1A: Smartwatch & Accessibility (Weeks 1-6)

#### REQ-001: Mood Recommendation System
- **Description**: ML-driven mood recommendations based on smartwatch health vitals
- **Must Have**:
  - Integrate iOS HealthKit API for vitals streaming (heart rate, sleep, steps)
  - Integrate Android Health Connect API for vitals streaming
  - Local ML inference (mood model runs on device, not cloud)
  - Privacy-preserving fine-tuning (user data stays local)
  - 95%+ accuracy on validation dataset
  - 500ms inference latency target
  - Works offline (cache vitals locally)
  
#### REQ-002: Gesture Recognition
- **Description**: Wrist movement control via smartwatch gyroscope
- **Must Have**:
  - Map gyroscope data to commands (click, swipe, scroll, hold)
  - 90%+ gesture accuracy
  - Zero false positives in idle state
  - Accessibility mode for disabled users
  - Works with Apple Watch, Garmin, Fitbit

#### REQ-003: Smartwatch Integration
- **Description**: Real-time vitals collection and battery optimization
- **Must Have**:
  - <2% battery drain/hour in background
  - 100ms streaming latency for vitals
  - Works offline with local caching
  - Support iOS + Android simultaneously

#### REQ-004: Platform Support
- **Must Have**:
  - iOS TestFlight beta ready
  - Android Play Store internal beta ready
  - Desktop app (macOS/Linux/Windows)

---

### Phase 1B: Core P2P Networking (Weeks 4-6)

#### REQ-005: Node Identity & Discovery
- **Description**: Establish persistent node identities and peer discovery
- **Must Have**:
  - Ed25519 keypair generation (persistent per node)
  - libp2p setup with Noise handshake
  - mDNS peer discovery (local network)
  - Connection pooling + keep-alive heartbeat
  - Basic logging and metrics collection

#### REQ-006: Network Connectivity
- **Must Have**:
  - Two nodes can connect and exchange messages
  - Error handling + retry logic (exponential backoff)
  - Connection timeout handling
  - Graceful degradation on network loss

---

### Phase 1C: Communication Features (Weeks 7-10)

#### REQ-007: VOIP Implementation
- **Description**: Peer-to-peer encrypted voice calls
- **Must Have**:
  - Opus codec, 48kHz encoding
  - Peer-routed via libp2p (no central server)
  - SOCKS5 Tor toggle (optional anonymity)
  - 150ms E2E latency on LAN
  - 300ms E2E latency on WAN (with Tor)
  - <1% call drop rate
  - Quality targets: 16kHz minimum, full duplex

#### REQ-008: Chat & Messaging
- **Description**: End-to-end encrypted instant messaging
- **Must Have**:
  - AES-256-GCM encryption (E2E)
  - Forward secrecy (Double Ratchet or similar)
  - Offline message queue (auto-sync on reconnect)
  - Message delivery receipts
  - Typing indicators
  - Zero plaintext on disk

#### REQ-009: Tor Integration
- **Description**: Optional anonymity layer via Tor SOCKS5
- **Must Have**:
  - SOCKS5 proxy toggle in UI
  - IP address verification (display real vs Tor exit node IP)
  - 300ms latency acceptable with Tor
  - Works with VOIP + chat simultaneously

---

### Phase 1D: File Storage & DHT (Weeks 8-12)

#### REQ-010: Dual DHT Architecture (✅ implemented)
- **Description**: Local + global distributed hash table for file discovery
- **Must Have**:
  - **Local DHT**: Regional peer cache
    - <10ms query latency (95th percentile)
    - 30-day TTL post-access
    - 99.9% uptime
  - **Global DHT**: Network-wide source of truth
    - <100ms query latency (95th percentile)
    - 2-month TTL post-access
    - 99.9% uptime
  - Parallel query threads (both run concurrently, return first valid result)

#### REQ-011: CES Pipeline (Compress-Encrypt-Shard)
- **Description**: Multi-layer file security and distribution
- **Compression**:
  - Zstd or Brotli compression
  - Target 2x compression ratio
  - Reduce data size before encryption
- **Encryption**:
  - AES-256-GCM client-side
  - Key derived from user password (Argon2-KDF)
  - Encryption happens before sharding
- **Sharding**:
  - Reed-Solomon 8+2 FEC (8 data blocks, 2 parity)
  - Distribute shards across network nodes
  - Nodes see only encrypted shards (zero knowledge)
  - 100% recovery with any 8 of 10 shards

#### REQ-012: BitTorrent-Style Caching
- **Description**: Distributed caching with automatic seeding
- **Must Have**:
  - Auto-seed when user downloads file
  - 80% cache hit rate target for popular files
  - Health-based eviction (deprioritize unhealthy seeds)
  - Auto-cleanup on TTL expiry

#### REQ-013: Bootstrap Nodes
- **Description**: Maintainer-hosted nodes for network bootstrapping
- **Must Have**:
  - 2-3 VPS nodes (AWS/DigitalOcean, ~$15/mo total)
  - Pure bootstrap function (no user data storage)
  - Health check endpoints
  - 99.99% uptime SLA
  - 50ms peer discovery latency
  - ML monitors when to scale up/disable

#### REQ-014: Centralized Fallback
- **Description**: Last-resort archive for orphaned shards
- **Must Have**:
  - Archive server (temporary, phased out post-v0.8)
  - Handles extreme failure (20%+ shards offline)
  - Encrypted shards only
  - No plaintext access

---

### Phase 1E: Testing & Polish (Weeks 10-12)

#### REQ-015: Unit Testing
- **Must Have**:
  - 90%+ code coverage
  - Test CES pipeline functionality
  - Test health scoring logic
  - Test DHT queries
  - `cargo test --lib` passes

#### REQ-016: Integration Testing
- **Must Have**:
  - 2-node local network via Docker Compose
  - Test DHT, messaging, file sharing end-to-end
  - Test VOIP audio quality
  - Test Tor toggle functionality

#### REQ-017: E2E Testing
- **Must Have**:
  - Real devices (iPhone, Android, macOS)
  - Smartwatch integration tests
  - VOIP + chat end-to-end
  - File storage round-trip (upload → download → verify)

#### REQ-018: Performance Benchmarking
- **Must Have**:
  - Latency measurements (VOIP, chat, DHT queries)
  - Throughput (file upload/download speed)
  - CPU/memory profiling
  - Battery drain monitoring

#### REQ-019: Security Audit
- **Must Have**:
  - Internal review of crypto implementation
  - Peer review of CES pipeline
  - No hardcoded secrets
  - No obvious vulnerabilities

#### REQ-020: UI/UX Polish
- **Must Have**:
  - First-run wizard (onboarding)
  - Settings panel (Tor toggle, storage mode)
  - Accessibility features (high contrast, large text)
  - Error messages (clear, actionable)

---

## v0.7 Security Requirements

### Cargo.toml & Dependency Management (Weeks 13-14)

#### REQ-021: SemVer Compliance
- **Must Have**:
  - Replace pinned versions `=x.y.z` with ranges `^x.y`
  - Create `CARGO_PINS.md` documenting any exceptions with justification
  - Add CI job: `cargo tree` (dependency graph)
  - Add CI job: `cargo update` (test with latest compatible)
  - Add CI job: `cargo audit` (security checks)
  - Weekly freshness test runs

#### REQ-022: Dependency Audit
- **Must Have**:
  - Zero unjustified pins
  - All dependencies from crates.io or verified sources
  - No local forks without documented reason

---

### Node Health ML (Weeks 14-15)

#### REQ-023: Node Health Scoring
- **Description**: ML-driven reliability assessment
- **Must Have**:
  - Health score formula: `(uptime% × 0.4) + (latency_inverse × 0.3) + (availability% × 0.3)`
  - Score buckets:
    - 0-30: Dead/unreliable (avoid)
    - 30-70: Degraded (use if necessary)
    - 70-100: Healthy (preferred)
  - Update every 5 minutes via DHT pings
  - Auto-blacklist nodes with score <30
  - No PII in telemetry

---

### Post-Quantum Crypto (Weeks 15-16)

#### REQ-024: PQ Crypto Hybrid
- **Description**: Quantum-resistant cryptography
- **Must Have**:
  - Library: aws-lc-rs with rustls-post-quantum
  - Algorithm: X25519 + ML-KEM hybrid
  - Handshake latency: <200ms
  - Security audit required before production
  - Backward compatibility with v0.6

---

## v0.8 Storage & Legal Requirements

### DKG & Shared Data (Weeks 17-18)

#### REQ-025: Distributed Key Generation (DKG) (✅ implemented)
- **Description**: Threshold cryptography for shared encryption
- **Must Have**:
  - Implement t-of-n threshold scheme
  - Key share generation + distribution
  - Key reconstruction (any t holders)
  - Key rotation support
  - <1% collusion risk
  - <1s key generation latency

---

### View-Only Mode (Weeks 18-19)

#### REQ-026: Dual Node Modes
- **Description**: Two operational modes for different threat models
- **Full Node**:
  - Communications + file storage + compute
  - Full feature set
  - Storage responsibility
- **View-Only Node**:
  - Communications only
  - Can participate as seed (lightweight)
  - Zero storage liability
  - Reduced features (essential only)
- **Must Have**:
  - Clear UI toggle
  - Legal disclaimer at mode selection

---

### IP Rotation & Certificate Proof (Weeks 19-20)

#### REQ-027: Seamless IP Rotation
- **Description**: Persistent identity across IP changes
- **Must Have**:
  - Detect node IP changes
  - Generate proof: `(old_ip, new_ip, signature, certificate)`
  - Peer verification logic
  - Update routing tables
  - <2s downtime on IP change
  - 100% reconnection success rate
  - Prevents SYBIL identity reuse

---

### Cold Data Archiving (Weeks 20-22)

#### REQ-028: Adaptive TTL & Archive
- **Description**: Multi-tier data retention
- **Local DHT**:
  - 30-day cleanup post-access
  - User offered to delete seed
- **Global DHT**:
  - 2-month TTL post-access
  - Flag as "cold data"
- **Archive Fallback**:
  - Centralized copy if no active holders
  - Temp storage until replication possible
  - ML triggers re-replication at 20% shard loss

---

### Legal TOS & Disclosures (Weeks 20-22)

#### REQ-029: Legal Framework
- **Must Have**:
  - README section explaining legal model
  - UI first-run warning (storage enables encryption)
  - Operator liability table (uploader vs seed vs receptor)
  - Multi-jurisdiction compliance notes (US, EU, UK, India, Russia, China)
  - Contact: team@pangea.net for questions
  - TOS signed by node operators

#### REQ-030: Operator Liability Clarity
- **Must Have**:
  - Document that encrypted shards = zero knowledge
  - Document that node operators see no plaintext
  - Document that uploaders are responsible for legality
  - Example: "Seed participants = encrypted relay, zero liability"

---

## v0.9 Distributed Compute Requirements

### WASM & Encrypted I/O Tunnel (Weeks 23-24)

#### REQ-031: WASM Sandbox with Data Privacy (✅ implemented)
- **Description**: Isolated computation with encrypted host interaction
- **Must Have**:
  - WASM sandbox setup (wasmer or wasmtime)
  - Separate decryption key per job (different from storage key)
  - Encrypted I/O tunnel (TLS + padding)
  - One-time ephemeral keys per computation
  - Host cannot access plaintext (only ciphertext)
  - Padding defeats timing attacks
  - <5% performance overhead

#### REQ-032: Host Isolation Testing
- **Must Have**:
  - Verify host OS cannot read plaintext
  - Verify keys not accessible to host process
  - Verify I/O remains encrypted end-to-end

---

### Job Scheduler (Weeks 25-26)

#### REQ-033: Job Submission & Scheduling
- **Must Have**:
  - Job submission RPC
  - Health-ranked node selection (prefer score >80)
  - Exponential backoff retry (3 attempts)
  - Queue with ETA and position feedback
  - 99%+ job completion rate
  - 30s average queue time
  - Job timeout handling

---

### Re-replication Automation (Weeks 27-28)

#### REQ-034: Automatic Shard Recovery
- **Description**: Proactive data replication on failure
- **Must Have**:
  - Shard availability monitoring (real-time)
  - Trigger at 20% shard loss
  - Auto-select healthy target nodes (health-scored ranked)
  - Encrypted shard copy (no decryption on nodes)
  - 10s trigger latency
  - Zero user intervention

#### REQ-035: Job Queue Backpressure
- **Must Have**:
  - UI feedback: "Network busy, queued at position 5, ~30s wait"
  - Graceful degradation when 80%+ capacity
  - Capacity feedback to users
  - No silent failures

---

### Testing & Benchmarks (Weeks 29-30)

#### REQ-036: 50-Node Cluster Tests
- **Must Have**:
  - Simulate 50 nodes locally
  - Fault injection (25% node failure)
  - Performance benchmarks (latency, throughput)
  - Load testing (job queue saturation)
  - All features functional on 50-node network

---

## v1.0 Full Suite Requirements

### Decentralized YouTube-Like (Weeks 31-35)

#### REQ-037: Decentralized Video Platform
- **Must Have**:
  - Content discovery via DHT
  - Peer-routed video streams (no CDN)
  - VP9/AV1 codec support
  - HD (1080p @ 30fps) target
  - 2s seek latency
  - Creator metadata (name, bio, avatar)
  - Comments + ratings system

---

### Decentralized Email (Weeks 35-37)

#### REQ-038: Email System
- **Must Have**:
  - Encrypted mailboxes (AES-256-GCM)
  - Decentralized address book (DHT)
  - Spam filtering (reputation-based)
  - Offline sync support
  - IMAP compatibility layer (optional)

---

### Office Suite (Weeks 37-39)

#### REQ-039: Collaborative Documents
- **Must Have**:
  - CRDT-based collaborative docs (conflict-free)
  - Real-time multiplayer sheets
  - 100ms cursor/edit sync latency
  - Export (ODT, PDF)
  - Import (Google Docs)

---

### Enterprise SLAs (Weeks 39-40)

#### REQ-040: Enterprise Features
- **Must Have**:
  - Uptime guarantees (99.9%)
  - Priority support tier
  - Custom job scheduling
  - Audit logs + compliance reports

#### REQ-041: Full Integration Tests
- **Must Have**:
  - 50+ node cluster simulation
  - All features end-to-end
  - Fault injection (25% node failure)
  - Performance benchmarks
  - Security audit (third-party)

---

## Cross-Cutting Requirements

### Performance Requirements

#### REQ-042: Latency Targets
| Metric | Target | Notes |
|--------|--------|-------|
| VOIP (LAN) | 150ms | E2E |
| VOIP (WAN+Tor) | 300ms | May include Tor delay |
| Chat message | 500ms | E2E + receipt |
| File upload | 10 MB/s | Local network |
| DHT query (local) | 10ms | 95th percentile |
| DHT query (global) | 100ms | 95th percentile |
| Node startup | 5s | Cold start |

#### REQ-043: Resource Targets
| Metric | Target | Notes |
|--------|--------|-------|
| Memory/node | 500MB | Typical usage |
| CPU (idle) | 20% | Background sync |
| Disk I/O | 100 IOPS | Average |
| Storage/node | 100GB | Configurable |

#### REQ-044: Availability Targets
| Metric | Target | Notes |
|--------|--------|-------|
| Node uptime | 85%+ | Graceful at 70% |
| File availability | 99.99% | 8+2 FEC + re-rep |
| Bootstrap nodes | 99.99% | Pure bootstrap |
| DHT uptime | 99.9% | Both local + global |

---

### Security Requirements

#### REQ-045: Cryptography
- **Must Have**:
  - AES-256-GCM for all file encryption (client-side)
  - AES-256-GCM for all communication encryption (E2E)
  - Ed25519 for node signatures
  - X25519 for key agreement
  - Double Ratchet for forward secrecy (chat)
  - All via audited libraries (rustls, aes-gcm, ed25519-dalek)

#### REQ-046: Key Management
- **Must Have**:
  - Keys generated on user device
  - No hardcoded secrets
  - Private data: uploader holds keys (Argon2-KDF)
  - Shared data: DKG (post-v0.8)
  - Keys never transmitted in plaintext

#### REQ-047: Input Validation
- **Must Have**:
  - Validate all RPC inputs
  - Validate file sizes (prevent DoS)
  - Validate message formats
  - Constant-time comparisons for crypto operations

#### REQ-048: Memory Safety
- **Must Have**:
  - No buffer overflows (Rust memory safety)
  - No use-after-free (enforced by compiler)
  - Secure random generation (no weak RNG)

#### REQ-049: Transport Security
- **Must Have**:
  - TLS/QUIC for all transport
  - Perfect forward secrecy (session keys)
  - Certificate pinning where applicable

#### REQ-050: Dependency Security
- **Must Have**:
  - Weekly `cargo audit` runs
  - Regular dependency updates
  - SemVer ranges (not pinned) except where justified
  - No unreviewed third-party code

---

### Testing Requirements

#### REQ-051: Unit Testing
- **Must Have**:
  - 90%+ code coverage
  - All crypto primitives tested
  - All data structures tested
  - Error handling tested

#### REQ-052: Integration Testing
- **Must Have**:
  - 2-node local network
  - DHT queries functional
  - File operations end-to-end
  - Messaging functional

#### REQ-053: E2E Testing
- **Must Have**:
  - Real devices (iOS, Android, desktop)
  - Smartwatch integration
  - VOIP quality tests
  - File storage round-trip

#### REQ-054: Load Testing
- **Must Have**:
  - 50+ node clusters
  - 100 concurrent jobs
  - 25% node churn (up/down cycling)
  - Latency, throughput, availability measured

#### REQ-055: Security Testing
- **Must Have**:
  - Fuzzing of crypto inputs
  - WASM sandbox escape attempts
  - Network fuzzing
  - Third-party audit (v0.7+)

---

### Documentation Requirements

#### REQ-056: API Documentation
- **Must Have**:
  - RPC endpoint specs
  - Message format specs
  - DHT protocol docs
  - Security properties documented

#### REQ-057: User Documentation
- **Must Have**:
  - Getting started guide
  - UI walkthroughs
  - Troubleshooting
  - FAQ

#### REQ-058: Developer Documentation
- **Must Have**:
  - Architecture docs
  - Code organization guide
  - Contribution guidelines
  - Build/deploy instructions

#### REQ-059: Legal Documentation
- **Must Have**:
  - LEGAL.md (operator liability)
  - THREAT_MODEL.md (security boundaries)
  - Terms of Service
  - Privacy policy

---

### Deployment Requirements

#### REQ-060: Development Environment
- **Must Have**:
  - Docker Compose setup (3 nodes locally)
  - Development configuration
  - Debug logging
  - Hot reload (if applicable)

#### REQ-061: Beta Release
- **Must Have**:
  - iOS TestFlight distribution
  - Android internal testing
  - macOS/Linux/Windows releases
  - 2-3 bootstrap VPS nodes

#### REQ-062: Production Deployment (v1.0+)
- **Must Have**:
  - Kubernetes-ready containers
  - High-availability setup (3+ nodes)
  - Monitoring + alerting
  - Auto-scaling capability

---

### Monitoring & Observability

#### REQ-063: Metrics Collection
- **Must Have**:
  - Node uptime (per node ID)
  - DHT query latency (percentiles)
  - Message throughput
  - Job completion rates
  - No PII logged

#### REQ-064: Logging
- **Must Have**:
  - Structured logs (JSON)
  - No message content logged
  - No PII logged
  - No plaintext data logged

#### REQ-065: Alerting
- **Must Have**:
  - Node downtime alerts
  - DHT latency degradation alerts
  - Job failure rate alerts
  - Shard availability alerts

---

### Accessibility Requirements

#### REQ-066: WCAG 2.1 Compliance
- **Must Have**:
  - Color contrast (4.5:1 for normal text, 3:1 for large)
  - Keyboard navigation
  - Screen reader support
  - ARIA labels

#### REQ-067: Mobile Accessibility
- **Must Have**:
  - Large touch targets (44pt minimum)
  - Haptic feedback options
  - Gesture alternatives

#### REQ-068: Smartwatch Accessibility
- **Must Have**:
  - Gesture controls (wrist movement)
  - Voice commands (if applicable)
  - Haptic notifications

---

### Localization Requirements

#### REQ-069: i18n Support
- **Must Have**:
  - UI strings extracted to translation files
  - Support for major languages (EN, DE, FR, ES, ZH, JA)
  - RTL language support
  - Date/time formatting per locale

---

## Success Metrics

### MVP v0.6
- [ ] 100 beta testers (50 from accessibility community)
- [ ] 99.9% uptime on bootstrap nodes
- [ ] 150ms VOIP latency (LAN)
- [ ] 80% cache hit rate
- [ ] <2% battery drain/hour

### v0.7
- [ ] Security audit score A- or better
- [ ] Zero critical vulnerabilities
- [ ] PQ crypto hybrid implemented

### v0.8
- [ ] 99.99% shard availability
- [ ] Legal TOS signed by 100+ operators
- [ ] Cold data archiving functional

### v0.9
- [ ] 99%+ job completion rate
- [ ] 30s average queue time
- [ ] 50-node integration tests passing

### v1.0
- [ ] 500+ active nodes
- [ ] 99.95% availability (all features)
- [ ] <100ms latency (optimal network)
- [ ] Self-sustaining community

---

**Owner**: Pangea Net Development Team  
**Last Updated**: December 23, 2025  
**Status**: Complete Requirements Specification
