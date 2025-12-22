# Pangea Net Desktop Application

## Overview

The Pangea Net Desktop Application is a standalone GUI application that provides complete access to all Pangea Net functionality **without requiring command-line interaction or a web browser**.

This application replaces the browser-based demo and provides direct Cap'n Proto RPC connectivity to the Go node for real-time network operations. It is built using **Kivy and KivyMD**, offering a modern, touch-friendly interface.

## Features

### ✅ Complete CLI Integration
All Python CLI commands are accessible through the GUI:
- Node management and discovery
- Compute task submission and monitoring
- File upload/download (Receptors)
- Communication liveness testing
- Network topology visualization
- Health status monitoring

### ✅ DCDN Integration
- **DCDN Demo**: Run the Decentralized Content Delivery Network demo directly from the GUI.
- **DCDN Info**: View system information and status for the DCDN components.
- **Container Tests**: Run isolated DCDN tests in Docker/Podman containers.

### ✅ Direct Cap'n Proto Connectivity
- Native RPC connection to Go nodes (no HTTP)
- Real-time data from actual network operations
- Full multiaddr support for peer connections
- No fake/simulated metrics

### ✅ Modern Desktop Experience
- Native window application (not browser-based)
- Cross-platform (Linux, macOS, Windows)
- Material Design interface (KivyMD)
- No web server required
- Runs entirely locally

## Installation

### Prerequisites

1. **Python 3.8 or higher**
   ```bash
   python3 --version
   ```

2. **System Dependencies (SDL2 & GStreamer)**
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
       libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good
   ```

   **macOS:**
   ```bash
   brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf gstreamer
   ```

3. **Python dependencies**
   ```bash
   cd python
   pip install -r requirements.txt
   # Ensure Kivy and KivyMD are installed
   pip install "kivy>=2.2.0" "kivymd>=1.1.1"
   ```

4. **Cap'n Proto compiler**
   ```bash
   # macOS
   brew install capnproto
   
   # Linux
   sudo apt-get install capnproto
   ```

### Build Go Node (Required)

The desktop app connects to a running Go node:

```bash
cd go
go build -o bin/go-node .
```

## Usage

### Quick Start

1. **Start a Go node** (in a separate terminal):
   ```bash
   ./go/bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local
   ```

2. **Launch the desktop app**:
   ```bash
   python3 desktop/desktop_app_kivy.py
   ```

3. **Connect to the node**:
   - Host: `localhost`
   - Port: `8080`
   - Click **Connect**

4. **Use the features**:
   - Navigate through tabs for different operations
   - All actions are point-and-click
   - Results appear in real-time

### Tabs and Features

#### 1. Node Management
- **List All Nodes**: Shows all nodes in the network
- **Get Node Info**: Displays current node details
- **Health Status**: Shows health metrics for all nodes

#### 2. Compute Tasks
- **Submit Compute Task**: Send computation tasks to workers
- **List Workers**: View available compute workers
- **Check Task Status**: Monitor running tasks

#### 3. DCDN & Streaming
- **DCDN Info**: View DCDN system status
- **Run Demo**: Execute the DCDN streaming demo
- **Container Tests**: Run isolated tests

#### 4. File Operations (Receptors)
- **Upload File**: Browse and upload files to the network
- **Download File**: Download files by hash
- **List Available Files**: View all files in the network

#### 5. Communications
- **Test P2P Connection**: Verify peer-to-peer connectivity
- **Ping All Nodes**: Check liveness of all nodes
- **Check Network Health**: Overall network status

## Architecture

```
┌─────────────────────────────────────────┐
│       Desktop Application (GUI)         │
│         (Kivy/KivyMD)                   │
└──────────────┬──────────────────────────┘
               │ Cap'n Proto RPC
               ↓
┌──────────────────────────────────────────┐
│          Go Node (libp2p)                │
│     - P2P Networking                     │
│     - Compute Management                 │
│     - File Storage                       │
└──────────────┬───────────────────────────┘
               │ libp2p (multiaddr)
               ↓
┌──────────────────────────────────────────┐
│      Distributed Network                 │
│   (Workers, Storage, Communication)      │
└──────────────────────────────────────────┘
```

### Key Design Principles

1. **No Browser Required**: Native desktop application
2. **Direct RPC**: Cap'n Proto for efficient communication
3. **Real Data Only**: No fake metrics or simulated data
4. **CLI Parity**: All CLI operations available in GUI
5. **Multiaddr Native**: Full support for libp2p addressing

## Configuration

### Environment Variables

```bash
# Go node connection
export GO_NODE_HOST=localhost
export GO_NODE_PORT=8080

# Logging level
export LOG_LEVEL=INFO
```

## Comparison: Desktop App vs Browser Demo

| Feature | Browser Demo | Desktop App |
|---------|--------------|-------------|
| **Interface** | Web browser | Native window (Kivy) |
| **Connection** | HTTP/WebSocket | Cap'n Proto RPC |
| **Data** | Simulated/fake | Real from network |
| **Metrics** | Fake stats | Actual network data |
| **CLI Access** | Limited | Complete |
| **Dependencies** | FastAPI, uvicorn | Kivy, KivyMD, SDL2 |
| **Installation** | `pip install fastapi uvicorn` | Python + System libs |
| **Startup** | `./setup.sh --demo` | `python3 desktop/desktop_app_kivy.py` |

## Development

### Adding New Features

1. **Add a new tab** in the KV string or Python builder
2. **Add button handlers** for the operation
3. **Implement RPC call** using `self.go_client`
4. **Display results** in the tab's output area

### Troubleshooting

### "Cap'n Proto client not available"
```bash
cd python
pip install pycapnp
```

### "Failed to connect to node"
1. Verify Go node is running: `ps aux | grep go-node`
2. Check port is correct: `lsof -i :8080`
3. Check firewall settings
4. Try explicit IP: `127.0.0.1` instead of `localhost`

### "ModuleNotFoundError: No module named 'kivy'"
```bash
pip install kivy kivymd
```

### GUI doesn't respond
- Check system log (bottom panel) for errors
- Restart the application
- Verify Go node is responsive: `curl localhost:8080` (should timeout, not refuse)

## Security Considerations

⚠️ **This application is for development and demonstration purposes.**

For production use:
- Add authentication/authorization
- Encrypt sensitive data
- Validate all inputs
- Implement rate limiting
- Add audit logging
- Use secure storage for credentials

## Contributing

To contribute improvements to the desktop app:

1. Test your changes thoroughly
2. Follow Python coding standards (PEP 8)
3. Add docstrings to all functions
4. Update this README with new features
5. Submit a pull request

## License

Same license as the main Pangea Net project.

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Review [PORT_CONFIGURATION.md](PORT_CONFIGURATION.md) for port setup
- See [NETWORK_CONNECTION.md](docs/NETWORK_CONNECTION.md) for connectivity

---

**Last Updated**: 2025-12-07  
**Version**: 0.6.0-alpha
