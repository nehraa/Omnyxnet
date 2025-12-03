"""
Job Definition DSL for Distributed Compute

This module provides a Pythonic DSL for defining compute jobs.
Jobs consist of three functions: split, execute, and merge.
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class JobDefinition:
    """Represents a complete job definition with split, execute, and merge functions."""
    
    name: str
    split_fn: Optional[Callable[[bytes], List[bytes]]] = None
    execute_fn: Optional[Callable[[bytes], bytes]] = None
    merge_fn: Optional[Callable[[List[bytes]], bytes]] = None
    metadata: dict = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Validate that the job definition is complete."""
        if not self.split_fn:
            logger.warning(f"Job {self.name} missing split function, using default")
            self.split_fn = default_split
        if not self.execute_fn:
            logger.warning(f"Job {self.name} missing execute function, using identity")
            self.execute_fn = default_execute
        if not self.merge_fn:
            logger.warning(f"Job {self.name} missing merge function, using default")
            self.merge_fn = default_merge
        return True
    
    def to_manifest(self, input_data: bytes, **kwargs) -> dict:
        """Convert job definition to a manifest for submission."""
        self.validate()
        
        # Calculate job ID from hash of definition + input
        hasher = hashlib.sha256()
        hasher.update(self.name.encode())
        hasher.update(input_data[:1024])  # First 1KB for uniqueness
        job_id = hasher.hexdigest()[:16]
        
        return {
            'jobId': f"job-{job_id}",
            'wasmModule': self._serialize_functions(),
            'inputData': list(input_data),  # Convert to list for JSON
            'splitStrategy': kwargs.get('split_strategy', 'fixed_size'),
            'minChunkSize': kwargs.get('min_chunk_size', 65536),
            'maxChunkSize': kwargs.get('max_chunk_size', 1048576),
            'verificationMode': kwargs.get('verification_mode', 'hash'),
            'timeoutSecs': kwargs.get('timeout_secs', 300),
            'retryCount': kwargs.get('retry_count', 3),
            'priority': kwargs.get('priority', 5),
            'redundancy': kwargs.get('redundancy', 1),
            **self.metadata,
        }
    
    def _serialize_functions(self) -> bytes:
        """Serialize functions for transmission.
        
        Note: In a real implementation, this would compile Python to WASM.
        For now, we return a placeholder that tells the server to use
        the built-in split/execute/merge functions.
        """
        # Placeholder - real implementation would use py2wasm or similar
        return b'PANGEA_PYTHON_JOB_V1'
    
    def split(self, data: bytes) -> List[bytes]:
        """Split input data into chunks."""
        if self.split_fn:
            return self.split_fn(data)
        return default_split(data)
    
    def execute(self, chunk: bytes) -> bytes:
        """Execute computation on a single chunk."""
        if self.execute_fn:
            return self.execute_fn(chunk)
        return default_execute(chunk)
    
    def merge(self, results: List[bytes]) -> bytes:
        """Merge results from multiple chunks."""
        if self.merge_fn:
            return self.merge_fn(results)
        return default_merge(results)


class JobBuilder:
    """Builder for creating job definitions."""
    
    def __init__(self, name: str):
        self.definition = JobDefinition(name=name)
    
    def with_split(self, fn: Callable[[bytes], List[bytes]]) -> 'JobBuilder':
        """Set the split function."""
        self.definition.split_fn = fn
        return self
    
    def with_execute(self, fn: Callable[[bytes], bytes]) -> 'JobBuilder':
        """Set the execute function."""
        self.definition.execute_fn = fn
        return self
    
    def with_merge(self, fn: Callable[[List[bytes]], bytes]) -> 'JobBuilder':
        """Set the merge function."""
        self.definition.merge_fn = fn
        return self
    
    def with_metadata(self, **kwargs) -> 'JobBuilder':
        """Add metadata to the job."""
        self.definition.metadata.update(kwargs)
        return self
    
    def build(self) -> JobDefinition:
        """Build the job definition."""
        self.definition.validate()
        return self.definition


class Job:
    """Decorator-based job definition.
    
    Example:
        @Job.define
        def word_count():
            @Job.split
            def split(data: bytes) -> list[bytes]:
                return data.split(b'\\n')
            
            @Job.execute
            def execute(line: bytes) -> bytes:
                return str(len(line.split())).encode()
            
            @Job.merge
            def merge(counts: list[bytes]) -> bytes:
                total = sum(int(c) for c in counts)
                return str(total).encode()
    """
    
    _current_builder: Optional[JobBuilder] = None
    
    @classmethod
    def define(cls, fn: Callable) -> JobDefinition:
        """Define a compute job using decorators.
        
        Args:
            fn: A function that defines the job using @Job.split, @Job.execute, @Job.merge
            
        Returns:
            A JobDefinition
        """
        cls._current_builder = JobBuilder(fn.__name__)
        
        # Execute the function to register split/execute/merge
        fn()
        
        definition = cls._current_builder.build()
        cls._current_builder = None
        
        return definition
    
    @classmethod
    def split(cls, fn: Callable[[bytes], List[bytes]]) -> Callable[[bytes], List[bytes]]:
        """Decorator to define the split function."""
        if cls._current_builder:
            cls._current_builder.with_split(fn)
        return fn
    
    @classmethod
    def execute(cls, fn: Callable[[bytes], bytes]) -> Callable[[bytes], bytes]:
        """Decorator to define the execute function."""
        if cls._current_builder:
            cls._current_builder.with_execute(fn)
        return fn
    
    @classmethod
    def merge(cls, fn: Callable[[List[bytes]], bytes]) -> Callable[[List[bytes]], bytes]:
        """Decorator to define the merge function."""
        if cls._current_builder:
            cls._current_builder.with_merge(fn)
        return fn


# Default implementations

def default_split(data: bytes, chunk_size: int = 65536) -> List[bytes]:
    """Default split: divide into fixed-size chunks."""
    return [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]


def default_execute(chunk: bytes) -> bytes:
    """Default execute: identity function."""
    return chunk


def default_merge(results: List[bytes]) -> bytes:
    """Default merge: concatenate results."""
    return b''.join(results)


# Pre-built job templates

def create_map_reduce_job(
    name: str,
    mapper: Callable[[bytes], bytes],
    reducer: Callable[[List[bytes]], bytes],
    chunk_size: int = 65536
) -> JobDefinition:
    """Create a MapReduce-style job.
    
    Args:
        name: Job name
        mapper: Function to apply to each chunk
        reducer: Function to combine results
        chunk_size: Size of each chunk
        
    Returns:
        A JobDefinition
    """
    return (
        JobBuilder(name)
        .with_split(lambda data: default_split(data, chunk_size))
        .with_execute(mapper)
        .with_merge(reducer)
        .build()
    )


def create_parallel_process_job(
    name: str,
    processor: Callable[[bytes], bytes],
    chunk_size: int = 65536
) -> JobDefinition:
    """Create a job that processes chunks in parallel and concatenates results.
    
    Args:
        name: Job name
        processor: Function to process each chunk
        chunk_size: Size of each chunk
        
    Returns:
        A JobDefinition
    """
    return create_map_reduce_job(name, processor, default_merge, chunk_size)
