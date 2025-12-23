# PRODUCT_VISION.md

**Version**: 1.0  
**Date**: December 23, 2025

---

## Executive Summary

Pangea Net is a decentralized platform enabling privacy-first communication, storage, and compute without reliance on centralized servers. We focus on **accessibility + community**, starting with smartwatch-powered features and gradually expanding to a full decentralized suite.

---

## What Pangea Does

### Core Value Proposition

**For Users**
- Encrypted communication (VOIP, chat) that nobody can intercept
- Distributed file storage that you control (keys in your hands)
- Accessible interface (smartwatch gestures, voice controls)
- Network that works peer-to-peer (no central authority)

**For Accessibility Community**
- Gesture controls via smartwatch gyroscope (wrist movements = clicks/swipes)
- Mood recommendation from health vitals (HR, sleep, steps)
- Privacy-preserving ML (models fine-tuned on-device only)
- Works for disabled users (alternative input methods)

**For Privacy-Conscious Users**
- End-to-end encrypted everything (nobody sees plaintext except you)
- Optional Tor integration (additional anonymity layer)
- Legal clarity (encrypted data = zero operator liability)
- Own your data (no corporate harvesting)

**For Developers**
- Open-source platform (fork/modify/contribute)
- Simple APIs for building apps
- Decentralized infrastructure (no servers to maintain)
- Community-driven features

---

## What Pangea Does NOT Do (Yet)

### Out of Scope for MVP (v0.6)
- **Distributed compute**: Deferred to v0.9 (no business need in MVP)
- **Web browsing**: VOIP/chat only via Tor (web browsing is future v1.0+)
- **Private compute**: WASM shows data to host (true TEE in v1.1+)
- **Homomorphic encryption**: Research-phase (post-v1.0)
- **TUN routing**: SOCKS5 only (TCP-level anonymity in v1.0+)

### Why Not These Things

1. **Compute too complex early**: Need stable network first; users don't have 3-hour compute tasks in MVP.
2. **Web browsing adds scope creep**: Tor handles communication; webpage viewing is separate.
3. **Private compute requires hardware**: Intel SGX/AMD SEV needed; limits adoption.
4. **HE too slow**: 1000x slower than plaintext; research-only for now.
5. **TUN overkill**: SOCKS5 solves 99% of anonymity needs; TUN adds complexity.

---

## Long-Term Vision (v1.0+)

### Full Decentralized Suite

**Phase by Phase**
1. **v0.6 (MVP)**: Smartwatch + VOIP/chat + file storage
2. **v0.7**: Security hardening (PQ crypto, dependency audit)
3. **v0.8**: Legal clarity + DKG sharing
4. **v0.9**: Distributed compute (job scheduler, WASM)
5. **v1.0**: YouTube-like + email + office suite
6. **v1.1+**: TEE integration + homomorphic encryption

### Products to Ship Eventually

- **Decentralized YouTube**: Peer-streamed videos, creator monetization
- **Decentralized Email**: Encrypted mailboxes, address book, spam filter
- **Decentralized Office**: Collaborative docs, sheets (CRDT-based)
- **Decentralized Compute**: Job scheduler, ML training, batch processing

---

## Go-to-Market Strategy

### Phase 1: Accessibility First (MVP, Weeks 1-12)

**Target Audience**: Health enthusiasts, disabled users, accessibility advocates

**Features**
- Smartwatch mood recommendation (from vitals)
- Gesture controls (wrist movement = clicks)
- Privacy-preserving AI (local fine-tuning)

**Launch Channels**
- iOS TestFlight + Android Play Store (beta)
- Accessibility forums + Reddit (r/accessibility)
- Partner with smartwatch makers (Garmin, Fitbit, Apple)
- Publish case studies (disabled users testing)

**Goal**: 100 beta users in 3 months

---

### Phase 2: Privacy Community (Weeks 13-24)

**Target Audience**: Privacy-conscious individuals, small communities, activists

**Features**
- VOIP (encrypted, peer-routed, Tor toggle)
- Chat (E2E encrypted, offline queue)
- File sharing (CES pipeline)

**Launch Channels**
- Public beta (invite-only)
- Privacy Reddit (r/privacy, r/privacytoolsio)
- Community Discord/Telegram channels
- Build on Phase 1 user base

**Goal**: 500+ active nodes

---

### Phase 3: Content Creators (Weeks 25-40)

**Target Audience**: YouTube creators, archivists, journalists, researchers

**Features**
- Decentralized YouTube-like (peer-streamed, creator revenue)
- Decentralized email (encrypted, no ads)
- Decentralized storage (cheap, reliable)

**Launch Channels**
- Pitch to content creators (YouTube migration)
- Compare vs IPFS/Arweave (better UX, built-in features)
- Academic research programs
- Media partnerships

**Goal**: 1000+ nodes, 10k creators on platform

---

### Phase 4: Enterprise (Post-v1.0)

**Target Audience**: Enterprises, governments, NGOs, researchers

**Features**
- Distributed compute (job scheduling, fault tolerance)
- Office suite (for teams)
- SLA-backed services

**Launch Channels**
- DevOps + infrastructure teams
- Research grants programs
- Government tech initiatives
- Enterprise support tier ($$$)

**Goal**: 10k+ nodes, $revenue/mo

---

## Why Now? Why Pangea?

### Problems We Solve

| Problem | Pangea Solution |
|---------|-----------------|
| Centralized data harvesting | Client-side encryption + distributed storage |
| Censorship (DNS, IP blocks) | Peer-routed via Tor, DHT-based discovery |
| Node operators' legal risk | Encrypted shards = zero knowledge = zero liability |
| Early adoption pain | Bootstrap nodes + centralized fallback (phase out at scale) |
| Privacy theater (WASM shows data) | Encrypted I/O tunnel (host sees ciphertext only) |
| Arbitrary rules (10-min dead nodes) | ML-driven adaptive health scoring |

### Why Not Alternatives?

| Alternative | Limitation | Pangea Advantage |
|-------------|-----------|-----------------|
| **IPFS** | No encryption, no access control, complex | CES pipeline, legal clarity, easy UX |
| **Tor** | Slow, VOIP/email hard, no storage | Built-in features, app layer |
| **Matrix** | Centralized servers needed | Pure P2P, nodes are optional |
| **Nextcloud** | Requires your own server | Peer-to-peer, bootstrap automatic |
| **Telegram** | Centralized, no compute | Decentralized, extensible |

---

## User Personas

### Persona 1: Alex (Accessibility Advocate)
- Uses smartwatch for health tracking
- Wants accessible technology (alternative input methods)
- Privacy-conscious but not paranoid
- Early adopter, willing to test beta

**Use Case**: Enable mood recommendations via wrist gestures; control app entirely via movements.

---

### Persona 2: Casey (Privacy Activist)
- Concerned about surveillance
- Uses Tor browser daily
- Encrypts emails, uses Signal
- Wants to move friends to decentralized platform

**Use Case**: VOIP calls over Tor, encrypted file backup, build community.

---

### Persona 3: Jordan (Content Creator)
- Frustrated with YouTube's policies
- Wants own audience, direct revenue
- Looking for alternatives to Big Tech

**Use Case**: Publish videos on decentralized YouTube, earn directly from viewers.

---

### Persona 4: Sam (Enterprise IT)
- Responsible for company data security
- Evaluates new infrastructure solutions
- Needs SLA guarantees and support

**Use Case**: Deploy Pangea for team communication + file storage, negotiate SLA.

---

## Success Metrics

### MVP (v0.6)
- 100 beta testers (50% from accessibility community)
- 99.9% uptime (communication features)
- <150ms latency (LAN), <300ms (WAN + Tor)
- 80% retention (30-day active)

### v1.0 (Full Suite)
- 500+ active nodes
- 10k+ creators on platform
- 99.95% availability (all features)
- $500k/year revenue (enterprise + donations)

### v2.0+ (Mature)
- 100k nodes globally
- 1M+ users
- Competitor to centralized platforms
- Self-sustaining community (no VC needed)

---

## Team & Governance

### Current Team
- **Builder**: You (Rust/Go, decentralized systems, AI/ML)
- **Contributors**: Open source community

### Governance (Future)
- **MVP**: Benevolent dictator (you)
- **v1.0+**: Community DAO (token-based voting)
- **v2.0+**: Decentralized governance (no central authority)

---

## Funding & Sustainability

### Phase 1 (MVP → v0.8): Bootstrap
- Bootstrap on personal resources
- Open-source contributions (GitHub sponsors)
- Grants from privacy/open-source orgs

### Phase 2 (v0.9 → v1.0): Scale
- Enterprise subscriptions (SLAs, support)
- Donations from privacy community
- Maybe seed funding (if needed)

### Phase 3 (v1.0+): Sustainable
- Enterprise services ($1k+/mo per org)
- Creator revenue sharing (1-2% cut of tips/ads)
- Community donations + sponsorships
- No VC (maintain independence)

---

## Core Principles

1. **Privacy First**: Encryption everywhere; you own your keys
2. **Decentralized**: No single point of failure or control
3. **Accessible**: Works for everyone (disabled users, low bandwidth, old devices)
4. **Legal**: Zero liability for hosts; encryption = zero knowledge
5. **Open Source**: Community builds on it; no closed algorithms
6. **Independent**: Not beholden to advertisers or investors

---

## FAQ

**Q: Is this production-ready?**  
A: No. MVP (v0.6) ships smartwatch + communication. Full suite by v1.0 (10 months). Early testers welcome.

**Q: Can I run a node?**  
A: Yes. View-only mode (lightweight, zero storage risk) or full node (comms + storage). Bootstrap your own instance.

**Q: What about my data on nodes?**  
A: Encrypted before leaving your device. Nodes see only ciphertext. You hold keys (or DKG shares post-v0.8).

**Q: Is Tor required?**  
A: No. Optional SOCKS5 toggle for anonymity. Works fine without it.

**Q: Can the network be shut down?**  
A: Not by any single entity. Decentralized = resilient. As long as one node remains, network lives.

**Q: When can I use this?**  
A: MVP beta launch: 3 months. Full suite: 10 months. Community nodes + incentives TBD.

---

**Owner**: Pangea Net Team  
**Last Updated**: December 23, 2025
