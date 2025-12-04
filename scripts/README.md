# Scripts Directory

**Last Updated:** 2025-12-04

Scripts for setup, testing, and development of Pangea Net.

## Quick Reference

| Script | Category | Purpose |
|--------|----------|---------|
| `setup.sh` | Setup | Interactive setup menu with all options |
| `verify_setup.sh` | Setup | Verify installation |
| `cross_device_setup.sh` | Setup | Cross-device setup |
| `download_test_media.sh` | Setup | Download test media |
| `live_test.sh` | Testing | Live P2P testing (chat/voice/video) |
| `run-tests.sh` | Testing | Run all tests |
| `test_pangea.sh` | Testing | Comprehensive P2P test |
| `easy_test.sh` | Testing | Quick test for single device |
| `test_automated.sh` | Testing | Automated testing |
| `test_10_nodes.sh` | Testing | 10-node testing |
| `test_mdns.sh` | Testing | mDNS discovery test |
| `cross_device_streaming_test.sh` | Testing | Cross-device streaming |
| `dev.sh` | Development | Development helper |
| `export_docs.sh` | Development | Export documentation |

## Script Categories

### Setup & Installation

- **`setup.sh`** - Main setup script with interactive menu
  - Install dependencies
  - Build all components
  - Run tests
  - View logs
  
- **`verify_setup.sh`** - Verify that all components are installed correctly
- **`cross_device_setup.sh`** - Setup for cross-device testing
- **`download_test_media.sh`** - Download test media files

### Live Testing

- **`live_test.sh`** - Interactive live P2P testing
  - Starts Go libp2p node
  - Provides menu for Chat, Voice, Video
  - Shows connection info (IP, port, peer ID) on one screen
  - Use on two devices to test real P2P communication

- **`easy_test.sh`** - Quick test for single device
- **`test_pangea.sh`** - Comprehensive P2P test with menu

### Automated Testing

- **`run-tests.sh`** - Run the full test suite
- **`test_automated.sh`** - Automated testing
- **`test_10_nodes.sh`** - Test with 10 nodes
- **`test_mdns.sh`** - Test mDNS discovery
- **`cross_device_streaming_test.sh`** - Test streaming between devices

### Development

- **`dev.sh`** - Development helper script
- **`export_docs.sh`** - Export documentation

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
- Python files in `python/src/communication/` are deprecated reference implementations
- Tests follow the Golden Rule: Go (networking), Rust (compute), Python (AI/CLI)
