# Pangea Net Documentation

**Last Updated**: December 7, 2025

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

#### DCDN & Streaming
- **[DCDN.md](DCDN.md)** ⭐ NEW (Dec 7, 2025)
  - Decentralized Content Delivery Network
  - Rust Data Plane (QUIC, FEC, Ring Buffer)
  - Streaming Architecture
  - Containerized Testing

#### Desktop Application
- **[DESKTOP_APP.md](DESKTOP_APP.md)** ⭐ UPDATED (Dec 7, 2025)
  - New Kivy/KivyMD Interface
  - DCDN Integration
  - Direct RPC Connectivity
