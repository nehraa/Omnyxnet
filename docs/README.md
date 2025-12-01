# Pangea Net Documentation

**Last Updated**: November 22, 2025

This directory contains all technical documentation for Pangea Net.

## 📂 Directory Structure

```
docs/
├── api/                    # API and RPC documentation
│   └── CAPNP_SERVICE.md   # Cap'n Proto RPC interface
│
├── networking/            # Network layer documentation
│   └── NETWORK_ADAPTER.md # P2P networking details
│
├── testing/               # Testing documentation
│   └── TESTING_GUIDE.md   # Complete testing guide
│
├── archive/               # Historical documentation
│   └── [old docs]         # Previous implementation notes
│
└── [component docs]       # Legacy component documentation
```

## 🚀 Start Here

### New to Pangea Net?

1. **Main Index**: `DOCUMENTATION_INDEX.md` (in docs directory)
2. **Quick Start**: `QUICK_START.md`
3. **Status**: `STATUS_SUMMARY.md`

### Core Technical Docs

#### Network Layer
- **[networking/NETWORK_ADAPTER.md](networking/NETWORK_ADAPTER.md)** ⭐ NEW (Nov 22, 2025)
  - NetworkAdapter interface
  - LibP2P and Legacy implementations
  - FetchShard protocol
  - Connection modes (localhost vs cross-device)
  - mDNS status and workarounds

#### API Layer
- **[api/CAPNP_SERVICE.md](api/CAPNP_SERVICE.md)** ⭐ NEW (Nov 22, 2025)
  - Cap'n Proto RPC service
  - Upload/Download methods (fully wired!)
  - Shard distribution protocol
  - Reed-Solomon encoding
  - Integration with CES pipeline

#### Testing
- **[testing/TESTING_GUIDE.md](testing/TESTING_GUIDE.md)** ⭐ NEW (Nov 22, 2025)
  - Test suite overview
  - Localhost multi-node testing
  - Cross-device testing guide
  - Known issues and workarounds
  - Test results and status

### Implementation Updates

- **[IMPLEMENTATION_UPDATE_NOV22.md](IMPLEMENTATION_UPDATE_NOV22.md)** - Latest changes (Nov 22, 2025)

### Legacy Documentation

#### Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture overview
- **[BLUEPRINT_IMPLEMENTATION.md](BLUEPRINT_IMPLEMENTATION.md)** - Implementation blueprint
- **[REORGANIZATION_COMPLETE.md](REORGANIZATION_COMPLETE.md)** - Project reorganization

#### Component-Specific
- **[RUST.md](RUST.md)** - Rust implementation details
- **[PYTHON_API.md](PYTHON_API.md)** - Python API documentation
- **[CACHING.md](CACHING.md)** - Caching system
- **[MDNS.md](MDNS.md)** - mDNS discovery notes
- **[AUTOMATED_OPERATIONS.md](AUTOMATED_OPERATIONS.md)** - Automation docs

#### Archived
See `archive/` directory for historical documentation:
- Original implementation notes
- Previous status reports
- Old change logs
- Legacy assessment documents

## 🎯 Quick Reference

### Most Important Docs (Nov 22, 2025)

| Document | Purpose | Status |
|----------|---------|--------|
| [NETWORK_ADAPTER.md](networking/NETWORK_ADAPTER.md) | Network layer | ✅ Current |
| [CAPNP_SERVICE.md](api/CAPNP_SERVICE.md) | RPC interface | ✅ Current |
| [TESTING_GUIDE.md](testing/TESTING_GUIDE.md) | Testing | ✅ Current |
| [IMPLEMENTATION_UPDATE_NOV22.md](IMPLEMENTATION_UPDATE_NOV22.md) | Latest changes | ✅ Current |

### Finding Information

**I want to know about...**

- **Network connectivity** → [networking/NETWORK_ADAPTER.md](networking/NETWORK_ADAPTER.md)
- **Upload/Download** → [api/CAPNP_SERVICE.md](api/CAPNP_SERVICE.md)
- **Testing** → [testing/TESTING_GUIDE.md](testing/TESTING_GUIDE.md)
- **mDNS issues** → [networking/NETWORK_ADAPTER.md](networking/NETWORK_ADAPTER.md#connection-modes)
- **Recent changes** → [IMPLEMENTATION_UPDATE_NOV22.md](IMPLEMENTATION_UPDATE_NOV22.md)
- **Architecture** → [ARCHITECTURE.md](ARCHITECTURE.md)
- **Rust CES** → [RUST.md](RUST.md)
- **Python API** → [PYTHON_API.md](PYTHON_API.md)

## 📝 Documentation Standards

### When to Update

Update documentation when you:
- Add new features
- Change APIs or interfaces
- Fix bugs that affect behavior
- Update connection methods
- Change test procedures

### What to Update

| You Changed | Update This |
|-------------|-------------|
| Network layer | `networking/NETWORK_ADAPTER.md` |
| RPC methods | `api/CAPNP_SERVICE.md` |
| Tests | `testing/TESTING_GUIDE.md` |
| Major features | `IMPLEMENTATION_UPDATE_*.md` (new file) |
| CLI flags | Component README + root index |

### Documentation Format

- Use Markdown (`.md`)
- Include "Last Updated" date
- Add status indicators (✅ ⚠️ ⏳ ❌)
- Provide code examples
- Link to related docs
- Keep under 500 lines (split if needed)

## 🔄 Recent Updates

### November 22, 2025

**New Documentation**:
- Created `api/CAPNP_SERVICE.md` - RPC interface documentation
- Created `networking/NETWORK_ADAPTER.md` - Network layer documentation
- Created `testing/TESTING_GUIDE.md` - Comprehensive testing guide
- Created `IMPLEMENTATION_UPDATE_NOV22.md` - Today's changes

**Organization**:
- Created organized directory structure (`api/`, `networking/`, `testing/`)
- Moved old docs to `archive/`
- Updated main documentation index
- Cleaned up root directory

**Status**:
- All core components documented ✅
- All tests passing (4/4) ✅
- Directory organized ✅
- Known issues documented with workarounds ✅

## 🤝 Contributing to Docs

### Writing New Documentation

1. Choose appropriate directory:
   - API/RPC → `api/`
   - Network → `networking/`
   - Testing → `testing/`
   - General → root `docs/`

2. Use template:
```markdown
# Title

**File**: `path/to/code.go`
**Last Updated**: YYYY-MM-DD
**Status**: ✅ Complete / ⏳ Pending / ⚠️ Partial

## Overview
[Brief description]

## [Sections]
[Detailed content]

## Related Files
[Links to related docs]
```

3. Update this README
4. Update main `../DOCUMENTATION_INDEX.md`

### Reviewing Documentation

Check for:
- Accuracy (matches current code)
- Clarity (easy to understand)
- Completeness (covers all features)
- Links (no broken links)
- Examples (code examples work)
- Date (Last Updated is current)

## 📚 External References

- [libp2p Documentation](https://docs.libp2p.io/)
- [Cap'n Proto](https://capnproto.org/)
- [Reed-Solomon Error Correction](https://en.wikipedia.org/wiki/Reed%E2%80%93Solomon_error_correction)
- [Go libp2p Examples](https://github.com/libp2p/go-libp2p/tree/master/examples)

---

**For more information**, see the main documentation index at `../DOCUMENTATION_INDEX.md`

**Questions?** Check the testing guide at `testing/TESTING_GUIDE.md` or status summary at `../STATUS_SUMMARY.md`
