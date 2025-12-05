# Quick Start Guide - Pangea Net

**Version:** 0.3.0-alpha  
**Last Updated:** 2025-11-22

> ⚠️ **Alpha Software:** This is development software. Works locally, NOT production-ready.

## 🚀 New to Pangea Net? Start Here!

### 1. Understand the Status
**Read First:** [VERSION.md](VERSION.md) - Know what's working and what's not

**Quick Status:**
- ✅ Works: Local testing, basic features, **cross-device P2P communication**
- 🚧 In Progress: Integration testing, production hardening
- ❌ Not Ready: Production deployment, key persistence

### 2. Find Documentation
**Read Second:** [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Navigate all docs

**Key Documents:**
- Project overview: [README.md](README.md)
- What's implemented: [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)
- Version history: [CHANGELOG.md](CHANGELOG.md)

### 3. Choose Your Component

#### Go Node (Networking)
- **Purpose:** P2P networking with encryption
- **Doc:** [go/README.md](go/README.md)
- **Status:** Alpha - works locally

#### Rust Node (Storage)
- **Purpose:** CES pipeline, file storage
- **Doc:** [rust/README.md](rust/README.md)
- **Status:** Alpha - works locally

#### Python AI (Intelligence)
- **Purpose:** ML-based optimization
- **Doc:** [python/README.md](python/README.md)
- **Status:** Alpha - works locally

### 4. Establish Network Connection

```bash
# Use the setup menu
./scripts/setup.sh
# Select: 2) Establish Network Connection

# Or check network status
./scripts/check_network.sh --status
```

### 5. Run Tests

**Easiest Way (Interactive Menu):**
```bash
# Interactive test menu - tests communication, compute, messaging
./scripts/test_pangea.sh

# Run all tests automatically
./scripts/test_pangea.sh --all
```

**Matrix Multiply CLI:**
```bash
cd python && source .venv/bin/activate

# Generate and multiply random matrices
python main.py compute matrix-multiply --size 10 --generate --verify

# Distributed execution (requires network connection)
python main.py compute matrix-multiply --size 50 --generate --connect
```

**Python CLI Tests:**
```bash
cd python && source .venv/bin/activate

# Test communication (P2P connection)
python main.py test communication

# Test compute (CES pipeline)
python main.py test ces

# Test all
python main.py test all

# Manual peer connection (when mDNS fails)
python main.py test manual-connect 192.168.1.100:9081
```

**Container Tests:**
```bash
# Quick tests (no Docker)
./scripts/run_container_tests.sh --quick

# Full test suite (requires Docker)
./scripts/run_container_tests.sh --full
```

**Component Tests:**
```bash
# Run all tests
./tests/test_all.sh

# Component-specific tests
./tests/test_go.sh
./tests/test_rust.sh
./tests/test_python.sh
```

See [tests/README.md](tests/README.md) for details.

---

## 📚 Documentation Structure

```
WGT/
├── VERSION.md              ⭐ START HERE - Project status
├── DOCUMENTATION_INDEX.md  📋 Find any doc
├── CHANGELOG.md            📝 Version history
├── README.md               📖 Project overview
├── QUICK_START.md          🚀 This file
│
├── docs/                   📚 Technical guides
│   ├── ARCHITECTURE.md
│   ├── BLUEPRINT_IMPLEMENTATION.md
│   ├── RUST.md
│   ├── CACHING.md
│   └── PYTHON_API.md
│
├── go/README.md            🔵 Go component
├── rust/README.md          🟠 Rust component
└── python/README.md        🟢 Python component
```

---

## ❓ Common Questions

**Q: Is this production-ready?**  
A: No. Alpha stage (v0.3.0-alpha). Local testing only.

**Q: Which documentation is current?**  
A: All docs updated 2025-11-22 to v0.3.0-alpha. Check version headers.

**Q: What's actually working?**  
A: See [VERSION.md](VERSION.md) - "Implemented Features" section.

**Q: Where do I start reading?**  
A: [VERSION.md](VERSION.md) → [README.md](README.md) → Component READMEs

**Q: How do I know if docs conflict?**  
A: Trust order: VERSION.md > CHANGELOG.md > Component READMEs > Other docs

---

## 🎯 Quick Navigation

- **Understand status** → [VERSION.md](VERSION.md)
- **Find any doc** → [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
- **See what changed** → [CHANGELOG.md](CHANGELOG.md)
- **Learn architecture** → [README.md](README.md)
- **Run tests** → [tests/README.md](tests/README.md)
- **Use Go node** → [go/README.md](go/README.md)
- **Use Rust node** → [rust/README.md](rust/README.md)
- **Use Python AI** → [python/README.md](python/README.md)

---

## ⚠️ Important Reminders

1. **Alpha Software** - Not production-ready
2. **Version 0.3.0-alpha** - Check docs show this version
3. **Local Testing Only** - WAN deployment not tested
4. **VERSION.md is Truth** - Authoritative status source
5. **All Docs Updated** - 2025-11-22, synchronized

---

**Need Help?** Check [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for detailed navigation.

*Created: 2025-11-22 | Version: 0.3.0-alpha*
