# DCDN System Documentation

**Version:** 1.0.0-alpha  
**Last Updated:** December 7, 2025

## Overview

The Decentralized Content Delivery Network (DCDN) is a high-performance subsystem of Pangea Net designed for low-latency video streaming and large file distribution. It separates the **Control Plane** (Go/Python) from the **Data Plane** (Rust) to achieve maximum throughput.

## Architecture

### Layers

1.  **Control Plane (Go/Python)**
    *   Handles peer discovery, negotiation, and policy.
    *   Configures the Data Plane via gRPC/FFI.
    *   Collects aggregated metrics.

2.  **Data Plane (Rust)**
    *   **QUIC Transport**: Uses `quinn` for reliable/unreliable UDP streams.
    *   **FEC Engine**: Reed-Solomon erasure coding for packet loss recovery.
    *   **Ring Buffer**: Lock-free memory management for zero-copy data handling.

3.  **Integrity Plane**
    *   Ed25519 signatures for chunk verification.
    *   Reputation tracking based on delivery performance.

## Features

*   **Adaptive Bitrate Streaming**: Automatically adjusts quality based on network conditions.
*   **Multipath Delivery**: Fetches chunks from multiple peers simultaneously.
*   **Forward Error Correction (FEC)**: Recovers lost packets without retransmission.
*   **Containerized Testing**: Fully isolated test environment using Docker/Podman.

## Usage

### Running the Demo

You can run the DCDN demo via the Desktop App or the CLI.

**Via Desktop App:**
1.  Open `desktop_app_kivy.py`.
2.  Navigate to the **DCDN** tab.
3.  Click **Run Demo**.

**Via CLI:**
```bash
python main.py dcdn demo
```

### Container Tests

To verify the DCDN implementation in an isolated environment:

```bash
./scripts/test_pangea.sh
# Select option 20.2 (Container Tests)
```

This will:
1.  Build a Docker image containing the Rust DCDN node.
2.  Spin up a test container.
3.  Run the test suite (chunk transfer, FEC recovery).
4.  Output logs to `test_log.txt`.

## Configuration

The DCDN behavior is controlled by `config/dcdn_config.json` (if present) or default values in the Rust code.

*   `max_concurrent_connections`: Default 1000
*   `congestion_algorithm`: BBR or CUBIC
*   `fec_shard_ratio`: 10:4 (Data:Parity)

## Development

The DCDN source code is located in the `rust/` directory.

```bash
cd rust
cargo build --release
cargo test
```
