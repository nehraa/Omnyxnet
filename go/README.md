# Pangea Net - Go Node

**Version:** 0.3.0-alpha  
**Status:** Alpha - Local Testing  
**Last Updated:** 2025-11-22

> ⚠️ **Development Status:** Working for local P2P networking and testing. Not ready for production deployment.

Go component that handles P2P networking with Noise Protocol encryption.

## Features

- ✅ Noise Protocol XX handshake (encrypted P2P)
- ✅ Single port for all connections
- ✅ Automatic ping/pong (latency measurement)
- ✅ Connection quality metrics
- ✅ Cap'n Proto RPC for Python
- ✅ Port cleanup and error handling

## Building

```bash
# Generate Cap'n Proto code
export PATH=$PATH:$(go env GOPATH)/bin
capnp compile -I$(go list -f '{{.Dir}}' capnproto.org/go/capnp/v3/std) -ogo schema/schema.capnp

# Build
go build -o bin/go-node .

# Or use Makefile
make build
```

## Running

```bash
# Basic
./bin/go-node -node-id=1

# Custom ports
./bin/go-node -node-id=1 -capnp-addr=:8080 -p2p-addr=:9090

# With peers
./bin/go-node -node-id=2 -peers="1:localhost:9090"
```

## Command Line Options

- `-node-id`: Node identifier (default: 1)
- `-capnp-addr`: Cap'n Proto RPC address (default: :8080)
- `-p2p-addr`: P2P listener address (default: :9090)
- `-peers`: Comma-separated peer addresses (format: id:host:port)

## Architecture

- **Port 8080**: Cap'n Proto RPC (Python connects here)
- **Port 9090**: P2P Network (other Go nodes connect here)
- **Noise Protocol**: All P2P traffic encrypted
- **Ping/Pong**: Automatic every 5 seconds

## Testing

```bash
./tests/test_go.sh
```

