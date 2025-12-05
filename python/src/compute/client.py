"""
Compute Client for connecting to Go orchestrator

This module provides the Python client for submitting and monitoring
compute jobs via the Go orchestrator's Cap'n Proto RPC interface.
"""

import logging
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import sys

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


class TaskStatus(IntEnum):
    """Status of a compute task."""
    PENDING = 0
    ASSIGNED = 1
    COMPUTING = 2
    VERIFYING = 3
    COMPLETED = 4
    FAILED = 5
    TIMEOUT = 6
    CANCELLED = 7


@dataclass
class JobStatus:
    """Status of a compute job."""
    job_id: str
    status: TaskStatus
    progress: float
    completed_chunks: int
    total_chunks: int
    estimated_time_remaining: int
    error: Optional[str] = None


@dataclass
class ComputeCapacity:
    """Compute capacity of a node."""
    cpu_cores: int
    ram_mb: int
    current_load: float
    disk_mb: int
    bandwidth_mbps: float


class ComputeClient:
    """Client for distributed compute operations.
    
    This client connects to the Go orchestrator via Cap'n Proto RPC
    and provides methods for submitting and monitoring compute jobs.
    
    Example:
        client = ComputeClient('localhost', 8080)
        client.connect()
        
        job_id = client.submit_job(my_job_definition, input_data)
        
        while True:
            status = client.get_status(job_id)
            print(f"Progress: {status.progress * 100:.1f}%")
            if status.status == TaskStatus.COMPLETED:
                break
            time.sleep(1)
        
        result, worker_node = client.get_result(job_id)
        print(f"Executed by: {worker_node}")
        client.disconnect()
    """
    
    def __init__(self, host: str = 'localhost', port: int = 8080, schema_path: str = None):
        """Initialize the compute client.
        
        Args:
            host: Go node host
            port: Go node RPC port
            schema_path: Path to Cap'n Proto schema (optional)
        """
        self.host = host
        self.port = port
        self.schema_path = schema_path
        self._connected = False
        self._go_client = None
        self._jobs: Dict[str, Any] = {}
    
    def connect(self) -> bool:
        """Connect to the Go orchestrator via Cap'n Proto RPC.
        
        Returns:
            True if connected successfully
        """
        try:
            from src.client.go_client import GoNodeClient
            
            logger.info(f"Connecting to compute service at {self.host}:{self.port}")
            self._go_client = GoNodeClient(self.host, self.port, self.schema_path)
            
            if self._go_client.connect():
                self._connected = True
                logger.info(f"✅ Connected to Go node at {self.host}:{self.port}")
                return True
            else:
                logger.error(f"Failed to connect to Go node at {self.host}:{self.port}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the Go orchestrator."""
        if self._connected and self._go_client:
            logger.info("Disconnecting from compute service")
            self._go_client.disconnect()
            self._connected = False
            self._go_client = None
    
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self._go_client is not None
    
    def submit_job(self, job_definition, input_data: bytes, **kwargs) -> str:
        """Submit a compute job to the Go orchestrator.
        
        Args:
            job_definition: A JobDefinition object
            input_data: The input data for the job
            **kwargs: Additional job configuration
            
        Returns:
            The job ID
            
        Raises:
            ConnectionError: If not connected
            RuntimeError: If job submission fails
        """
        if not self._connected:
            raise ConnectionError("Not connected to compute service")
        
        # Convert job definition to manifest
        manifest = job_definition.to_manifest(input_data, **kwargs)
        job_id = manifest['jobId']
        
        logger.info(f"Submitting job {job_id} with {len(input_data)} bytes of input")
        
        # Store job locally for tracking
        self._jobs[job_id] = {
            'manifest': manifest,
            'input_data': input_data,
            'definition': job_definition,
            'status': TaskStatus.PENDING,
            'start_time': time.time(),
            'result': None,
        }
        
        # Submit to Go orchestrator via RPC
        success, error_msg = self._go_client.submit_compute_job(
            job_id=job_id,
            input_data=input_data,
            split_strategy=manifest.get('splitStrategy', 'fixed'),
            min_chunk_size=manifest.get('minChunkSize', 1024),
            max_chunk_size=manifest.get('maxChunkSize', 65536),
            timeout_secs=manifest.get('timeoutSecs', 300),
            priority=manifest.get('priority', 5)
        )
        
        if success:
            logger.info(f"✅ Job {job_id} submitted to Go orchestrator")
            self._jobs[job_id]['status'] = TaskStatus.ASSIGNED
        else:
            logger.warning(f"⚠️ Go orchestrator submission failed: {error_msg}")
            logger.info(f"   Falling back to local execution for job {job_id}")
            self._execute_locally(job_id)
        
        return job_id
    
    def _execute_locally(self, job_id: str):
        """Execute job locally when Go orchestrator is unavailable.
        
        This is the fallback when distributed execution fails.
        """
        job = self._jobs[job_id]
        definition = job['definition']
        input_data = job['input_data']
        
        try:
            # Split
            job['status'] = TaskStatus.COMPUTING
            print("   [LOCAL] SPLIT phase...")
            chunks = definition.split(input_data)
            print(f"   [LOCAL] Split into {len(chunks)} chunks")
            
            # Execute each chunk
            print("   [LOCAL] EXECUTE phase...")
            results = []
            for i, chunk in enumerate(chunks):
                result = definition.execute(chunk)
                results.append(result)
                print(f"   [LOCAL] Chunk {i+1}/{len(chunks)} completed")
            
            # Merge
            print("   [LOCAL] MERGE phase...")
            final_result = definition.merge(results)
            
            job['result'] = final_result
            job['status'] = TaskStatus.COMPLETED
            logger.info(f"Job {job_id} completed locally with {len(final_result)} bytes result")
            
        except Exception as e:
            job['status'] = TaskStatus.FAILED
            job['error'] = str(e)
            logger.error(f"Job {job_id} failed: {e}")
    
    
    def get_status(self, job_id: str) -> JobStatus:
        """Get the status of a job from Go orchestrator.
        
        Args:
            job_id: The job ID
            
        Returns:
            JobStatus object
            
        Raises:
            ConnectionError: If not connected
            KeyError: If job not found
        """
        if not self._connected:
            raise ConnectionError("Not connected to compute service")
        
        if job_id not in self._jobs:
            raise KeyError(f"Job {job_id} not found")
        
        # Try to get status from Go orchestrator
        status_dict = self._go_client.get_compute_job_status(job_id)
        
        if status_dict:
            # Map Go status string to TaskStatus enum
            status_map = {
                'pending': TaskStatus.PENDING,
                'assigned': TaskStatus.ASSIGNED,
                'computing': TaskStatus.COMPUTING,
                'verifying': TaskStatus.VERIFYING,
                'completed': TaskStatus.COMPLETED,
                'failed': TaskStatus.FAILED,
                'timeout': TaskStatus.TIMEOUT,
                'cancelled': TaskStatus.CANCELLED,
            }
            status = status_map.get(status_dict['status'].lower(), TaskStatus.PENDING)
            
            return JobStatus(
                job_id=job_id,
                status=status,
                progress=status_dict['progress'],
                completed_chunks=status_dict['completedChunks'],
                total_chunks=status_dict['totalChunks'],
                estimated_time_remaining=status_dict['estimatedTimeRemaining'],
                error=status_dict['errorMsg'] if status_dict['errorMsg'] else None,
            )
        
        # Fallback to local status
        job = self._jobs[job_id]
        return JobStatus(
            job_id=job_id,
            status=job['status'],
            progress=1.0 if job['status'] == TaskStatus.COMPLETED else 0.5,
            completed_chunks=1 if job['status'] == TaskStatus.COMPLETED else 0,
            total_chunks=1,
            estimated_time_remaining=0 if job['status'] == TaskStatus.COMPLETED else 10,
            error=job.get('error'),
        )
    
    def get_result(self, job_id: str, timeout: float = 300.0) -> Tuple[bytes, str]:
        """Get the result of a completed job from Go orchestrator.
        
        Args:
            job_id: The job ID
            timeout: Maximum time to wait in seconds
            
        Returns:
            Tuple of (result_bytes, worker_node)
            worker_node is "local" or the peer ID of the remote node that executed
            
        Raises:
            ConnectionError: If not connected
            KeyError: If job not found
            TimeoutError: If job doesn't complete in time
            RuntimeError: If job failed
        """
        if not self._connected:
            raise ConnectionError("Not connected to compute service")
        
        if job_id not in self._jobs:
            raise KeyError(f"Job {job_id} not found")
        
        # Try to get result from Go orchestrator first
        result_data, error_msg, worker_node = self._go_client.get_compute_job_result(
            job_id, 
            timeout_ms=int(timeout * 1000)
        )
        
        if result_data:
            return result_data, worker_node
        
        if error_msg:
            logger.warning(f"Go orchestrator result fetch failed: {error_msg}")
        
        # Fallback to local result
        start = time.time()
        while time.time() - start < timeout:
            job = self._jobs[job_id]
            
            if job['status'] == TaskStatus.COMPLETED:
                return job['result'], "local"
            
            if job['status'] == TaskStatus.FAILED:
                raise RuntimeError(f"Job failed: {job.get('error', 'Unknown error')}")
            
            if job['status'] == TaskStatus.CANCELLED:
                raise RuntimeError("Job was cancelled")
            
            time.sleep(0.1)
        
        raise TimeoutError(f"Timeout waiting for job {job_id}")
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job via Go orchestrator.
        
        Args:
            job_id: The job ID
            
        Returns:
            True if cancelled successfully
        """
        if not self._connected:
            raise ConnectionError("Not connected to compute service")
        
        # Try to cancel via Go orchestrator
        cancelled = self._go_client.cancel_compute_job(job_id)
        
        if cancelled:
            if job_id in self._jobs:
                self._jobs[job_id]['status'] = TaskStatus.CANCELLED
            logger.info(f"Job {job_id} cancelled via Go orchestrator")
            return True
        
        # Fallback to local cancellation
        if job_id not in self._jobs:
            return False
        
        self._jobs[job_id]['status'] = TaskStatus.CANCELLED
        logger.info(f"Job {job_id} cancelled locally")
        return True
    
    def get_capacity(self) -> ComputeCapacity:
        """Get the compute capacity of the connected node from Go orchestrator.
        
        Returns:
            ComputeCapacity object
        """
        if not self._connected:
            raise ConnectionError("Not connected to compute service")
        
        # Query capacity from Go node
        capacity = self._go_client.get_compute_capacity()
        
        if capacity:
            return ComputeCapacity(
                cpu_cores=capacity.get('cpuCores', 4),
                ram_mb=capacity.get('ramMb', 8192),
                current_load=capacity.get('currentLoad', 0.0),
                disk_mb=capacity.get('diskMb', 100000),
                bandwidth_mbps=capacity.get('bandwidthMbps', 100.0),
            )
        
        # Fallback to estimated local capacity
        return ComputeCapacity(
            cpu_cores=4,
            ram_mb=8192,
            current_load=0.1,
            disk_mb=100000,
            bandwidth_mbps=100.0,
        )
    
    def list_jobs(self) -> List[str]:
        """List all job IDs.
        
        Returns:
            List of job IDs
        """
        return list(self._jobs.keys())
    
    def cleanup_job(self, job_id: str):
        """Clean up a completed or failed job.
        
        Args:
            job_id: The job ID
        """
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.debug(f"Cleaned up job {job_id}")
