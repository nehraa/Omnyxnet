# THREAT_MODEL.md

**Version**: 1.0  
**Date**: December 23, 2025

---

## Overview

This document describes what Pangea Net protects against, what it doesn't, and how to use it safely.

---

## What Pangea Protects Against

### 1. Eavesdropping on Communications

**Threat**: Someone intercepts your VOIP/chat messages.

**Pangea's Defense**
- End-to-end AES-256-GCM encryption (nobody in the middle can read)
- Forward secrecy via Double Ratchet (past messages safe even if key compromised)
- No server logs (peer-to-peer, ephemeral)

**Residual Risk**: Very low. Attacker can see you're communicating but not content.

---

### 2. File Access by Unauthorized Peers

**Threat**: Random node operator reads your stored file.

**Pangea's Defense**
- Client-side AES-256-GCM encryption before sharding
- Nodes hold only encrypted shards (zero knowledge)
- You hold encryption keys (only you can decrypt)
- No plaintext ever touches node storage

**Residual Risk**: Very low. Node operators see ciphertext only.

---

### 3. Node Operator Legal Liability

**Threat**: Node operator sued for content they host.

**Pangea's Defense**
- Encrypted shards = zero knowledge (operator can't prove what's stored)
- View-only mode = no storage management (seed participation only)
- Legal TOS clarifies: "Node operators not liable for encrypted content"
- Uploader responsible for content legality

**Residual Risk**: Varies by jurisdiction. Encryption provides strong legal defense.

---

### 4. Network Censorship (DNS/IP Blocking)

**Threat**: ISP blocks Pangea traffic via DNS/firewall.

**Pangea's Defense**
- DHT-based peer discovery (no central server to block)
- Optional Tor integration (SOCKS5 proxy anonymizes traffic)
- P2P bootstrap (network self-heals)

**Residual Risk**: Tor can be slow (~300ms latency); heavily censored regions may struggle.

---

### 5. Data Theft from Your Device

**Threat**: Malware on your phone/laptop steals encryption keys.

**Pangea's Defense**
- Client-side encryption (keys never leave your device)
- Optional smartwatch (separate device, harder to compromise)
- Biometric unlock (Face ID, fingerprint, pattern)

**Residual Risk**: Medium. If your device is compromised, keys are at risk.

---

## What Pangea Does NOT Protect Against

### 1. Host Sees WASM Computation Data

**What It Means**: When compute job runs, the host OS can observe raw data (in memory, on disk).

**Why**
- WASM sandbox isolates execution but not memory/storage
- Host process has access to plaintext during computation
- Can't prevent without TEE (Intel SGX)

**Mitigation (v0.9+)**
- Encrypted I/O tunnel (host sees only ciphertext on network)
- One-time ephemeral keys (host can't decrypt even if it tries)
- Not perfect but better than plaintext

**Timeline**: v1.1+ gets Intel SGX for true private compute.

---

### 2. SYBIL Attacks (Fake Nodes)

**What It Means**: Attacker creates 1000 fake node IDs and controls network.

**Why It's Hard to Prevent**
- Anonymous network = easy to create identities
- Can't require payment (excludes poor countries)
- Reputation = game-able

**Pangea's Defense**
- ML-based health scoring (fake nodes fail uptime/latency tests)
- Random node selection for jobs (attacker needs 1000s for majority)
- Redundancy (critical jobs run on 2-3 independent nodes)
- IP rotation + certificate proof (persistent identity, hard to sybil)

**Residual Risk**: Medium. Determined attacker can create 100+ fake nodes; unlikely to breach majority.

---

### 3. Timing Attacks

**What It Means**: Attacker observes how long encryption takes, guesses operations.

**Why**
- Cryptographic operations take variable time
- Constant-time math is hard (still leaks small amounts)

**Pangea's Defense**
- Uses audited crypto libraries (aws-lc-rs, rustls)
- Side-channel mitigation built-in
- Padding + noise on encrypted traffic (hides I/O patterns)

**Residual Risk**: Low. Padding defeats most timing attacks; very determined attacker might correlate.

---

### 4. Node Operator Sees Your IP

**What It Means**: Even encrypted, peer knows your IP address.

**Why**
- Peer-to-peer = peers learn each other's IPs
- libp2p relays can't hide this

**Pangea's Defense**
- Optional Tor routing (masks real IP, shows Tor exit node)
- VPN compatible (use alongside Pangea)
- Distributed architecture (no central server to log IPs)

**Residual Risk**: Medium. IP reveals rough location; Tor fixes this.

---

### 5. File Availability When Nodes Are Offline

**What It Means**: If 25+ of 50 shard holders go offline, file is hard to recover.

**Why**
- 8+2 Reed-Solomon can tolerate 2 offline shards permanently
- Beyond that, re-replication takes time

**Pangea's Defense**
- ML triggers re-replication at 20% shard loss (automatic)
- Local DHT caches popular files (fast retrieval)
- Archive fallback (centralized copy if all nodes down)

**Residual Risk**: Low. 99.99% availability target; extreme failure requires 25+ nodes down simultaneously.

---

### 6. Data Staleness / Inconsistency

**What It Means**: File version gets out of sync across nodes; you read old version.

**Why**
- Decentralized systems have eventual consistency
- Two nodes might have different versions temporarily

**Pangea's Defense**
- Version hashing (metadata includes version number)
- ML monitors shard staleness (re-replication if too old)
- You always get latest version (global DHT is truth source)

**Residual Risk**: Low. Unlikely unless node clocks wildly out of sync.

---

## Attack Scenarios

### Scenario 1: Nation-State Wants Your Messages

**Attacker Capability**: Access to ISP/backbone, can intercept all traffic

**Can Pangea Prevent?**
- Encryption protects content (nation can't read)
- Tor integration masks IP (partial protection)
- DHT avoids central log (no "message log" to subpoena)

**Can't Prevent**
- Metadata (when/how often you communicate)
- Your device is compromised (keys stolen)
- Tor exit node logs (last-hop visibility)

**Recommendation**: Use Tor toggle; assume metadata is visible.

---

### Scenario 2: Criminal Uploads Child Abuse Material (CSAM)

**Attacker Capability**: Illegal content distributed across network

**Pangea's Design**
- No content moderation (decentralized)
- Files encrypted (nobody knows what's where)
- Node operators have zero liability (can't see plaintext)

**Defense Mechanisms**
- Nodes can self-delete (optional storage mode)
- Hash-based filtering (known-bad hashes block automatically, if implemented)
- Uploader responsible for legality (TOS)

**Risk**: Network could unknowingly host illegal content. Crypto doesn't help law enforcement.

**Pangea's Position**: We cannot prevent this. Decentralization = no gatekeepers. Jurisdictions must enforce at ISP/device level.

---

### Scenario 3: Attacker Controls 100 Nodes

**Attacker Capability**: 100 fake nodes in 500-node network (20% majority)

**Can They?**
- See traffic routing through their nodes (partial eavesdropping)
- Drop/delay some messages
- Force re-replication to their nodes

**Can't They?**
- Decrypt your messages (E2E crypto)
- Impersonate you (Ed25519 keys persistent)
- Control network majority (80% still honest)

**Defense**: Random node selection makes it statistically unlikely attackers intercept your message.

**Recommendation**: Run your own node (don't rely on attackers' peers).

---

## Cryptographic Assumptions

Pangea's security depends on:

1. **AES-256-GCM is unbreakable** (current assumption, true for 20+ years)
2. **X25519/P-256 are computationally secure** (no quantum algorithms yet)
3. **Ed25519 signatures are unforgeable** (no known attacks)
4. **Tor anonymity is maintained** (depends on Tor's design)
5. **No quantum computers exist yet** (NIST PQ candidates evaluated)

**Post-Quantum Plan**: v0.7 adds ML-KEM hybrid (hedges against quantum).

---

## What You Should Do

### Best Practices

**Protect Your Device**
- Use device lock (fingerprint, face, PIN)
- Keep OS updated (patches)
- Don't install untrusted apps
- Use antivirus/malware protection

**Protect Your Keys**
- Never share recovery phrases
- Use strong password for key derivation
- Back up keys in secure location (paper, hardware wallet)
- Consider 2FA where available

**Use Tor If Needed**
- Toggle "Use Tor Proxy" in settings
- Be aware of speed penalty (~200ms extra)
- Don't disable for performance (defeats purpose)

**Monitor Your Network**
- Run a node yourself (get involved)
- Check node health scores (prefer healthy peers)
- Report suspicious behavior (Discord)

**Assume Metadata is Visible**
- Who you communicate with (visible to peers)
- When (timestamps on messages)
- How often (message frequency)
- Not plaintext, but metadata can reveal patterns

---

## What NOT to Assume

**Don't Assume**:
- Pangea hides who you are (use Tor for that)
- Files disappear after deletion (archival may keep copies)
- Nobody can ever get your data (quantum computers change everything)
- It's perfect (no system is)
- Governments can't find you (metadata + metadata correlation can)

---

## Responsible Disclosure

If you find a vulnerability:

1. **Don't post publicly** (gives attackers time)
2. **Email security@pangea.net** (if created)
3. **Include**: How to reproduce, impact, suggested fix
4. **Timeline**: 30 days for team to patch before you disclose

---

## Audit & Security Review

- **MVP (v0.6)**: Internal review (open source audit welcome)
- **v0.7**: Professional security audit (PQ crypto focus)
- **v1.0**: Full third-party audit (all critical components)
- **Ongoing**: Bug bounty program (incentivize researchers)

---

## Summary Table

| Threat | Protection Level | Residual Risk | Notes |
|--------|------------------|---------------|-------|
| Eavesdropping on comms | Very Strong | Very Low | E2E encryption + Tor |
| File access by peers | Very Strong | Very Low | Client-side encryption |
| Node operator liability | Strong | Medium | Jurisdiction-dependent |
| Network censorship | Strong | Medium | Tor + DHT help; may be slow |
| Host sees compute data | Medium | Medium | Encrypted I/O tunnel v0.9+ |
| SYBIL attacks | Medium | Medium | ML scoring + redundancy |
| Your device compromised | Weak | High | Own problem (crypto can't help) |
| Metadata visibility | Weak | High | Tor helps but not perfect |
| Data staleness | Strong | Low | ML-driven re-replication |

---

**Owner**: Pangea Net Security Team  
**Last Updated**: December 23, 2025
