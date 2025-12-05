"""
Matrix Utilities for Distributed Matrix Multiplication

This module provides reusable matrix functions for the CLI and distributed
compute system. It wraps the existing functionality from distributed_matrix_multiply.py.

Usage:
    from src.matrix_utils import (
        serialize_matrix, deserialize_matrix, 
        matrix_multiply_block, generate_random_matrix,
        load_matrix_file, save_matrix_file
    )
"""

import struct
import json
import random
from pathlib import Path
from typing import List, Tuple, Optional

# Try to import numpy, but provide fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ============================================================
# Matrix Serialization
# ============================================================

def serialize_matrix(matrix: list, rows: int, cols: int) -> bytes:
    """Serialize a 2D matrix to bytes.
    
    Format: [rows:4][cols:4][data:rows*cols*8]
    Each element is a float64 (8 bytes)
    
    Args:
        matrix: 2D list of floats
        rows: Number of rows
        cols: Number of columns
        
    Returns:
        Serialized bytes
    """
    header = struct.pack('>II', rows, cols)  # big-endian unsigned ints
    data = b''
    for row in matrix:
        for val in row:
            data += struct.pack('>d', float(val))  # big-endian double
    return header + data


def deserialize_matrix(data: bytes) -> Tuple[list, int, int]:
    """Deserialize bytes back to a 2D matrix.
    
    Args:
        data: Serialized matrix bytes
        
    Returns:
        Tuple of (matrix, rows, cols)
    """
    rows, cols = struct.unpack('>II', data[:8])
    matrix = []
    offset = 8
    for i in range(rows):
        row = []
        for j in range(cols):
            val = struct.unpack('>d', data[offset:offset+8])[0]
            row.append(val)
            offset += 8
        matrix.append(row)
    return matrix, rows, cols


# ============================================================
# Matrix Operations
# ============================================================

def matrix_multiply_block(a: list, b: list) -> list:
    """Multiply two matrices (block multiplication).
    
    A: m x k matrix
    B: k x n matrix
    Result: m x n matrix
    
    Args:
        a: First matrix
        b: Second matrix
        
    Returns:
        Result matrix
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


def add_matrices(a: list, b: list) -> list:
    """Add two matrices element-wise.
    
    Args:
        a: First matrix
        b: Second matrix
        
    Returns:
        Sum matrix
    """
    rows = len(a)
    cols = len(a[0]) if rows > 0 else 0
    return [[a[i][j] + b[i][j] for j in range(cols)] for i in range(rows)]


def generate_random_matrix(rows: int, cols: int, seed: Optional[int] = None) -> list:
    """Generate a random matrix.
    
    Args:
        rows: Number of rows
        cols: Number of columns
        seed: Random seed for reproducibility
        
    Returns:
        Random matrix as 2D list
    """
    if seed is not None:
        random.seed(seed)
    
    return [[random.uniform(-10, 10) for _ in range(cols)] for _ in range(rows)]


def matrix_to_string(matrix: list, max_display: int = 5) -> str:
    """Pretty print a matrix (truncated for large matrices).
    
    Args:
        matrix: 2D list matrix
        max_display: Maximum rows/cols to display
        
    Returns:
        Formatted string representation
    """
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
# File Operations
# ============================================================

def load_matrix_file(filepath: str) -> list:
    """Load a matrix from file (JSON, NumPy, or CSV format).
    
    Args:
        filepath: Path to matrix file
        
    Returns:
        Matrix as 2D list
    """
    path = Path(filepath)
    
    if path.suffix == '.json':
        with open(path, 'r') as f:
            return json.load(f)
    elif path.suffix == '.npy' and HAS_NUMPY:
        arr = np.load(path)
        return arr.tolist()
    elif path.suffix == '.csv':
        matrix = []
        with open(path, 'r') as f:
            for line in f:
                row = [float(x.strip()) for x in line.split(',') if x.strip()]
                if row:
                    matrix.append(row)
        return matrix
    else:
        # Try JSON format
        with open(path, 'r') as f:
            return json.load(f)


def save_matrix_file(filepath: str, matrix: list):
    """Save a matrix to file.
    
    Args:
        filepath: Path to save to
        matrix: Matrix to save
    """
    path = Path(filepath)
    
    if path.suffix == '.json':
        with open(path, 'w') as f:
            json.dump(matrix, f, indent=2)
    elif path.suffix == '.npy' and HAS_NUMPY:
        np.save(path, np.array(matrix))
    elif path.suffix == '.csv':
        with open(path, 'w') as f:
            for row in matrix:
                f.write(','.join(str(x) for x in row) + '\n')
    else:
        with open(path, 'w') as f:
            json.dump(matrix, f, indent=2)


# ============================================================
# Verification
# ============================================================

def verify_with_numpy(result: list, matrix_a: list, matrix_b: list, rtol: float = 1e-5) -> Tuple[bool, Optional[float]]:
    """Verify matrix multiplication result using NumPy.
    
    Args:
        result: Computed result matrix
        matrix_a: First input matrix
        matrix_b: Second input matrix
        rtol: Relative tolerance for comparison
        
    Returns:
        Tuple of (matches, max_difference)
    """
    if not HAS_NUMPY:
        return True, None  # Can't verify without numpy
    
    a = np.array(matrix_a)
    b = np.array(matrix_b)
    expected = np.matmul(a, b)
    result_np = np.array(result)
    
    matches = np.allclose(result_np, expected, rtol=rtol)
    max_diff = float(np.abs(result_np - expected).max())
    
    return matches, max_diff


def has_numpy() -> bool:
    """Check if NumPy is available.
    
    Returns:
        True if NumPy is installed
    """
    return HAS_NUMPY
