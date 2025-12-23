"""
Data Preprocessing utilities for Distributed Compute

This module provides utilities for preparing data for distributed processing,
including chunking strategies and data encoding.
"""

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Iterator
import logging

logger = logging.getLogger(__name__)


class ChunkStrategy(Enum):
    """Strategies for splitting data into chunks."""

    FIXED_SIZE = "fixed_size"
    LINE_BASED = "line_based"
    RECORD_BASED = "record_based"
    ADAPTIVE = "adaptive"


@dataclass
class ChunkInfo:
    """Information about a data chunk."""

    index: int
    offset: int
    size: int
    hash: str


class DataPreprocessor:
    """Preprocessor for preparing data for distributed computation.

    This class provides methods for splitting data into chunks,
    encoding data for transmission, and calculating checksums.

    Example:
        preprocessor = DataPreprocessor(chunk_size=65536)
        chunks = preprocessor.split(large_data)
        for chunk in chunks:
            process(chunk)
    """

    def __init__(
        self,
        chunk_size: int = 65536,
        min_chunk_size: int = 1024,
        max_chunk_size: int = 1048576,
        strategy: ChunkStrategy = ChunkStrategy.FIXED_SIZE,
    ):
        """Initialize the preprocessor.

        Args:
            chunk_size: Target chunk size in bytes
            min_chunk_size: Minimum chunk size
            max_chunk_size: Maximum chunk size
            strategy: Chunking strategy
        """
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.strategy = strategy

    def split(self, data: bytes) -> List[bytes]:
        """Split data into chunks using the configured strategy.

        Args:
            data: Input data

        Returns:
            List of chunks
        """
        if self.strategy == ChunkStrategy.FIXED_SIZE:
            return self._split_fixed_size(data)
        elif self.strategy == ChunkStrategy.LINE_BASED:
            return self._split_line_based(data)
        elif self.strategy == ChunkStrategy.RECORD_BASED:
            return self._split_record_based(data)
        elif self.strategy == ChunkStrategy.ADAPTIVE:
            return self._split_adaptive(data)
        else:
            return self._split_fixed_size(data)

    def split_with_info(self, data: bytes) -> List[Tuple[bytes, ChunkInfo]]:
        """Split data and return chunk info.

        Args:
            data: Input data

        Returns:
            List of (chunk, info) tuples
        """
        chunks = self.split(data)
        result = []
        offset = 0

        for i, chunk in enumerate(chunks):
            info = ChunkInfo(
                index=i,
                offset=offset,
                size=len(chunk),
                hash=self.hash_chunk(chunk),
            )
            result.append((chunk, info))
            offset += len(chunk)

        return result

    def split_streaming(self, data: bytes) -> Iterator[bytes]:
        """Split data as a generator for memory efficiency.

        Args:
            data: Input data

        Yields:
            Chunks one at a time
        """
        for i in range(0, len(data), self.chunk_size):
            yield data[i : i + self.chunk_size]

    def _split_fixed_size(self, data: bytes) -> List[bytes]:
        """Split into fixed-size chunks."""
        return [
            data[i : i + self.chunk_size] for i in range(0, len(data), self.chunk_size)
        ]

    def _split_line_based(self, data: bytes) -> List[bytes]:
        """Split on newline boundaries, grouping lines to reach target chunk size."""
        lines = data.split(b"\n")
        chunks = []
        current_chunk = b""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > self.chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = line + b"\n"
            else:
                current_chunk += line + b"\n"

        if current_chunk:
            chunks.append(current_chunk.rstrip(b"\n"))

        return chunks

    def _split_record_based(
        self, data: bytes, delimiter: bytes = b"\n\n"
    ) -> List[bytes]:
        """Split on record delimiters (e.g., double newline)."""
        records = data.split(delimiter)
        chunks = []
        current_chunk = b""

        for record in records:
            if (
                len(current_chunk) + len(record) + len(delimiter) > self.chunk_size
                and current_chunk
            ):
                chunks.append(current_chunk)
                current_chunk = record
            else:
                if current_chunk:
                    current_chunk += delimiter + record
                else:
                    current_chunk = record

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_adaptive(self, data: bytes) -> List[bytes]:
        """Adaptively split based on data characteristics."""
        # Try to detect data format and choose appropriate strategy
        if b"\n" in data[:1024]:
            # Likely line-based text
            return self._split_line_based(data)
        else:
            # Binary or single-line - use fixed size
            return self._split_fixed_size(data)

    def merge(self, chunks: List[bytes]) -> bytes:
        """Merge chunks back into a single bytes object.

        Args:
            chunks: List of chunks

        Returns:
            Merged data
        """
        return b"".join(chunks)

    def hash_chunk(self, chunk: bytes) -> str:
        """Calculate SHA256 hash of a chunk.

        Args:
            chunk: Data chunk

        Returns:
            Hex-encoded hash
        """
        return hashlib.sha256(chunk).hexdigest()

    def hash_data(self, data: bytes) -> str:
        """Calculate SHA256 hash of data.

        Args:
            data: Input data

        Returns:
            Hex-encoded hash
        """
        return hashlib.sha256(data).hexdigest()

    def verify_integrity(self, chunks: List[bytes], expected_hash: str) -> bool:
        """Verify that chunks reassemble to expected data.

        Args:
            chunks: List of chunks
            expected_hash: Expected hash of merged data

        Returns:
            True if integrity check passes
        """
        merged = self.merge(chunks)
        actual_hash = self.hash_data(merged)
        return actual_hash == expected_hash

    def estimate_chunks(self, data_size: int) -> int:
        """Estimate the number of chunks for given data size.

        Args:
            data_size: Size of data in bytes

        Returns:
            Estimated number of chunks
        """
        return max(1, (data_size + self.chunk_size - 1) // self.chunk_size)

    def optimize_chunk_size(self, data_size: int, target_chunks: int = 8) -> int:
        """Calculate optimal chunk size for target number of chunks.

        Args:
            data_size: Size of data in bytes
            target_chunks: Target number of chunks

        Returns:
            Optimal chunk size
        """
        optimal = data_size // target_chunks
        return max(self.min_chunk_size, min(optimal, self.max_chunk_size))


# Utility functions


def encode_for_transmission(data: bytes) -> str:
    """Encode bytes for transmission (base64).

    Args:
        data: Binary data

    Returns:
        Base64-encoded string
    """
    import base64

    return base64.b64encode(data).decode("ascii")


def decode_from_transmission(encoded: str) -> bytes:
    """Decode bytes from transmission.

    Args:
        encoded: Base64-encoded string

    Returns:
        Binary data
    """
    import base64

    return base64.b64decode(encoded.encode("ascii"))


def compress_data(data: bytes, level: int = 6) -> bytes:
    """Compress data using zlib.

    Args:
        data: Input data
        level: Compression level (1-9)

    Returns:
        Compressed data
    """
    import zlib

    return zlib.compress(data, level)


def decompress_data(data: bytes) -> bytes:
    """Decompress zlib-compressed data.

    Args:
        data: Compressed data

    Returns:
        Decompressed data
    """
    import zlib

    return zlib.decompress(data)
