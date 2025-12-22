#!/usr/bin/env python3
"""
Distributed Matrix Multiplication Example

This example demonstrates how to perform matrix multiplication across
multiple nodes using the Pangea Net distributed compute system.

The algorithm uses block matrix multiplication:
1. SPLIT: Divide matrices into blocks that can be processed independently
2. EXECUTE: Multiply corresponding blocks on different nodes
3. MERGE: Combine block results into the final matrix

Usage:
    # Generate input file and run locally
    python distributed_matrix_multiply.py --size 100 --generate

    # Run with existing file
    python distributed_matrix_multiply.py --file matrix_a.npy --file-b matrix_b.npy

    # Connect to distributed network
    python distributed_matrix_multiply.py --file matrix_a.npy --connect --host 192.168.1.100
"""

import sys
import json
import struct
import argparse
import time
from pathlib import Path
from typing import List, Tuple

# Add parent directories for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.compute import Job, ComputeClient

# Try to import numpy, but provide fallback
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ============================================================
# Matrix Serialization (works without numpy too)
# ============================================================


def serialize_matrix(matrix: list, rows: int, cols: int) -> bytes:
    """Serialize a 2D matrix to bytes.

    Format: [rows:4][cols:4][data:rows*cols*8]
    Each element is a float64 (8 bytes)
    """
    header = struct.pack(">II", rows, cols)  # big-endian unsigned ints
    data = b""
    for row in matrix:
        for val in row:
            data += struct.pack(">d", float(val))  # big-endian double
    return header + data


def deserialize_matrix(data: bytes) -> Tuple[list, int, int]:
    """Deserialize bytes back to a 2D matrix.

    Returns: (matrix, rows, cols)
    """
    rows, cols = struct.unpack(">II", data[:8])
    matrix = []
    offset = 8
    for i in range(rows):
        row = []
        for j in range(cols):
            val = struct.unpack(">d", data[offset : offset + 8])[0]
            row.append(val)
            offset += 8
        matrix.append(row)
    return matrix, rows, cols


def matrix_to_string(matrix: list, max_display: int = 5) -> str:
    """Pretty print a matrix (truncated for large matrices)."""
    rows = len(matrix)
    cols = len(matrix[0]) if rows > 0 else 0

    lines = [f"Matrix {rows}x{cols}:"]

    display_rows = min(rows, max_display)
    display_cols = min(cols, max_display)

    for i in range(display_rows):
        row_str = "  ["
        for j in range(display_cols):
            row_str += f"{matrix[i][j]:8.2f}"
        if cols > max_display:
            row_str += " ..."
        row_str += " ]"
        lines.append(row_str)

    if rows > max_display:
        lines.append("  ...")

    return "\n".join(lines)


# ============================================================
# Matrix Operations (pure Python, no numpy required)
# ============================================================


def matrix_multiply_block(a: list, b: list) -> list:
    """Multiply two matrices (block multiplication).

    A: m x k matrix
    B: k x n matrix
    Result: m x n matrix
    """
    m = len(a)
    k = len(a[0]) if m > 0 else 0
    n = len(b[0]) if len(b) > 0 else 0

    # Initialize result matrix with zeros
    result = [[0.0 for _ in range(n)] for _ in range(m)]

    # Standard matrix multiplication
    for i in range(m):
        for j in range(n):
            for p in range(k):
                result[i][j] += a[i][p] * b[p][j]

    return result


def generate_random_matrix(rows: int, cols: int, seed: int = None) -> list:
    """Generate a random matrix."""
    import random

    if seed is not None:
        random.seed(seed)

    return [[random.uniform(-10, 10) for _ in range(cols)] for _ in range(rows)]


def add_matrices(a: list, b: list) -> list:
    """Add two matrices element-wise."""
    rows = len(a)
    cols = len(a[0]) if rows > 0 else 0
    return [[a[i][j] + b[i][j] for j in range(cols)] for i in range(rows)]


# ============================================================
# Distributed Matrix Multiplication Job Definition
# ============================================================


@Job.define
def distributed_matrix_multiply():
    """
    Distributed matrix multiplication using block decomposition.

    The input is serialized as:
    [4 bytes: num_blocks][block_data...]

    Each block contains:
    [4 bytes: block_row][4 bytes: block_col][matrix_a_block][matrix_b_block]
    """

    @Job.split
    def split(data: bytes) -> List[bytes]:
        """Split matrices into blocks for parallel processing.

        Input format: [matrix_a][matrix_b] (both serialized)
        Output: List of block pairs to multiply
        """
        # Find where matrix A ends (read its dimensions)
        a_rows, a_cols = struct.unpack(">II", data[:8])
        a_size = 8 + a_rows * a_cols * 8

        matrix_a_data = data[:a_size]
        matrix_b_data = data[a_size:]

        # Deserialize matrices
        matrix_a, a_rows, a_cols = deserialize_matrix(matrix_a_data)
        matrix_b, b_rows, b_cols = deserialize_matrix(matrix_b_data)

        # Determine block size (aim for ~4 blocks per dimension)
        block_rows = max(1, a_rows // 4)
        block_cols = max(1, b_cols // 4)
        block_k = max(1, a_cols // 4)

        chunks = []

        # Create block pairs for multiplication
        for i in range(0, a_rows, block_rows):
            for j in range(0, b_cols, block_cols):
                # For each output block (i,j), we need to sum over k
                for k in range(0, a_cols, block_k):
                    # Extract block from A: rows [i:i+block_rows], cols [k:k+block_k]
                    a_block = []
                    for row in range(i, min(i + block_rows, a_rows)):
                        a_row = []
                        for col in range(k, min(k + block_k, a_cols)):
                            a_row.append(matrix_a[row][col])
                        a_block.append(a_row)

                    # Extract block from B: rows [k:k+block_k], cols [j:j+block_cols]
                    b_block = []
                    for row in range(k, min(k + block_k, b_rows)):
                        b_row = []
                        for col in range(j, min(j + block_cols, b_cols)):
                            b_row.append(matrix_b[row][col])
                        b_block.append(b_row)

                    # Serialize block pair with position info
                    b_block_cols = (
                        len(b_block[0])
                        if b_block and len(b_block) > 0 and len(b_block[0]) > 0
                        else 0
                    )
                    chunk = struct.pack(">IIII", i, j, len(a_block), b_block_cols)
                    a_block_cols = (
                        len(a_block[0]) if a_block and len(a_block) > 0 else 0
                    )
                    chunk += serialize_matrix(a_block, len(a_block), a_block_cols)
                    chunk += serialize_matrix(b_block, len(b_block), b_block_cols)
                    chunks.append(chunk)

        print(f"  📊 Split into {len(chunks)} block multiplications")
        return chunks

    @Job.execute
    def execute(chunk: bytes) -> bytes:
        """Execute block matrix multiplication.

        Each worker receives a pair of blocks and returns the product.
        """
        # Parse position info
        i, j, a_rows, b_cols = struct.unpack(">IIII", chunk[:16])

        # Parse block A
        offset = 16
        block_a_header = chunk[offset : offset + 8]
        ba_rows, ba_cols = struct.unpack(">II", block_a_header)
        ba_size = 8 + ba_rows * ba_cols * 8
        block_a, _, _ = deserialize_matrix(chunk[offset : offset + ba_size])
        offset += ba_size

        # Parse block B
        block_b, _, _ = deserialize_matrix(chunk[offset:])

        # Multiply blocks
        result_block = matrix_multiply_block(block_a, block_b)

        # Serialize result with position
        result = struct.pack(">II", i, j)
        result += serialize_matrix(
            result_block, len(result_block), len(result_block[0]) if result_block else 0
        )

        print(
            f"    🔢 Computed block ({i},{j}): {len(block_a)}x{len(block_a[0])} * {len(block_b)}x{len(block_b[0])}"
        )
        return result

    @Job.merge
    def merge(results: List[bytes]) -> bytes:
        """Merge block results into final matrix.

        Sum blocks that contribute to the same output position.
        """
        # First pass: determine output matrix dimensions
        blocks = {}
        max_i = 0
        max_j = 0

        for result in results:
            i, j = struct.unpack(">II", result[:8])
            matrix, rows, cols = deserialize_matrix(result[8:])

            key = (i, j)
            if key in blocks:
                # Add to existing block
                blocks[key] = add_matrices(blocks[key], matrix)
            else:
                blocks[key] = matrix

            max_i = max(max_i, i + rows)
            max_j = max(max_j, j + cols)

        # Assemble final matrix
        final_matrix = [[0.0 for _ in range(max_j)] for _ in range(max_i)]

        for (i, j), block in blocks.items():
            for bi, row in enumerate(block):
                for bj, val in enumerate(row):
                    if i + bi < max_i and j + bj < max_j:
                        final_matrix[i + bi][j + bj] = val

        print(f"  ✅ Merged into {max_i}x{max_j} result matrix")
        return serialize_matrix(final_matrix, max_i, max_j)


# ============================================================
# File-based Compute Interface
# ============================================================


def compute_from_file(
    file_a: str,
    file_b: str = None,
    output_file: str = None,
    host: str = "localhost",
    port: int = 8080,
    connect: bool = False,
) -> list:
    """
    Perform distributed matrix multiplication from files.

    Args:
        file_a: Path to first matrix file (JSON or .npy)
        file_b: Path to second matrix file (optional, uses transpose of A if not provided)
        output_file: Path to save result (optional)
        host: Compute node host
        port: Compute node port
        connect: Whether to connect to remote node

    Returns:
        Result matrix as 2D list
    """
    print("=" * 60)
    print("🧮 DISTRIBUTED MATRIX MULTIPLICATION")
    print("=" * 60)

    # Load matrices
    print(f"\n📂 Loading matrix A from: {file_a}")
    matrix_a = load_matrix_file(file_a)
    a_rows, a_cols = len(matrix_a), len(matrix_a[0])
    print(f"   Dimensions: {a_rows} x {a_cols}")

    if file_b:
        print(f"📂 Loading matrix B from: {file_b}")
        matrix_b = load_matrix_file(file_b)
    else:
        print("📂 Using transpose of A as matrix B")
        matrix_b = [[matrix_a[j][i] for j in range(a_rows)] for i in range(a_cols)]

    b_rows, b_cols = len(matrix_b), len(matrix_b[0])
    print(f"   Dimensions: {b_rows} x {b_cols}")

    # Verify dimensions are compatible
    if a_cols != b_rows:
        raise ValueError(
            f"Matrix dimensions incompatible: {a_rows}x{a_cols} * {b_rows}x{b_cols}"
        )

    print(f"\n📊 Expected result dimensions: {a_rows} x {b_cols}")

    # Serialize input
    input_data = serialize_matrix(matrix_a, a_rows, a_cols)
    input_data += serialize_matrix(matrix_b, b_rows, b_cols)
    print(f"📦 Serialized input: {len(input_data)} bytes")

    # Get job definition
    job = distributed_matrix_multiply

    # Execute
    execution_mode = None  # Track whether we executed remotely or locally

    if connect:
        print(f"\n🌐 Connecting to compute node at {host}:{port}...")
        client = ComputeClient(host, port)
        connection_successful = client.connect()

        if not connection_successful:
            print(f"❌ Failed to connect to remote node at {host}:{port}")
            print("⚠️  FALLING BACK TO LOCAL EXECUTION")
            connect = False
        else:
            print("✅ Successfully connected to remote node")

    start_time = time.time()

    if connect:
        execution_mode = "REMOTE"
        print("\n⚡ Submitting job to DISTRIBUTED NETWORK...")
        print(f"   Target: {host}:{port}")
        worker_node = None
        try:
            job_id = client.submit_job(job, input_data)
            print("   ✅ Job submitted successfully")
            print(f"   Job ID: {job_id}")

            # Wait for result
            print("   Waiting for remote execution...")
            result_data, worker_node = client.get_result(job_id)
            print("   ✅ Result received from remote node")
            client.disconnect()
        except Exception as e:
            print(f"❌ Remote execution failed: {e}")
            print("⚠️  FALLING BACK TO LOCAL EXECUTION")
            execution_mode = None
            connect = False

    if not connect:
        execution_mode = "LOCAL"
        print("\n⚡ Running computation LOCALLY on this machine...")
        print("\n--- SPLIT Phase ---")
        chunks = job.split(input_data)

        print(f"\n--- EXECUTE Phase ({len(chunks)} blocks) ---")
        results = []
        for i, chunk in enumerate(chunks):
            result = job.execute(chunk)
            results.append(result)

        print("\n--- MERGE Phase ---")
        result_data = job.merge(results)

    elapsed = time.time() - start_time

    # Deserialize result
    result_matrix, r_rows, r_cols = deserialize_matrix(result_data)

    print(f"\n{'=' * 60}")
    print("✅ COMPUTATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"   Result dimensions: {r_rows} x {r_cols}")
    print(f"   Computation time: {elapsed:.3f} seconds")
    print(f"   Result size: {len(result_data)} bytes")

    # Show execution mode used
    if execution_mode == "REMOTE":
        print("   🌐 Execution Mode: REMOTE (distributed)")
        if worker_node and worker_node != "local":
            print(f"      Executed by Worker: {worker_node}")
        else:
            print(f"      Connected via: {host}:{port}")
    elif execution_mode == "LOCAL":
        print("   💻 Execution Mode: LOCAL (this machine)")

    # Save result if requested
    if output_file:
        save_matrix_file(output_file, result_matrix)
        print(f"   Saved to: {output_file}")

    # Show preview
    print(f"\n{matrix_to_string(result_matrix)}")

    return result_matrix


def load_matrix_file(filepath: str) -> list:
    """Load a matrix from file (JSON or NumPy format)."""
    path = Path(filepath)

    if path.suffix == ".json":
        with open(path, "r") as f:
            return json.load(f)
    elif path.suffix == ".npy" and HAS_NUMPY:
        arr = np.load(path)
        return arr.tolist()
    elif path.suffix == ".csv":
        matrix = []
        with open(path, "r") as f:
            for line in f:
                row = [float(x.strip()) for x in line.split(",") if x.strip()]
                if row:
                    matrix.append(row)
        return matrix
    else:
        # Try JSON format
        with open(path, "r") as f:
            return json.load(f)


def save_matrix_file(filepath: str, matrix: list):
    """Save a matrix to file."""
    path = Path(filepath)

    if path.suffix == ".json":
        with open(path, "w") as f:
            json.dump(matrix, f, indent=2)
    elif path.suffix == ".npy" and HAS_NUMPY:
        np.save(path, np.array(matrix))
    elif path.suffix == ".csv":
        with open(path, "w") as f:
            for row in matrix:
                f.write(",".join(str(x) for x in row) + "\n")
    else:
        with open(path, "w") as f:
            json.dump(matrix, f, indent=2)


# ============================================================
# Main Entry Point
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="Distributed Matrix Multiplication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate test matrices and compute locally
  python distributed_matrix_multiply.py --size 50 --generate
  
  # Use existing files
  python distributed_matrix_multiply.py --file matrix_a.json --file-b matrix_b.json
  
  # Connect to distributed network
  python distributed_matrix_multiply.py --file matrix.json --connect --host 192.168.1.100
        """,
    )

    parser.add_argument("--file", "-f", type=str, help="Path to matrix A file")
    parser.add_argument("--file-b", type=str, help="Path to matrix B file (optional)")
    parser.add_argument("--output", "-o", type=str, help="Output file path")
    parser.add_argument(
        "--size", "-s", type=int, default=10, help="Matrix size for generation"
    )
    parser.add_argument(
        "--generate", "-g", action="store_true", help="Generate random matrices"
    )
    parser.add_argument(
        "--connect", "-c", action="store_true", help="Connect to remote node"
    )
    parser.add_argument(
        "--host", type=str, default="localhost", help="Remote node host"
    )
    parser.add_argument("--port", type=int, default=8080, help="Remote node port")
    parser.add_argument(
        "--verify", "-v", action="store_true", help="Verify result with numpy"
    )

    args = parser.parse_args()

    if args.generate:
        # Generate random matrices
        print(f"🎲 Generating {args.size}x{args.size} random matrices...")
        matrix_a = generate_random_matrix(args.size, args.size, seed=42)

        # Save to temp files
        file_a = "temp_matrix_a.json"
        file_b = "temp_matrix_b.json"

        # Generate second matrix (transpose for square multiplication)
        matrix_b = generate_random_matrix(args.size, args.size, seed=43)

        save_matrix_file(file_a, matrix_a)
        save_matrix_file(file_b, matrix_b)
        print(f"   Saved to {file_a} and {file_b}")

        args.file = file_a
        args.file_b = file_b

    if not args.file:
        # Demo mode with small matrices
        print("🎯 Running demo with small matrices...")

        # Create simple test matrices
        matrix_a = [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ]
        matrix_b = [
            [9, 8, 7],
            [6, 5, 4],
            [3, 2, 1],
        ]

        file_a = "demo_matrix_a.json"
        file_b = "demo_matrix_b.json"
        save_matrix_file(file_a, matrix_a)
        save_matrix_file(file_b, matrix_b)

        args.file = file_a
        args.file_b = file_b

    # Run computation
    result = compute_from_file(
        file_a=args.file,
        file_b=args.file_b,
        output_file=args.output,
        host=args.host,
        port=args.port,
        connect=args.connect,
    )

    # Verify with numpy if requested
    if args.verify and HAS_NUMPY:
        print("\n🔍 Verifying with NumPy...")
        a = np.array(load_matrix_file(args.file))
        b = np.array(load_matrix_file(args.file_b)) if args.file_b else a.T
        expected = np.matmul(a, b)

        result_np = np.array(result)

        if np.allclose(result_np, expected, rtol=1e-5):
            print("   ✅ Result matches NumPy computation!")
        else:
            print("   ❌ Result differs from NumPy!")
            diff = np.abs(result_np - expected).max()
            print(f"   Max difference: {diff}")


if __name__ == "__main__":
    main()
