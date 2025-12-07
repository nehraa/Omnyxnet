# Pangea Net Go Node - Architecture

**Version:** 0.6.0-alpha  
**Last Updated:** 2025-12-07

> 📋 This document describes the implemented architecture. For version status and deployment readiness, see [../VERSION.md](../VERSION.md).

## Overview

This document explains the code organization and architecture of the Go node implementation, including the new DCDN components.

## Folder Structure

```
WGT/
├── cmd/
│   └── go-node/          # Main application entry point
│       └── main.go       # CLI and node initialization
│
├── internal/             # Internal packages (not exposed to Python)
│   ├── store/           # Node data storage
│   │   └── store.go     # Thread-safe node store with quality metrics
│   ├── network/         # P2P networking layer
│   │   └── p2p.go       # Noise Protocol, connections, latency measurement
│   ├── rpc/             # Cap'n Proto RPC server
│   │   └── server.go    # RPC server implementation
│   └── utils/           # Utility functions
│       └── ports.go     # Port cleanup and availability checking
│
├── pkg/
│   └── api/             # Public API for Python (high-level functions)
│       └── node.go      # NodeManager - easy-to-use functions for Python
│
├── schema/              # Cap'n Proto schema definitions
│   └── schema.capnp     # RPC interface definition
│
├── rust/                # DCDN Data Plane
│   ├── src/             # Rust source code
│   └── Cargo.toml       # Rust dependencies
│
├── docs/                # Documentation
│   └── ARCHITECTURE.md  # This file
│
└── scripts/             # Utility scripts
    └── cleanup.sh       # Port cleanup script
```

## Package Responsibilities

### cmd/go-node
**Purpose**: Main application entry point
**What it does**:
- Parses command-line arguments
- Initializes all components (store, network, RPC)

### rust/ (DCDN Data Plane)
**Purpose**: High-performance content delivery
**What it does**:
- **QUIC Layer**: Manages high-speed UDP connections using `quinn`.
- **FEC Engine**: Forward Error Correction using Reed-Solomon codes.
- **Ring Buffer**: Lock-free data structures for low-latency streaming.
- **Integrity Plane**: Cryptographic verification of chunks.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   CONTROL PLANE                          │
│  (Go Node / Python CLI)                                  │
│  - Configuration                                         │
│  - Peer Discovery                                        │
│  - Policy Management                                     │
└────────────────┬────────────────────────────────────────┘
                 │ Configuration Updates
                 │ Metrics Push
                 ▼
┌─────────────────────────────────────────────────────────┐
│                    DATA PLANE                            │
│  (High-throughput packet processing in Rust)             │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ QUIC Layer   │─▶│ FEC Engine   │─▶│ Ring Buffer  │ │
│  │ (quinn)      │  │ (reed-solomon)│  │ (lock-free)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```
