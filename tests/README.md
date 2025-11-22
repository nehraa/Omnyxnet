# Test Scripts

**Version:** 0.3.0-alpha  
**Last Updated:** 2025-11-22

> 📋 These test scripts validate local functionality. For comprehensive test status, see [../VERSION.md](../VERSION.md).

Test scripts for Go, Rust, and Python components.

## Running Tests

### Path Resolution Tests
```bash
./tests/test_paths.sh
```

Tests that all paths work correctly from any directory:
- From project root
- From python/ directory
- From go/ directory
- From tests/ directory
- Schema file location

### Go Tests
```bash
./tests/test_go.sh
```

Tests:
- Build compilation
- Binary creation
- Help command
- Port availability
- Schema file existence

**Note**: Uses absolute paths, works from any directory.

### Python Tests
```bash
./tests/test_python.sh
```

Tests:
- Python version check
- Dependencies check
- Module structure
- Syntax validation
- CLI functionality
- PyTorch availability

**Note**: Uses absolute paths, works from any directory.

### Full Integration Test
```bash
./tests/test_integration.sh
```

**Full system test with Go + Python connectivity**:
1. Builds Go node
2. Starts Go node on localhost:8080
3. Tests Python connecting via Cap'n Proto RPC
4. Tests all RPC methods:
   - getAllNodes()
   - getNode()
   - updateThreatScore()
   - getConnectedPeers()
   - getConnectionQuality()
   - sendMessage()
5. Cleans up automatically

**Note**: Uses absolute paths, works from any directory.

## Manual Testing

### Test Go Node
```bash
cd go
go build -o bin/go-node .
./bin/go-node -node-id=1 -capnp-addr=:8080 -p2p-addr=:9090
```

### Test Python Client
```bash
cd python
python3 main.py connect
python3 main.py list-nodes
```

**Note**: Python automatically finds schema.capnp using absolute paths.

## Path Resolution

All scripts and Python code use **absolute paths**:
- Python uses `utils.paths` module to find project root
- Test scripts calculate absolute paths from script location
- Schema paths are automatically resolved
- Works from any directory

## Integration Testing

1. Start Go node:
```bash
cd go
./bin/go-node -node-id=1
```

2. In another terminal, test Python (from any directory):
```bash
# Works from project root
python3 python/main.py connect

# Or from python directory
cd python
python3 main.py connect
python3 main.py list-nodes
python3 main.py predict
```

