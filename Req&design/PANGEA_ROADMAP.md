# PANGEA_NET_ROADMAP.md

**Version**: 1.0  
**Date**: December 23, 2025  
**Status**: Complete implementation roadmap with detailed requirements

---

## Overview

Pangea Net roadmap spans 40 weeks across 6 major milestones (v0.6 → v1.1). MVP focuses on accessibility + communication; compute/suite added progressively based on node network health.

---

## v0.6: MVP — Accessibility + Communication (Weeks 1-12)

### Phase 1A: Smartwatch Accessibility (Weeks 1-6)

**Mood Recommendation System**
- Smartwatch vitals integration (heart rate, sleep, steps)
- Local ML model (device-side inference, no cloud)
- Privacy-preserving fine-tuning on user data
- <500ms inference time
- 95% accuracy on validation dataset

**Gesture Recognition**
- Gyroscope → wrist movement mapping
- Click/swipe/scroll/hold commands
- Accessibility mode for disabled users
- 90%+ gesture accuracy
- Zero false positives in idle state

**Smartwatch SDKs**
- iOS: HealthKit integration
- Android: Health Connect API
- Real-time vitals streaming (<100ms latency)
- Battery optimization (<2% drain/hour background)
- Works with: Apple Watch, Garmin, Fitbit

**Acceptance Criteria**
- [ ] Mood rec: 95% accuracy, <500ms latency
- [ ] Gestures: 90% accuracy, zero false positives
- [ ] Battery: <2% drain/hour on both platforms
- [ ] Vitals: <100ms streaming latency
- [ ] All features work offline (cache vitals locally)

---

### Phase 1B: Core Communication (Weeks 4-12)

**VOIP (Opus Codec)**
- Peer-routed via libp2p
- Opus 48kHz encoding
- SOCKS5 Tor toggle (optional anonymity)
- <150ms E2E latency (LAN)
- <300ms E2E latency (WAN + Tor)
- Call drop rate <1%

**Chat & Messaging**
- End-to-end AES-256-GCM encryption
- Message delivery receipts
- Typing indicators
- Forward secrecy (Double Ratchet or similar)
- Offline message queue (auto-sync on reconnect)
- Zero plaintext on disk

**File Sharing (CES Pipeline)**
- Compress: zstd or brotli (2x ratio target)
- Encrypt: Client-side AES-256-GCM
- Shard: Reed-Solomon 8+2 FEC
- Distributed across network
- Nodes see only encrypted shards

**Tor Integration (SOCKS5)**
- Toggle in UI: "Use Tor Proxy"
- Test endpoint: 127.0.0.1:9050
- Show public IP vs Tor exit node IP
- Performance: acceptable <300ms latency with Tor

**Acceptance Criteria**
- [ ] VOIP: <150ms LAN, <300ms WAN+Tor, <1% drop
- [ ] Chat: E2E encrypted, offline queue, receipts working
- [ ] File share: 2x compression, 100% recovery (2 nodes down)
- [ ] Tor: Optional toggle, IP display correct
- [ ] All features: Full on iOS, Android, desktop

---

### Phase 1C: File Storage + DHT (Weeks 8-12)

**Dual DHT Architecture**
- Local DHT: Regional peer cache (fast, ~10ms query)
- Global DHT: Network-wide truth (slower, ~50-100ms query)
- Parallel query threads (both run concurrently)
- TTL: Local 30 days (post-access), Global 2 months

**BitTorrent-Style Caching**
- Anyone who downloads a file becomes a seed
- Auto-cleanup on TTL expiry
- Health-based eviction (deprioritize unhealthy seeds)
- 80% cache hit rate target (local)

**Bootstrap Nodes**
- 2-3 VPS nodes hosted by maintainers
- Pure bootstrap function (no user data storage)
- Health check endpoints
- ML monitors when to scale up/disable
- Cost: ~$15/mo total

**Acceptance Criteria**
- [ ] Local DHT: <10ms query, 99.9% uptime
- [ ] Global DHT: <100ms query, 99.9% uptime
- [ ] Cache hit rate: 80%+ for popular files
- [ ] Bootstrap: 99.99% uptime, <50ms discovery
- [ ] Fallback: Centralized archive working (last resort)

---

## v0.7: Security Hardening (Weeks 13-16)

**Cargo.toml Audit & SemVer**
- Replace pinned `=x.y.z` with ranges `^x.y`
- Create CARGO_PINS.md for any pins that must stay (with justification)
- Add CI job: `cargo tree`, `cargo update`, `cargo audit`
- Weekly dependency freshness tests

**Node Health ML**
- Score formula: `(uptime_pct × 0.4) + (latency_inverse × 0.3) + (availability_pct × 0.3)`
- Buckets: 0-30 (avoid), 30-70 (degraded), 70-100 (healthy)
- Update every 5 minutes via DHT pings
- Auto-blacklist scores <30

**Post-Quantum Crypto (Hybrid)**
- Library: aws-lc-rs with rustls-post-quantum
- Algorithm: X25519 + ML-KEM hybrid
- Handshake latency: <200ms
- Security audit required before production

**Acceptance Criteria**
- [ ] Cargo.toml: Zero unjustified pins
- [ ] CI: Freshness tests passing weekly
- [ ] Health score: 95% correlation with manual scoring
- [ ] PQ crypto: Hybrid handshake <200ms, audit pass

---

## v0.8: Storage + Legal (Weeks 17-22)

**DKG (Distributed Key Generation)**
- Threshold cryptography (t-of-n shares)
- Shared data key generation
- Key rotation support
- Any t holders can reconstruct
- <1% collusion risk

**View-Only Mode**
- Communications only, no storage management
- Can participate as seed (lightweight)
- Reduced features initially (essential only)
- Zero storage legal liability
- Clear UI toggle

**IP Rotation + Certificate Proof**
- When peer IP changes: send `(old_ip, new_ip, signature, certificate)`
- Peers verify and update routing
- Seamless reconnection without re-bootstrap
- Proof of identity prevents SYBIL reuse

**Cold Data Archiving**
- Local DHT: 30 days post-access (offer delete seed)
- Global DHT: 2 months post-access (flag as cold)
- Archive fallback: Centralized copy if no nodes have shard
- ML triggers re-replication at 20% shard loss

**Legal TOS & Disclosures**
- README section: "Legal & Risk"
- UI first-run warning when enabling storage
- Operator liability table (uploader vs seed vs receptor)
- Multi-jurisdiction compliance notes
- Contact: team@pangea.net for questions

**Acceptance Criteria**
- [ ] DKG: t-of-n threshold, <1s key gen
- [ ] View-only: Full comms, zero storage liability
- [ ] IP rotation: 100% reconnect success, <2s downtime
- [ ] Archive: Cold data <2 months, auto-fallback
- [ ] Legal: TOS signed, UI warnings shown

---

## v0.9: Distributed Compute (Weeks 23-30)

**WASM + Encrypted I/O Tunnel**
- Separate decrypt key per job (different from storage key)
- TLS + padding on I/O (host sees ciphertext)
- One-time ephemeral keys per computation
- Host cannot access plaintext (only encrypted traffic)
- Padding defeats timing attacks

**Job Scheduler**
- Health-ranked node selection (prefer score >80)
- Retry + exponential backoff
- Queue with ETA and position
- 99% job completion rate
- <30s average queue time

**Re-replication Automation**
- Trigger at 20% shard loss (ML monitors)
- Auto-select healthy target nodes (health score ranked)
- Encrypted shard copy (no decryption on nodes)
- <10s trigger latency
- Zero user intervention

**Job Queue with Backpressure**
- UI shows: "Network busy, queued at position 5, ~30s wait"
- Graceful degradation when <80% capacity available
- Capacity feedback to users
- No silent failures

**Acceptance Criteria**
- [ ] WASM: Zero plaintext exposure, <5% perf overhead
- [ ] Scheduler: 99% completion, <30s queue
- [ ] Re-replication: <10s latency, 100% availability
- [ ] Queue: Backpressure working, ETA accurate

---

## v1.0: Full Suite + Stability (Weeks 31-40)

**Decentralized YouTube-Like**
- Content discovery via DHT
- Peer-routed video streams
- VP9/AV1 codecs (HD support)
- <2s seek latency
- 1080p@30fps on 50+ nodes

**Decentralized Email**
- Encrypted mailboxes (AES-256-GCM)
- Decentralized address book (DHT-based)
- Spam filtering via reputation
- Offline sync support
- IMAP compatibility layer

**Office Suite**
- CRDT-based collaborative docs (conflict-free)
- Real-time multiplayer sheets
- <100ms cursor/edit sync
- Export to ODT/PDF
- Import from Google Docs

**Enterprise SLAs**
- Uptime guarantees (99.9%)
- Priority support tier
- Custom job scheduling
- Audit logs + compliance reports

**Full Integration Tests**
- 50+ node cluster simulation
- All features end-to-end
- Fault injection (25% node failure)
- Performance benchmarks
- Security audit

**Acceptance Criteria**
- [ ] YouTube: <2s seek, 1080p@30fps
- [ ] Email: Encrypted, offline sync, spam filter
- [ ] Docs: CRDT merge, <100ms sync
- [ ] SLAs: 99.9% uptime, audit logs
- [ ] Integration: All features on 50 nodes

---

## v1.1+: Research (Post-Launch)

- **Intel SGX Integration**: True private compute via TEE
- **Homomorphic Encryption**: On-encrypted-data computation
- **Advanced ML**: Predictive re-replication, anomaly detection
- **Full Decentralized Suite**: All features (docs, sheets, email, YouTube, compute)

---

## Non-Functional Requirements (All Versions)

| Requirement | Target | Notes |
|-------------|--------|-------|
| E2E Latency | <150ms LAN, <500ms WAN | +100ms for Tor |
| Node Health | 85%+ availability | Graceful at 70%+ |
| Encryption | AES-256-GCM everywhere | Client-side before shard |
| Scalability | 5→100 nodes seamless | No hardcoded limits |
| Shard Tolerance | 2 permanent failures | 8+2 Reed-Solomon |
| Battery Drain | <2% per hour mobile | Background sync only |
| Storage | 100GB per node typical | Configurable per user |
| Bandwidth | Fair DHT tit-for-tat | No hoarding |

---

## Testing Strategy

| Test Type | Coverage | Examples |
|-----------|----------|----------|
| **Unit** | 90%+ | CES pipeline, health scoring, DHT queries |
| **Integration** | 50-node clusters | Bootstrap, re-replication, IP rotation |
| **E2E** | Real devices | Smartwatch→VOIP→file storage→compute |
| **Security** | Fuzzing + audit | Crypto primitives, WASM sandbox |
| **Load** | 100 nodes, 50% churn | Job queue saturation, cache coherency |
| **Fault Injection** | 25% node failure | Graceful degradation, recovery |

---

## Deployment Plan

**MVP (v0.6) Launch**
```
├─ iOS app (TestFlight beta)
├─ Android app (Google Play internal)
├─ Desktop (GitHub releases)
├─ 3x Bootstrap VPS (~$15/mo)
└─ Centralized archive fallback
```

**Scale to 50 nodes (v0.8)**
```
├─ Disable bootstrap nodes (self-sufficient)
├─ Disable centralized fallback (DHT handles)
├─ Move to public release (open beta)
└─ Metrics: 99.99% availability, <500ms latency
```

**Scale to 200+ nodes (v1.0)**
```
├─ Enterprise tier (SLAs + support)
├─ API for developers
├─ Content creators migration program
└─ Metrics: 99.95% availability, <100ms latency
```

---

## Success Metrics

| Milestone | Metric | Target |
|-----------|--------|--------|
| **v0.6 Launch** | Beta users | 100 (accessibility focus) |
| **v0.7 Security** | Audit score | A- or better |
| **v0.8 Storage** | Shard availability | 99.99% |
| **v0.9 Compute** | Job completion rate | 99% |
| **v1.0 Suite** | Active nodes | 500+ |
| **v1.1 Research** | Features shipped | TEE + HE |

---

## Critical Path

```
Accessibility (v0.6, Weeks 1-6)
    ↓
Communication (v0.6, Weeks 4-12)
    ↓
Storage + DHT (v0.6, Weeks 8-12)
    ↓
Security Hardening (v0.7, Weeks 13-16)
    ↓
Legal + Archive (v0.8, Weeks 17-22)
    ↓
Distributed Compute (v0.9, Weeks 23-30)
    ↓
Full Suite (v1.0, Weeks 31-40)
    ↓
Research (v1.1+)
```

---

**Owner**: Pangea Net Team  
**Last Updated**: December 23, 2025
