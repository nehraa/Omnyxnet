# Scripts Directory

**Last Updated:** 2025-12-04

Scripts for setup, testing, and development of Pangea Net.

## Quick Reference

| Script | Purpose |
|--------|---------|
| `setup.sh` | Interactive setup menu with all options |
| `live_test.sh` | Live P2P testing (chat/voice/video) |
| `verify_setup.sh` | Verify installation |
| `run-tests.sh` | Run all tests |

## Script Categories

### Setup & Installation

- **`setup.sh`** - Main setup script with interactive menu
  - Install dependencies
  - Build all components
  - Run tests
  - View logs
  
- **`verify_setup.sh`** - Verify that all components are installed correctly

### Live Testing

- **`live_test.sh`** - Interactive live P2P testing
  - Starts Go libp2p node
  - Provides menu for Chat, Voice, Video
  - Shows connection info (IP, port, peer ID) on one screen
  - Use on two devices to test real P2P communication

- **`easy_test.sh`** - Quick test for single device
- **`test_pangea.sh`** - Comprehensive P2P test with menu

### Cross-Device Testing

- **`cross_device_setup.sh`** - Setup for cross-device testing
- **`cross_device_streaming_test.sh`** - Test streaming between devices

### Development

- **`dev.sh`** - Development helper script
- **`run-tests.sh`** - Run the test suite
- **`export_docs.sh`** - Export documentation

### Testing Utilities

- **`test_10_nodes.sh`** - Test with 10 nodes
- **`test_automated.sh`** - Automated testing
- **`test_mdns.sh`** - Test mDNS discovery
- **`download_test_media.sh`** - Download test media files

## Usage Examples

### First-time Setup
```bash
./scripts/setup.sh
# Select option 1 for full installation
```

### Live P2P Test (Two Devices)
```bash
# Device 1 (Bootstrap):
./scripts/live_test.sh
# Press Y, copy the peer address

# Device 2 (Join):
./scripts/live_test.sh
# Press N, paste the peer address
# Select 1/2/3/4 for Chat/Voice/Video
```

### Run All Tests
```bash
./scripts/run-tests.sh
# Or use setup.sh and select option 7
```

## Notes

- All scripts use the **Go libp2p implementation** for networking
- Python files in `python/` are deprecated reference implementations
- Tests follow the Golden Rule: Go (networking), Rust (compute), Python (AI/CLI)
