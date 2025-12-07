# Desktop Application Setup Guide

## Overview

The Pangea Net Desktop Application provides a graphical user interface (GUI) for all CLI functionality without requiring command-line interaction. The application is built using **tkinter**, Python's standard GUI library.

## Requirements

### System Dependencies

The desktop application requires tkinter to be installed on your system:

#### Linux (Debian/Ubuntu)
```bash
sudo apt-get install python3-tk
```

#### macOS
```bash
brew install python-tk@3.11
```

#### Other Python Dependencies
All other dependencies are installed via the standard Python setup:
```bash
cd python
source .venv/bin/activate
pip install -r requirements.txt  # or requirements-minimal.txt
```

## Launching the Desktop App

### Method 1: Via Setup Script (Recommended)

The easiest way to launch the desktop app is through the main setup script:

```bash
./scripts/setup.sh
```

Then select option **22) Launch Desktop App (GUI Interface)**

The setup script will:
1. Check if tkinter is installed
2. Provide installation instructions if missing
3. Launch the desktop application

### Method 2: Direct Launch

You can also launch the desktop app directly:

```bash
python3 desktop_app.py
```

## Features

The desktop application provides:

- **Node Connection Management**: Connect to local or remote Go nodes via Cap'n Proto RPC
- **Compute Task Submission**: Submit and monitor distributed compute tasks
- **File Operations**: Upload and download files using the Receptor system
- **P2P Communications**: 
  - Chat messaging
  - Voice streaming
  - Video streaming
- **Network Monitoring**: View peers, topology, and connection statistics
- **System Logs**: Real-time log viewer with timestamps

## Auto-Startup Behavior

When the desktop app launches, it automatically:

1. Checks if a Go node is running on localhost:8080
2. If not found, attempts to build and start a Go node
3. Automatically connects to the node once ready
4. Runs health checks to verify functionality

## Troubleshooting

### tkinter Not Found

If you get a "ModuleNotFoundError: No module named 'tkinter'" error:

1. Install tkinter using the commands above for your platform
2. Restart your terminal/shell
3. Try launching again

### Go Node Connection Failed

If the desktop app cannot connect to the Go node:

1. Ensure the Go node binary is built:
   ```bash
   cd go && go build -o bin/go-node .
   ```

2. Manually start a Go node:
   ```bash
   cd go && ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local
   ```

3. Then launch the desktop app

### Cap'n Proto Client Not Available

If you see warnings about Cap'n Proto:

1. Ensure Python dependencies are installed:
   ```bash
   cd python
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Verify pycapnp is installed:
   ```bash
   python3 -c "import capnp; print('pycapnp available')"
   ```

## Architecture

The desktop application architecture:

```
Desktop App (tkinter) ←→ Cap'n Proto RPC ←→ Go Node ←→ libp2p Network
       │
       └─→ Python CLI Modules (compute, streaming, etc.)
```

- **UI Layer**: tkinter-based GUI with tabbed interface
- **RPC Layer**: Cap'n Proto client for Go node communication
- **Business Logic**: Reuses Python CLI modules where possible

## Notes

- **No Kivy/KivyMD**: The application uses Python's built-in tkinter library, not Kivy
- **Cross-platform**: Works on Linux, macOS, and Windows
- **Lightweight**: No heavy GUI framework dependencies
- **Integrated**: Uses the same RPC interface as the Python CLI

## Related Documentation

- [Desktop App Source Code](desktop_app.py)
- [Python CLI Documentation](python/src/cli.py)
- [Setup Script](scripts/setup.sh)
- [DCDN Setup Guide](DCDN_SETUP.md)
