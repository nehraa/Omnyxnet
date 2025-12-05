# Matrix Multiply CLI Reference

The `pangea compute matrix-multiply` command performs distributed matrix multiplication across the WGT network. It supports local execution, file-based input, random matrix generation, and NumPy verification.

## Quick Start

```bash
# Activate Python environment
cd python && source .venv/bin/activate

# Generate and multiply random 10x10 matrices
python main.py compute matrix-multiply --size 10 --generate

# With NumPy verification
python main.py compute matrix-multiply --size 10 --generate --verify

# Save result to file
python main.py compute matrix-multiply --size 10 --generate --output result.json
```

## Command Syntax

```bash
python main.py compute matrix-multiply [OPTIONS]
```

## Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--host` | | TEXT | localhost | Go node host address |
| `--port` | | INT | 8080 | Go node RPC port |
| `--size` | `-s` | INT | 10 | Matrix size for generation (NxN) |
| `--file-a` | `-a` | PATH | | Path to matrix A file (JSON, CSV, or .npy) |
| `--file-b` | `-b` | PATH | | Path to matrix B file (optional, uses transpose of A if not provided) |
| `--output` | `-o` | PATH | | Output file path to save result |
| `--generate` | `-g` | FLAG | | Generate random matrices instead of using files |
| `--verify` | `-v` | FLAG | | Verify result with NumPy (requires numpy) |
| `--connect` | `-c` | FLAG | | Connect to remote node for distributed execution |
| `--peer-address` | | TEXT | | Manual peer multiaddr for mDNS bypass |

## Examples

### Local Random Matrices

Generate and multiply random matrices locally:

```bash
# Small 5x5 matrices
python main.py compute matrix-multiply --size 5 --generate

# Medium 50x50 matrices with verification
python main.py compute matrix-multiply --size 50 --generate --verify

# Large 100x100 matrices
python main.py compute matrix-multiply --size 100 --generate
```

### File-Based Input

Use existing matrix files:

```bash
# Both matrices from files
python main.py compute matrix-multiply \
    --file-a matrix_a.json \
    --file-b matrix_b.json

# Only matrix A (uses transpose for B)
python main.py compute matrix-multiply --file-a matrix_a.json

# Save result
python main.py compute matrix-multiply \
    --file-a matrix_a.json \
    --file-b matrix_b.json \
    --output result.json
```

### Distributed Execution

Connect to the distributed network for parallel execution:

```bash
# With auto peer discovery (mDNS)
python main.py compute matrix-multiply \
    --size 100 --generate --connect

# Custom host/port
python main.py compute matrix-multiply \
    --size 100 --generate --connect \
    --host 192.168.1.100 --port 8080

# With manual peer address (bypass mDNS)
python main.py compute matrix-multiply \
    --size 100 --generate --connect \
    --peer-address /ip4/192.168.1.100/tcp/9081/p2p/QmXYZ...
```

## Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| JSON | `.json` | 2D array in JSON format |
| NumPy | `.npy` | NumPy binary format (requires numpy) |
| CSV | `.csv` | Comma-separated values |

### Example JSON Format

```json
[
  [1.0, 2.0, 3.0],
  [4.0, 5.0, 6.0],
  [7.0, 8.0, 9.0]
]
```

### Example CSV Format

```csv
1.0,2.0,3.0
4.0,5.0,6.0
7.0,8.0,9.0
```

## Output

The command displays:

1. **Matrix dimensions** - Size of input matrices
2. **Serialized size** - Bytes used for transmission
3. **Execution phases** - SPLIT, EXECUTE, MERGE stages
4. **Computation time** - Total execution time
5. **Execution mode** - LOCAL or REMOTE (distributed)
6. **Verification result** - NumPy comparison (if `--verify`)
7. **Result preview** - First 5x5 elements of result matrix

### Example Output

```
============================================================
🧮 DISTRIBUTED MATRIX MULTIPLICATION
============================================================

🎲 Generating 10x10 random matrices...
   Matrix A: 10x10
   Matrix B: 10x10

📊 Expected result dimensions: 10x10
📦 Serialized input: 1616 bytes

⚡ Running computation LOCALLY on this machine...

--- SPLIT Phase ---
   📊 Split into 125 block multiplications

--- EXECUTE Phase (125 blocks) ---
   🔢 Computed block 10/125
   ...

--- MERGE Phase ---
   ✅ Merged into final result matrix

============================================================
✅ COMPUTATION COMPLETE
============================================================
   Result dimensions: 10x10
   Computation time: 0.015 seconds
   Result size: 808 bytes
   💻 Execution Mode: LOCAL (this machine)

🔍 Verifying with NumPy...
   ✅ Result matches NumPy computation!

Matrix 10x10:
  [  -32.88  -51.09  -33.45   89.23   73.74 ... ]
  ...
```

## Algorithm

The implementation uses **block matrix multiplication**:

1. **SPLIT**: Divide both matrices into blocks (approximately 4x4 grid)
2. **EXECUTE**: Multiply corresponding block pairs in parallel
3. **MERGE**: Sum and combine block results into final matrix

This approach enables:
- Parallel execution across multiple workers
- Efficient memory usage for large matrices
- Verification through NumPy comparison

## Troubleshooting

### NumPy Not Available

```bash
# Install numpy for verification
pip install numpy
```

### Connection Failed

```bash
# Check if Go node is running
curl localhost:8080/health

# Start Go node first
cd go && ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true
```

### Matrix Dimension Mismatch

Ensure matrix dimensions are compatible for multiplication:
- Matrix A: m × k
- Matrix B: k × n
- Result: m × n

The number of columns in A must equal the number of rows in B.

## Related Commands

- `pangea compute submit` - Submit generic compute jobs
- `pangea compute status` - Check job status
- `pangea compute result` - Retrieve job results
- `pangea compute capacity` - Show node capacity

## See Also

- [NETWORK_CONNECTION.md](NETWORK_CONNECTION.md) - Network setup
- [DISTRIBUTED_COMPUTE_QUICK_START.md](DISTRIBUTED_COMPUTE_QUICK_START.md) - Quick start guide
- [CONTAINERIZED_TESTING.md](CONTAINERIZED_TESTING.md) - Testing in Docker
