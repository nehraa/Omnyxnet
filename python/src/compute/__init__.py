"""
Distributed Compute SDK for Pangea Net

This module provides the Python client SDK for submitting and managing
distributed compute jobs. Following the Golden Rule: Python handles
AI, CLI management, and user interface.

Example:
    from pangea.compute import Job, submit_job

    @Job.define
    def my_job():
        @Job.split
        def split(data: bytes) -> list[bytes]:
            return [data[i:i+1024] for i in range(0, len(data), 1024)]

        @Job.execute
        def execute(chunk: bytes) -> bytes:
            return chunk.upper()

        @Job.merge
        def merge(results: list[bytes]) -> bytes:
            return b''.join(results)

    result = submit_job(my_job, input_data=b"hello world")
"""

from .job import Job, JobBuilder, JobDefinition
from .client import ComputeClient, JobStatus, TaskStatus
from .preprocessor import DataPreprocessor, ChunkStrategy
from .visualizer import ResultVisualizer

__all__ = [
    "Job",
    "JobBuilder",
    "JobDefinition",
    "ComputeClient",
    "JobStatus",
    "TaskStatus",
    "DataPreprocessor",
    "ChunkStrategy",
    "ResultVisualizer",
]


# Convenience function for submitting jobs
def submit_job(
    job_definition,
    input_data: bytes,
    host: str = "localhost",
    port: int = 8080,
    **kwargs,
):
    """
    Submit a compute job to the network with safe fallbacks.

    Args:
        job_definition: A job definition created with @Job.define
        input_data: The input data for the job
        host: The Go node host
        port: The Go node RPC port
        **kwargs: Additional job configuration

    Returns:
        Tuple of (result bytes, worker_node) where worker_node indicates which node executed
    """
    client = ComputeClient(host, port)
    connected = False
    try:
        connected = client.connect()
        if not connected:
            # Match CLI behaviour: fail clearly instead of raising opaque errors later
            raise ConnectionError(
                f"Unable to connect to compute service at {host}:{port}"
            )

        job_id = client.submit_job(job_definition, input_data, **kwargs)
        return client.get_result(job_id)
    finally:
        # Always attempt to disconnect, but don't let cleanup errors hide the real problem
        try:
            if connected:
                client.disconnect()
        except Exception:
            # Best-effort cleanup; log at call-site if desired
            pass
